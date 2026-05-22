"""
Groww App Review Insights — executive dashboard (Streamlit Cloud).
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
    render_deliverables,
    render_hero,
    render_kpis,
    render_quotes,
    render_reviews_grid,
    render_section_head,
    render_sidebar_brand,
    render_sidebar_sync,
    render_pipeline_steps,
    render_themes,
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


def _analysis_configured() -> bool:
    return bool(config_value("GROQ_API_KEY"))


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

    steps: dict[int, str] = {i: "pending" for i in range(1, 5)}
    pipeline_slot = st.sidebar.empty()

    def on_step(phase: int, _label: str, state: str) -> None:
        steps[phase] = state
        with pipeline_slot.container():
            render_pipeline_steps(steps)

    with st.spinner("Updating your dashboard…"):
        result = run_full_pipeline(database_path=db_path, on_step=on_step)

    st.session_state["pipeline_result"] = result
    st.session_state["pipeline_done"] = True
    st.session_state["last_sync"] = datetime.now().strftime("%d %b %Y · %H:%M")


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


from shared.db_paths import resolve_database_path
from shared.play_store_config import resolve_play_package, validate_finance_package

db_path = resolve_database_path(config_value("DATABASE_PATH") or None)
os.environ["DATABASE_PATH"] = db_path

_raw_pkg = config_value("GOOGLE_PLAY_PACKAGE_NAME") or None
play_pkg = resolve_play_package(_raw_pkg)
os.environ["GOOGLE_PLAY_PACKAGE_NAME"] = play_pkg
_pkg_ok, _pkg_info = validate_finance_package(play_pkg)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()
    if _raw_pkg == "com.groww":
        st.warning(
            "Secrets still use `com.groww` (plant app). Fixed to **com.nextbillion.groww** for this run. "
            "Update Streamlit Secrets, then **Refresh insights**."
        )
    st.caption(f"Source app: {_pkg_info}" if _pkg_ok else f"⚠ {_pkg_info}")
    st.caption("Tap refresh to wipe old data and re-fetch finance reviews.")
    if st.button("Refresh insights", type="primary", use_container_width=True):
        st.session_state["pipeline_done"] = False
        st.session_state["force_refresh"] = True
        st.rerun()
    render_sidebar_sync(st.session_state.get("last_sync"))
    if not _analysis_configured():
        st.warning("Dashboard sync is unavailable. Check app configuration.")

data = load_dashboard(db_path)
needs_pipeline = (
    data["insights"] is None
    or data["total"] == 0
    or st.session_state.get("force_refresh")
)
if needs_pipeline and _analysis_configured() and not st.session_state.get("pipeline_done"):
    if st.session_state.get("force_refresh"):
        from shared.database import DatabaseManager

        _db = DatabaseManager(db_path)
        try:
            _db.clear_all_data()
        finally:
            _db.close()
    if not _pkg_ok:
        st.error(f"Cannot sync: {_pkg_info}")
        st.stop()
    run_background_pipeline(db_path)
    st.session_state.pop("force_refresh", None)
    st.rerun()

data = load_dashboard(db_path)
insights = data["insights"] or {}
sentiment = insights.get("sentiment_summary") or {}
pos = sentiment.get("positive", 0)
neg = sentiment.get("negative", 0)
neu = sentiment.get("neutral", 0)
analysed = insights.get("total_reviews_analysed", 0) or 0
total_sent = pos + neg + neu or 1
pos_pct = int(round(100 * pos / total_sent)) if total_sent else 0
week = insights.get("week", "—")
doc_url = doc_url_from_id(insights.get("doc_id"))
email_id = insights.get("email_id")
play_url = f"https://play.google.com/store/apps/details?id={play_pkg}"

# ── Dashboard ─────────────────────────────────────────────────────────────────
render_hero(week, data["total"], analysed, pos_pct)
render_kpis(data["total"], analysed, pos, neg, neu)

chart_left, chart_mid, chart_right = st.columns([1.05, 1.05, 1], gap="large")

with chart_left:
    st.markdown('<div class="panel"><div class="panel-title"><span>●</span> Sentiment</div>', unsafe_allow_html=True)
    if pos + neg + neu > 0:
        st.plotly_chart(sentiment_donut(pos, neg, neu), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("Awaiting next sync.")
    st.markdown("</div>", unsafe_allow_html=True)

with chart_mid:
    st.markdown('<div class="panel"><div class="panel-title"><span>●</span> Ratings</div>', unsafe_allow_html=True)
    if sum(data["rating_dist"].values()):
        st.plotly_chart(rating_bars(data["rating_dist"]), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("Awaiting next sync.")
    st.markdown("</div>", unsafe_allow_html=True)

with chart_right:
    st.markdown('<div class="panel"><div class="panel-title"><span>●</span> Themes</div>', unsafe_allow_html=True)
    render_themes(insights.get("themes") or [])
    st.markdown("</div>", unsafe_allow_html=True)

render_section_head("Voice of the customer")
tab_pos, tab_neg, tab_recent, tab_quotes = st.tabs(
    ["Loved by users", "Needs attention", "Latest", "Highlighted quotes"]
)

with tab_pos:
    render_reviews_grid(data["positive"])
with tab_neg:
    render_reviews_grid(data["negative"], negative=True)
with tab_recent:
    render_reviews_grid(data["recent"])
with tab_quotes:
    render_quotes(insights.get("quotes") or [])

render_section_head("Recommended for product")
render_actions(insights.get("actions") or [])

render_deliverables(bool(doc_url), bool(email_id))

link1, link2, link3 = st.columns(3)
with link1:
    if doc_url:
        st.link_button("Open weekly report", doc_url, use_container_width=True, type="primary")
with link2:
    if email_id:
        st.link_button("Open Gmail drafts", "https://mail.google.com/mail/u/0/#drafts", use_container_width=True)
with link3:
    st.link_button("View on Play Store", play_url, use_container_width=True)
