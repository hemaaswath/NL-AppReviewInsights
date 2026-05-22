"""
Groww App Review Insights — dashboard (Streamlit Cloud).

Pipeline phases 1–4 run automatically in the background when data is missing
or when the user clicks Refresh in the sidebar. No per-phase buttons.
"""
from __future__ import annotations

import html
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
for sub in ("", "phase-1/src", "phase-2/src", "phase-3/src", "phase-4/src"):
    p = str(ROOT / sub) if sub else str(ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("STREAMLIT_DEPLOYMENT", "1")
os.environ.setdefault("USE_DIRECT_GOOGLE", "1")

import streamlit as st
from dotenv import load_dotenv

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
    page_title="Groww Review Insights",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding-top: 1.5rem; max-width: 1200px; }
.hero {
  background: linear-gradient(135deg, #0d3b2e 0%, #00d09c 55%, #00a67e 100%);
  border-radius: 16px; padding: 2rem 2.2rem; color: #fff; margin-bottom: 1.5rem;
  box-shadow: 0 8px 32px rgba(0, 166, 126, 0.25);
}
.hero h1 { margin: 0; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.02em; }
.hero p { margin: 0.5rem 0 0; opacity: 0.92; font-size: 1rem; }
div[data-testid="stMetric"] {
  background: #f8faf9; border: 1px solid #e8efec; border-radius: 12px;
  padding: 0.75rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
div[data-testid="stMetric"] label { color: #5f6f6b; font-size: 0.8rem; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #0d3b2e; }
.review-card {
  background: #fff; border: 1px solid #e8efec; border-radius: 12px;
  padding: 1rem 1.15rem; margin-bottom: 0.75rem;
  border-left: 4px solid #00a67e;
}
.review-card.negative { border-left-color: #e85d4c; }
.review-card .stars { color: #f5a623; font-size: 0.95rem; margin-bottom: 0.35rem; }
.review-card .meta { color: #7a8a86; font-size: 0.78rem; margin-bottom: 0.5rem; }
.review-card .text { color: #1a2e28; font-size: 0.92rem; line-height: 1.45; }
.quote-card {
  background: linear-gradient(180deg, #f0faf6 0%, #fff 100%);
  border-radius: 12px; padding: 1rem 1.2rem; border: 1px solid #d4ebe3;
  font-style: italic; color: #2d4a42;
}
.pipeline-pill {
  display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 600; margin-right: 0.35rem;
}
.pill-done { background: #d4f5e8; color: #0d5c40; }
.pill-run { background: #fff3cd; color: #856404; }
.pill-err { background: #fde8e6; color: #9b2c2c; }
.pill-skip { background: #eef1f0; color: #5f6f6b; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)


def stars_html(rating: int) -> str:
    filled = "★" * rating + "☆" * (5 - rating)
    return f'<span class="stars">{filled}</span>'


def review_card(review: dict, negative: bool = False) -> str:
    date_str = html.escape((review.get("date") or "")[:10])
    raw = review.get("text") or review.get("title") or ""
    if len(raw) > 280:
        raw = raw[:277] + "…"
    text = html.escape(raw)
    rating = review.get("rating", 0)
    css = "review-card negative" if negative else "review-card"
    return (
        f'<div class="{css}">'
        f'{stars_html(rating)}'
        f'<div class="meta">{date_str} · Google Play · {rating}/5</div>'
        f'<div class="text">{text}</div></div>'
    )


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

    steps = {i: "running" for i in range(1, 5)}
    status_box = st.sidebar.empty()

    def on_step(phase: int, label: str, state: str) -> None:
        steps[phase] = state
        pills = []
        labels = {
            1: "Collect",
            2: "Analyze",
            3: "Doc",
            4: "Email",
        }
        for n in range(1, 5):
            s = steps.get(n, "pending")
            cls = {
                "done": "pill-done",
                "running": "pill-run",
                "error": "pill-err",
                "skipped": "pill-skip",
            }.get(s, "pill-skip")
            pills.append(f'<span class="pipeline-pill {cls}">{labels[n]}</span>')
        status_box.markdown(
            "**Background sync**<br>" + "".join(pills),
            unsafe_allow_html=True,
        )

    with st.spinner("Updating reviews and insights in the background…"):
        result = run_full_pipeline(database_path=db_path, on_step=on_step)

    st.session_state["pipeline_result"] = result
    st.session_state["pipeline_done"] = True
    st.session_state["last_sync"] = datetime.now().isoformat(timespec="seconds")


def load_dashboard(db_path: str) -> dict:
    from shared.database import DatabaseManager

    db = DatabaseManager(db_path)
    try:
        insights = db.get_insights()
        total = db.get_review_count()
        positive = db.get_top_reviews(limit=6, mode="positive")
        negative = db.get_top_reviews(limit=6, mode="negative")
        recent = db.get_top_reviews(limit=6, mode="recent")
        rating_dist = db.get_rating_distribution()
        return {
            "insights": insights,
            "total": total,
            "positive": positive,
            "negative": negative,
            "recent": recent,
            "rating_dist": rating_dist,
        }
    finally:
        db.close()


# ── Sidebar: background sync only ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### Settings")
    if not config_value("GROQ_API_KEY"):
        st.error("Add **GROQ_API_KEY** to Streamlit secrets.")
    if st.button("Refresh data", type="primary", use_container_width=True):
        st.session_state["pipeline_done"] = False
        st.session_state["force_refresh"] = True
        st.rerun()
    if st.session_state.get("last_sync"):
        st.caption(f"Last sync: {st.session_state['last_sync']}")

db_path = config_value("DATABASE_PATH", "data/reviews.db")
os.environ["DATABASE_PATH"] = db_path

# Auto background pipeline when no insights or forced refresh
data = load_dashboard(db_path)
needs_pipeline = (
    data["insights"] is None
    or data["total"] == 0
    or st.session_state.get("force_refresh")
)
if needs_pipeline and config_value("GROQ_API_KEY") and not st.session_state.get("pipeline_done"):
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

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="hero">
  <h1>Groww App Review Insights</h1>
  <p>Weekly pulse from Google Play · Week <strong>{week}</strong> ·
  Pipeline runs automatically — no manual steps required.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Reviews in DB", data["total"])
c2.metric("Analysed", insights.get("total_reviews_analysed", 0))
c3.metric("Positive", pos)
c4.metric("Negative", neg)
c5.metric("Neutral", neu)

# ── Charts + themes ───────────────────────────────────────────────────────────
left, right = st.columns([1, 1])

with left:
    st.subheader("Rating distribution")
    if sum(data["rating_dist"].values()):
        st.bar_chart(data["rating_dist"])
    else:
        st.info("Collecting reviews… run Refresh in the sidebar if this stays empty.")

with right:
    st.subheader("Top themes")
    themes = insights.get("themes") or []
    if themes:
        for i, theme in enumerate(themes[:5], 1):
            sent = theme.get("sentiment", "neutral")
            icon = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(sent, "⚪")
            st.markdown(
                f"**{i}. {theme.get('name', 'Theme')}** {icon}  \n"
                f"{theme.get('review_count', 0)} reviews · {sent}"
            )
    else:
        st.caption("Themes appear after background analysis completes.")

# ── Top reviews ───────────────────────────────────────────────────────────────
st.subheader("Top reviews")
tab_pos, tab_neg, tab_recent, tab_quotes = st.tabs(
    ["Top positive", "Top critical", "Most recent", "AI highlights"]
)

with tab_pos:
    if data["positive"]:
        st.markdown("".join(review_card(r) for r in data["positive"]), unsafe_allow_html=True)
    else:
        st.caption("No positive reviews yet.")

with tab_neg:
    if data["negative"]:
        st.markdown(
            "".join(review_card(r, negative=True) for r in data["negative"]),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No critical reviews yet.")

with tab_recent:
    if data["recent"]:
        st.markdown("".join(review_card(r) for r in data["recent"]), unsafe_allow_html=True)
    else:
        st.caption("No reviews yet.")

with tab_quotes:
    quotes = insights.get("quotes") or []
    if quotes:
        for q in quotes:
            qt = html.escape(q.get("text", ""))
            tn = html.escape(q.get("theme_name", ""))
            st.markdown(
                f'<div class="quote-card">"{qt}"<br><br>'
                f'<small>{q.get("rating", "?")}★ · {tn}</small></div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("Representative quotes appear after analysis.")

# ── Actions + links ───────────────────────────────────────────────────────────
st.subheader("Recommended actions")
actions = insights.get("actions") or []
if actions:
    for action in actions:
        pri = (action.get("priority") or "medium").upper()
        st.markdown(f"**[{pri}]** {action.get('description', '')}")
else:
    st.caption("Action items will show after analysis.")

link1, link2, link3 = st.columns(3)
with link1:
    if doc_url:
        st.link_button("Open weekly report (Google Doc)", doc_url, use_container_width=True)
    else:
        st.caption("Google Doc link available after Phase 3 sync.")
with link2:
    if email_id:
        st.success("Gmail draft created — check **Drafts** in Gmail.")
    else:
        st.caption("Gmail draft after sync (needs EMAIL_RECIPIENT).")
with link3:
    pkg = config_value("GOOGLE_PLAY_PACKAGE_NAME", "com.groww")
    st.link_button(
        "View on Play Store",
        f"https://play.google.com/store/apps/details?id={pkg}",
        use_container_width=True,
    )

# Pipeline result (collapsed detail)
if st.session_state.get("pipeline_result"):
    with st.expander("Background sync log"):
        st.json(st.session_state["pipeline_result"])
