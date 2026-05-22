"""
Groww App Review Insights — premium dashboard (Streamlit Cloud).

Phases 1–4 run in the background when data is missing or on Refresh.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
for sub in ("", "frontend", "phase-1/src", "phase-2/src", "phase-3/src", "phase-4/src"):
    p = str(ROOT / sub) if sub else str(ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("STREAMLIT_DEPLOYMENT", "1")
os.environ.setdefault("USE_DIRECT_GOOGLE", "1")

import streamlit as st
from dotenv import load_dotenv

from frontend.dashboard_ui import (
    inject_styles,
    rating_bars,
    render_actions,
    render_cta_strip,
    render_kpis,
    render_quotes,
    render_reviews_grid,
    render_themes,
    render_topbar,
    sentiment_donut,
)

load_dotenv(ROOT / ".env")

SECRET_KEYS = (
    "GROQ_API_KEY",
    "GOOGLE_PLAY_PACKAGE_NAME",
    "GOOGLE_DOC_ID",
    "EMAIL_RECIPIENT",
    "DATABASE_PATH",
    "GOOGLE_TOKEN_JSON",
    "GOOGLE_CREDENTIALS_JSON",
)


def _clean_secret_value(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    return v


def apply_streamlit_secrets() -> None:
    try:
        for key in SECRET_KEYS:
            if key in st.secrets and st.secrets[key]:
                os.environ[key] = _clean_secret_value(str(st.secrets[key]))
    except Exception:
        pass


def config_value(key: str, default: str = "") -> str:
    apply_streamlit_secrets()
    return _clean_secret_value(os.getenv(key, default))


apply_streamlit_secrets()

st.set_page_config(
    page_title="Groww Review Pulse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()


def doc_url_from_id(doc_id: str | None) -> str | None:
    if not doc_id:
        return None
    if doc_id.startswith("http"):
        return doc_id
    if doc_id.startswith("file://"):
        return None
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def run_background_pipeline(db_path: str) -> None:
    from shared.pipeline_runner import run_full_pipeline

    steps = {i: "pending" for i in range(1, 5)}
    status_box = st.sidebar.empty()

    def on_step(phase: int, label: str, state: str) -> None:
        steps[phase] = state
        icons = {1: "📥", 2: "🧠", 3: "📄", 4: "✉️"}
        lines = []
        for n in range(1, 5):
            s = steps.get(n, "pending")
            mark = {"done": "✅", "running": "⏳", "error": "❌", "skipped": "⏭️"}.get(s, "○")
            lines.append(f"{mark} {icons[n]} {['Collect', 'Analyze', 'Doc', 'Email'][n-1]}")
        status_box.markdown("**Pipeline**\n\n" + "\n\n".join(lines))

    with st.spinner("Syncing reviews & insights…"):
        result = run_full_pipeline(database_path=db_path, on_step=on_step)

    st.session_state["pipeline_result"] = result
    st.session_state["pipeline_done"] = True
    st.session_state["last_sync"] = datetime.now().strftime("%d %b %Y, %H:%M")


def load_dashboard(db_path: str) -> dict:
    from shared.database import DatabaseManager

    db = DatabaseManager(db_path)
    try:
        return {
            "insights": db.get_insights(),
            "total": db.get_review_count(),
            "positive": db.get_top_reviews(limit=8, mode="positive"),
            "negative": db.get_top_reviews(limit=8, mode="negative"),
            "recent": db.get_top_reviews(limit=8, mode="recent"),
            "rating_dist": db.get_rating_distribution(),
        }
    finally:
        db.close()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Control panel")
    st.caption("Data syncs automatically. Use refresh to pull latest Play Store reviews.")
    if not config_value("GROQ_API_KEY"):
        st.error("Add **GROQ_API_KEY** in Streamlit secrets.")
    else:
        st.success("Groq API connected")
    if st.button("🔄 Refresh all data", type="primary", use_container_width=True):
        st.session_state["pipeline_done"] = False
        st.session_state["force_refresh"] = True
        st.rerun()
    if st.session_state.get("last_sync"):
        st.markdown(f"**Last sync**  \n{st.session_state['last_sync']}")
    with st.expander("Setup checklist"):
        st.markdown(
            """
            - `GROQ_API_KEY`
            - `GOOGLE_TOKEN_JSON`
            - `GOOGLE_DOC_ID`
            - `EMAIL_RECIPIENT`
            """
        )

from shared.db_paths import resolve_database_path

db_path = resolve_database_path(config_value("DATABASE_PATH") or None)
os.environ["DATABASE_PATH"] = db_path

data = load_dashboard(db_path)
needs_pipeline = (
    data["insights"] is None
    or data["total"] == 0
    or st.session_state.get("force_refresh")
)
syncing = False
if needs_pipeline and config_value("GROQ_API_KEY") and not st.session_state.get("pipeline_done"):
    syncing = True
    run_background_pipeline(db_path)
    st.session_state.pop("force_refresh", None)
    st.rerun()

data = load_dashboard(db_path)
insights = data["insights"] or {}
sentiment = insights.get("sentiment_summary") or {}
pos = sentiment.get("positive", 0)
neg = sentiment.get("negative", 0)
neu = sentiment.get("neutral", 0)
week = insights.get("week", "—")
doc_url = doc_url_from_id(insights.get("doc_id"))
email_id = insights.get("email_id")
pkg = config_value("GOOGLE_PLAY_PACKAGE_NAME", "com.groww")
play_url = f"https://play.google.com/store/apps/details?id={pkg}"

# ── Main dashboard ────────────────────────────────────────────────────────────
render_topbar(week, syncing=syncing)
render_kpis(
    data["total"],
    insights.get("total_reviews_analysed", 0),
    pos,
    neg,
    neu,
)

chart_left, chart_mid, chart_right = st.columns([1.1, 1.1, 1], gap="large")

with chart_left:
    st.markdown('<div class="panel"><div class="panel-title">Sentiment mix</div>', unsafe_allow_html=True)
    if pos + neg + neu > 0:
        st.plotly_chart(sentiment_donut(pos, neg, neu), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("Run refresh to load sentiment data.")
    st.markdown("</div>", unsafe_allow_html=True)

with chart_mid:
    st.markdown('<div class="panel"><div class="panel-title">Star ratings</div>', unsafe_allow_html=True)
    if sum(data["rating_dist"].values()):
        st.plotly_chart(rating_bars(data["rating_dist"]), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No ratings yet.")
    st.markdown("</div>", unsafe_allow_html=True)

with chart_right:
    st.markdown('<div class="panel"><div class="panel-title">Theme leaderboard</div>', unsafe_allow_html=True)
    render_themes(insights.get("themes") or [])
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 💬 Voice of the customer")

tab_pos, tab_neg, tab_recent, tab_quotes = st.tabs(
    ["🌟 Top positive", "⚠️ Critical", "🕐 Recent", "✨ AI picks"]
)

with tab_pos:
    render_reviews_grid(data["positive"])
with tab_neg:
    render_reviews_grid(data["negative"], negative=True)
with tab_recent:
    render_reviews_grid(data["recent"])
with tab_quotes:
    render_quotes(insights.get("quotes") or [])

st.markdown("### 🎯 Product actions")
render_actions(insights.get("actions") or [])

btn1, btn2, btn3 = st.columns(3)
with btn1:
    if doc_url:
        st.link_button("📄 Open Google Doc report", doc_url, use_container_width=True, type="primary")
    else:
        st.button("📄 Google Doc (pending)", disabled=True, use_container_width=True)
with btn2:
    if email_id:
        st.success("✉️ Gmail draft ready — open **Drafts**")
    else:
        st.info("✉️ Gmail draft after EMAIL_RECIPIENT is set")
with btn3:
    st.link_button("📱 View on Play Store", play_url, use_container_width=True)

render_cta_strip(doc_url, email_id, play_url)

if st.session_state.get("pipeline_result"):
    with st.expander("🔧 Sync log (technical)"):
        st.json(st.session_state["pipeline_result"])
