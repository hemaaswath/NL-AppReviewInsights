"""
Groww App Review Insights — executive dashboard (Streamlit Cloud).

Instant load: bundled seed snapshot renders immediately; live sync runs after.
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

load_dotenv(ROOT / ".env", override=False)
os.environ.setdefault("GOOGLE_CREDENTIALS_JSON_OVERWRITE", "0")

# Remove any OAuth files from repo tree; migrate to %LOCALAPPDATA%\groww-insights
from shared.secret_paths import ensure_secrets_outside_repo  # noqa: E402

ensure_secrets_outside_repo()

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
    return _clean_secret_value(os.getenv(key, default))


def _analysis_configured() -> bool:
    return bool(config_value("GROQ_API_KEY"))


def _google_configured() -> bool:
    return bool(config_value("GOOGLE_TOKEN_JSON"))


def _publish_configured() -> bool:
    return bool(config_value("GOOGLE_DOC_ID") and config_value("EMAIL_RECIPIENT"))


def _next_sync_phase(current: str | None) -> str | None:
    if current == "data":
        return "publish" if _google_configured() and _publish_configured() else None
    return None


def _db_mtime(db_path: str) -> float:
    try:
        return os.path.getmtime(db_path)
    except OSError:
        return 0.0


st.set_page_config(
    page_title="Groww Review Pulse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("_secrets_loaded"):
    apply_streamlit_secrets()
    st.session_state["_secrets_loaded"] = True

from frontend.dashboard_ui import (  # noqa: E402
    PLOTLY_CONFIG,
    inject_styles,
    product_map_chart,
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
    render_wow_pulse,
    sentiment_donut,
)
from shared.dashboard_data import has_live_data  # noqa: E402
from shared.db_paths import is_streamlit_cloud, resolve_database_path  # noqa: E402
from shared.groww_product_map import themes_to_area_counts  # noqa: E402
from shared.play_store_config import resolve_play_package, validate_finance_package  # noqa: E402

inject_styles()

db_path = resolve_database_path(config_value("DATABASE_PATH") or None)
os.environ["DATABASE_PATH"] = db_path

_raw_pkg = config_value("GOOGLE_PLAY_PACKAGE_NAME") or None
play_pkg = resolve_play_package(_raw_pkg)
os.environ["GOOGLE_PLAY_PACKAGE_NAME"] = play_pkg

if "_pkg_ok" not in st.session_state:
    st.session_state._pkg_ok, st.session_state._pkg_info = validate_finance_package(play_pkg)
_pkg_ok = st.session_state._pkg_ok
_pkg_info = st.session_state._pkg_info


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_cached(db_path: str, db_mtime: float) -> dict:
    from shared.database import DatabaseManager
    from shared.week_over_week import compute_week_over_week

    db = DatabaseManager(db_path)
    try:
        snap = db.get_dashboard_snapshot()
        snap["wow"] = compute_week_over_week(snap["insights"], snap["prior_insights"])
        return snap
    finally:
        db.close()


@st.cache_data(show_spinner=False)
def load_seed_cached() -> dict:
    from shared.dashboard_data import load_seed_snapshot

    return load_seed_snapshot()


def doc_url_from_id(doc_id: str | None) -> str | None:
    if not doc_id:
        return None
    if doc_id.startswith("http"):
        return doc_id
    if doc_id.startswith("file://"):
        return None
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _pipeline_callbacks():
    steps: dict[int, str] = {i: "pending" for i in range(1, 5)}
    slot = st.sidebar.empty()

    def on_step(phase: int, _label: str, state: str) -> None:
        steps[phase] = state
        with slot.container():
            render_pipeline_steps(steps)

    return on_step


def run_sync_pipeline(db_path: str, *, clear_first: bool, phase: str) -> None:
    from shared.database import DatabaseManager
    from shared.pipeline_runner import run_dashboard_pipeline, run_publish_phases

    if clear_first:
        _db = DatabaseManager(db_path)
        try:
            _db.clear_all_data()
        finally:
            _db.close()
        load_dashboard_cached.clear()

    on_step = _pipeline_callbacks()
    if phase == "data":
        with st.spinner("Fetching live Play Store reviews…"):
            result = run_dashboard_pipeline(
                database_path=db_path, on_step=on_step, include_publish=False
            )
    else:
        with st.spinner("Publishing report & email draft…"):
            result = run_publish_phases(database_path=db_path, on_step=on_step)

    load_dashboard_cached.clear()
    st.session_state["pipeline_result"] = result
    st.session_state["last_sync"] = datetime.now().strftime("%d %b %Y · %H:%M")


def render_dashboard(data: dict, *, data_source: str, play_url: str) -> None:
    insights = data.get("insights") or {}
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

    if data_source == "seed":
        st.caption("📊 Showing bundled snapshot — live sync runs automatically in the background.")

    render_hero(week, data["total"], analysed, pos_pct)
    if data.get("wow"):
        render_wow_pulse(data["wow"])
    render_kpis(data["total"], analysed, pos, neg, neu)

    chart_left, chart_mid, chart_right = st.columns([1.05, 1.05, 1], gap="large")

    with chart_left:
        st.markdown(
            '<div class="panel"><div class="panel-title"><span>●</span> Sentiment</div>',
            unsafe_allow_html=True,
        )
        if pos + neg + neu > 0:
            st.plotly_chart(
                sentiment_donut(pos, neg, neu),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_mid:
        st.markdown(
            '<div class="panel"><div class="panel-title"><span>●</span> Ratings</div>',
            unsafe_allow_html=True,
        )
        if sum(data["rating_dist"].values()):
            st.plotly_chart(
                rating_bars(data["rating_dist"]),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_right:
        st.markdown(
            '<div class="panel"><div class="panel-title"><span>●</span> Top product areas</div>',
            unsafe_allow_html=True,
        )
        render_themes(insights.get("themes") or [])
        st.markdown("</div>", unsafe_allow_html=True)

    area_counts = themes_to_area_counts(insights.get("themes") or [])
    render_section_head("Groww product map")
    map_col, map_side = st.columns([1.4, 1], gap="large")
    with map_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        if sum(area_counts.values()):
            st.plotly_chart(
                product_map_chart(area_counts),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with map_side:
        st.markdown(
            '<div class="panel"><div class="panel-title">Prior week</div>',
            unsafe_allow_html=True,
        )
        prior = data.get("prior_insights")
        if prior:
            p_sent = prior.get("sentiment_summary") or {}
            p_total = sum(p_sent.get(k, 0) for k in ("positive", "negative", "neutral")) or 1
            p_pos = int(round(100 * p_sent.get("positive", 0) / p_total))
            st.caption(
                f"**{prior.get('week', '—')}** · {prior.get('total_reviews_analysed', 0)} reviews · {p_pos}% positive"
            )
            render_themes(prior.get("themes") or [])
        else:
            st.caption("Save insights for two different weeks to compare trends.")
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
            st.link_button(
                "Open Gmail drafts",
                "https://mail.google.com/mail/u/0/#drafts",
                use_container_width=True,
            )
    with link3:
        st.link_button("View on Play Store", play_url, use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()
    if _raw_pkg == "com.groww":
        st.warning(
            "Secrets still use `com.groww` (plant app). Fixed to **com.nextbillion.groww** for this run. "
            "Update Streamlit Secrets."
        )
    st.caption(f"Source app: {_pkg_info}" if _pkg_ok else f"⚠ {_pkg_info}")
    if is_streamlit_cloud():
        st.caption("Cloud: snapshot loads instantly — use **Refresh insights** for live sync.")
        missing = [
            k
            for k, ok in (
                ("GROQ_API_KEY", _analysis_configured()),
                ("GOOGLE_TOKEN_JSON", _google_configured()),
                ("GOOGLE_DOC_ID", bool(config_value("GOOGLE_DOC_ID"))),
                ("EMAIL_RECIPIENT", bool(config_value("EMAIL_RECIPIENT"))),
            )
            if not ok
        ]
        if missing:
            st.info("Streamlit Secrets → add: " + ", ".join(missing))
    else:
        st.caption("Dashboard loads instantly; live sync runs automatically when needed.")
    if st.button("Refresh insights", type="primary", use_container_width=True):
        st.session_state["force_refresh"] = True
        st.session_state["sync_phase"] = "data"
        st.rerun()
    render_sidebar_sync(st.session_state.get("last_sync"))
    if not _analysis_configured():
        st.warning("Live sync unavailable. Bundled snapshot still displays.")

play_url = f"https://play.google.com/store/apps/details?id={play_pkg}"

# Manual full refresh
if st.session_state.get("force_refresh") and _analysis_configured():
    if not _pkg_ok:
        st.error(f"Cannot sync: {_pkg_info}")
        st.stop()
    run_sync_pipeline(db_path, clear_first=True, phase="data")
    st.session_state["force_refresh"] = False
    st.session_state["sync_phase"] = _next_sync_phase("data")
    st.rerun()

# Bootstrap auto-sync when live DB is empty (Streamlit Cloud cold start)
live_snap = load_dashboard_cached(db_path, _db_mtime(db_path))
if has_live_data(live_snap):
    data, data_source = live_snap, "live"
else:
    data, data_source = load_seed_cached(), "seed"
    if (
        _analysis_configured()
        and st.session_state.get("sync_phase") is None
        and not is_streamlit_cloud()
    ):
        st.session_state["sync_phase"] = "data"

render_dashboard(data, data_source=data_source, play_url=play_url)

# Background sync after UI is rendered (local dev only; cloud uses Refresh button)
sync_phase = st.session_state.get("sync_phase")
if sync_phase and _analysis_configured() and _pkg_ok:
    try:
        if sync_phase == "data":
            run_sync_pipeline(db_path, clear_first=False, phase="data")
            st.session_state["sync_phase"] = _next_sync_phase("data")
            st.rerun()
        elif sync_phase == "publish":
            run_sync_pipeline(db_path, clear_first=False, phase="publish")
            st.session_state["sync_phase"] = None
            st.rerun()
    except Exception as exc:
        st.session_state["sync_phase"] = None
        st.error(f"Sync failed: {exc}")
