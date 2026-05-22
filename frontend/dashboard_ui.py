"""Premium dashboard styling and render helpers for Streamlit."""
from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --groww: #00b386;
  --groww-2: #34d399;
  --groww-dark: #007a5c;
  --ink: #0f172a;
  --ink-muted: #64748b;
  --surface: #ffffff;
  --surface-2: #f1f5f9;
  --border: #e2e8f0;
  --danger: #ef4444;
  --warn: #f59e0b;
  --ok: #10b981;
}

.stApp {
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 48%, #f8fafc 100%) !important;
}

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
  color: var(--ink);
}

.block-container {
  padding: 0.5rem 2.25rem 3.5rem !important;
  max-width: 1380px !important;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(165deg, #0c1222 0%, #152238 50%, #0f172a 100%) !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] h3 {
  color: #f8fafc !important; font-weight: 800 !important; letter-spacing: -0.02em;
}
.sidebar-brand {
  padding: 0.5rem 0 1.25rem; border-bottom: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 1.25rem;
}
.sidebar-brand .logo-text {
  font-size: 1.05rem; font-weight: 800; color: #fff !important; margin: 0;
}
.sidebar-brand .logo-sub {
  font-size: 0.72rem; color: #94a3b8 !important; margin-top: 0.25rem;
}
.sync-time {
  background: rgba(255,255,255,0.06); border-radius: 12px;
  padding: 0.85rem 1rem; margin-top: 1rem; font-size: 0.8rem;
}
.sync-time strong { color: #f1f5f9; display: block; margin-bottom: 0.25rem; }
.pipeline-step {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.78rem; padding: 0.35rem 0; color: #94a3b8 !important;
}
.pipeline-step.done { color: #6ee7b7 !important; }
.pipeline-step.run { color: #fcd34d !important; }
section[data-testid="stSidebar"] .stButton button {
  background: linear-gradient(135deg, var(--groww) 0%, var(--groww-2) 100%) !important;
  color: #fff !important; border: none !important;
  border-radius: 12px !important; font-weight: 700 !important;
  padding: 0.65rem 1rem !important;
  box-shadow: 0 4px 14px rgba(0, 179, 134, 0.35) !important;
}

/* Hero */
.hero-banner {
  background: linear-gradient(120deg, #062a22 0%, #0d3d32 35%, #00a67e 100%);
  border-radius: 24px; padding: 2rem 2.25rem; margin-bottom: 1.75rem;
  color: #fff; position: relative; overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 100, 75, 0.28);
}
.hero-banner::after {
  content: ''; position: absolute; right: -40px; top: -60px;
  width: 280px; height: 280px; border-radius: 50%;
  background: rgba(255,255,255,0.08);
}
.hero-inner { position: relative; z-index: 1; display: flex;
  justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1.5rem; }
.hero-banner h1 {
  margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -0.04em;
}
.hero-banner .sub { margin: 0.5rem 0 0; opacity: 0.88; font-size: 0.95rem; max-width: 520px; }
.hero-stats { display: flex; gap: 1.25rem; flex-wrap: wrap; }
.hero-stat {
  background: rgba(255,255,255,0.12); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.15); border-radius: 14px;
  padding: 0.85rem 1.15rem; min-width: 100px; text-align: center;
}
.hero-stat .num { font-size: 1.5rem; font-weight: 800; line-height: 1; }
.hero-stat .lbl { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em;
  opacity: 0.85; margin-top: 0.35rem; }

/* KPI */
.kpi-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;
  margin-bottom: 1.75rem;
}
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 18px; padding: 1.15rem 1.3rem;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  position: relative; overflow: hidden;
}
.kpi-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--groww), var(--groww-2));
  opacity: 0; transition: opacity 0.2s;
}
.kpi-card:hover::before { opacity: 1; }
.kpi-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(15,23,42,0.09); }
.kpi-card .icon { font-size: 1.35rem; margin-bottom: 0.5rem; }
.kpi-card .label {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--ink-muted); font-weight: 700;
}
.kpi-card .value {
  font-size: 1.85rem; font-weight: 800; letter-spacing: -0.04em;
  margin-top: 0.2rem; line-height: 1;
}
.kpi-card.positive .value { color: var(--ok); }
.kpi-card.negative .value { color: var(--danger); }
.kpi-card.accent .value { color: var(--groww-dark); }

/* Panels */
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 1.35rem 1.45rem;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.05); height: 100%;
}
.panel-title {
  font-size: 1rem; font-weight: 800; margin: 0 0 1.1rem;
  letter-spacing: -0.02em; color: var(--ink);
}
.panel-title span { color: var(--groww-dark); }

.section-head {
  font-size: 1.25rem; font-weight: 800; letter-spacing: -0.03em;
  margin: 2rem 0 1rem; color: var(--ink);
  display: flex; align-items: center; gap: 0.5rem;
}
.section-head .line {
  flex: 1; height: 1px; background: linear-gradient(90deg, var(--border), transparent);
}

.theme-row { margin-bottom: 0.9rem; }
.theme-row .head {
  display: flex; justify-content: space-between; font-size: 0.82rem;
  font-weight: 600; margin-bottom: 0.4rem;
}
.theme-bar {
  height: 10px; background: #f1f5f9; border-radius: 999px; overflow: hidden;
}
.theme-bar-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #00b386 0%, #5eead4 100%);
}

.reviews-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
}
@media (max-width: 900px) { .reviews-grid { grid-template-columns: 1fr; } }
.review-card {
  background: #fff; border: 1px solid var(--border);
  border-radius: 16px; padding: 1.15rem 1.2rem;
  box-shadow: 0 2px 8px rgba(15,23,42,0.03);
  transition: box-shadow 0.2s, border-color 0.2s;
}
.review-card:hover {
  box-shadow: 0 8px 24px rgba(15,23,42,0.08);
  border-color: #cbd5e1;
}
.review-card.neg {
  border-color: #fecaca; background: linear-gradient(135deg, #fff 0%, #fff5f5 100%);
}
.review-card .rating-chip {
  display: inline-block; font-size: 0.68rem; font-weight: 800;
  padding: 0.25rem 0.6rem; border-radius: 8px; margin-bottom: 0.55rem;
  letter-spacing: 0.02em;
}
.review-card .rating-chip.high { background: #d1fae5; color: #047857; }
.review-card .rating-chip.low { background: #fee2e2; color: #b91c1c; }
.review-card .rating-chip.mid { background: #fef3c7; color: #b45309; }
.review-card .stars { color: #f59e0b; letter-spacing: 2px; font-size: 0.9rem; }
.review-card .meta { color: var(--ink-muted); font-size: 0.72rem; margin: 0.4rem 0; }
.review-card .text { font-size: 0.9rem; line-height: 1.55; color: #334155; }

.quote-card {
  background: #fff; border: 1px solid #bbf7d0;
  border-radius: 16px; padding: 1.25rem 1.35rem; margin-bottom: 0.85rem;
  box-shadow: 0 2px 12px rgba(0, 179, 134, 0.08);
  position: relative;
}
.quote-card::before {
  content: '"'; position: absolute; top: 0.5rem; left: 1rem;
  font-size: 2.5rem; color: #a7f3d0; font-weight: 800; line-height: 1;
}
.quote-card .q {
  font-size: 0.95rem; color: #134e4a; line-height: 1.55;
  padding-left: 1.5rem; font-weight: 500;
}
.quote-card .meta { margin-top: 0.75rem; padding-left: 1.5rem;
  font-size: 0.75rem; color: var(--ink-muted); font-weight: 600; }

.action-card {
  border-radius: 16px; padding: 1.2rem 1.25rem;
  border: 1px solid var(--border); background: #fff;
  box-shadow: 0 2px 12px rgba(15,23,42,0.04); height: 100%;
}
.action-card.high { border-top: 3px solid var(--danger); }
.action-card.medium { border-top: 3px solid var(--warn); }
.action-card.low { border-top: 3px solid var(--ok); }
.action-card .pri {
  font-size: 0.65rem; font-weight: 800; letter-spacing: 0.1em;
  text-transform: uppercase; margin-bottom: 0.5rem;
}
.action-card.high .pri { color: var(--danger); }
.action-card.medium .pri { color: var(--warn); }
.action-card.low .pri { color: var(--ok); }
.action-card .desc { font-size: 0.88rem; line-height: 1.5; color: #334155; }

.deliverables {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;
  margin: 1.75rem 0;
}
.deliverable-card {
  background: #fff; border: 1px solid var(--border); border-radius: 18px;
  padding: 1.35rem; text-align: center;
  box-shadow: 0 4px 20px rgba(15,23,42,0.05);
}
.deliverable-card.ready { border-color: #a7f3d0; background: linear-gradient(180deg, #ecfdf5 0%, #fff 100%); }
.deliverable-card .ico { font-size: 1.75rem; margin-bottom: 0.5rem; }
.deliverable-card .title { font-weight: 800; font-size: 0.95rem; color: var(--ink); }
.deliverable-card .status { font-size: 0.78rem; color: var(--ink-muted); margin-top: 0.35rem; }

.wow-banner {
  background: linear-gradient(135deg, #fff 0%, #ecfdf5 100%);
  border: 1px solid #a7f3d0; border-radius: 18px;
  padding: 1.15rem 1.35rem; margin-bottom: 1.5rem;
  box-shadow: 0 4px 18px rgba(0, 179, 134, 0.08);
}
.wow-banner .wow-title {
  font-size: 0.72rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--groww-dark); margin-bottom: 0.45rem;
}
.wow-banner .wow-headline { font-size: 1rem; font-weight: 700; color: var(--ink); line-height: 1.45; }
.wow-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.wow-chip {
  font-size: 0.72rem; font-weight: 700; padding: 0.35rem 0.65rem;
  border-radius: 999px; background: #f0fdf4; color: #047857; border: 1px solid #bbf7d0;
}
.wow-chip.down { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.wow-chip.neu { background: #f8fafc; color: #475569; border-color: #e2e8f0; }

.product-map-hint {
  font-size: 0.72rem; color: var(--ink-muted); margin: -0.5rem 0 0.75rem;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 6px; background: #fff; padding: 8px; border-radius: 14px;
  border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px; font-weight: 700; font-size: 0.8rem; padding: 0.55rem 1.1rem;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #ecfdf5, #d1fae5) !important;
  color: var(--groww-dark) !important;
}
div[data-testid="stPlotlyChart"] { border-radius: 14px; overflow: hidden; }

div[data-testid="stAlert"] { border-radius: 12px; }
</style>
"""


def inject_styles() -> None:
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
          <p class="logo-text">Groww Insights</p>
          <p class="logo-sub">Weekly Play Store pulse</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_sync(last_sync: str | None) -> None:
    if last_sync:
        st.markdown(
            f'<div class="sync-time"><strong>Last updated</strong>{html.escape(last_sync)}</div>',
            unsafe_allow_html=True,
        )


def render_pipeline_steps(steps: dict[int, str]) -> None:
    labels = {1: "Ingest reviews", 2: "Analyze themes", 3: "Publish report", 4: "Prepare email"}
    rows = []
    for n in range(1, 5):
        state = steps.get(n, "pending")
        cls = {"done": "done", "running": "run"}.get(state, "")
        mark = {"done": "●", "running": "◐", "error": "✕", "skipped": "○"}.get(state, "○")
        rows.append(f'<div class="pipeline-step {cls}">{mark} {labels[n]}</div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_hero(week: str, total: int, analysed: int, pos_pct: int) -> None:
    st.markdown(
        f"""
        <div class="hero-banner">
          <div class="hero-inner">
            <div>
              <h1>Review Intelligence</h1>
              <p class="sub">Real user feedback from Google Play, distilled into themes,
              actions, and a shareable weekly report for product teams.</p>
            </div>
            <div class="hero-stats">
              <div class="hero-stat">
                <div class="num">{html.escape(week)}</div>
                <div class="lbl">Reporting week</div>
              </div>
              <div class="hero-stat">
                <div class="num">{analysed}</div>
                <div class="lbl">Reviews analysed</div>
              </div>
              <div class="hero-stat">
                <div class="num">{pos_pct}%</div>
                <div class="lbl">Positive sentiment</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_head(title: str) -> None:
    st.markdown(
        f'<div class="section-head">{html.escape(title)}<span class="line"></span></div>',
        unsafe_allow_html=True,
    )


def render_kpis(total: int, analysed: int, pos: int, neg: int, neu: int) -> None:
    cards = [
        ("📚", "In library", str(total), ""),
        ("🔍", "This week", str(analysed), "accent"),
        ("👍", "Positive", str(pos), "positive"),
        ("👎", "Critical", str(neg), "negative"),
        ("➖", "Neutral", str(neu), ""),
    ]
    inner = "".join(
        f'<div class="kpi-card {cls}"><div class="icon">{icon}</div>'
        f'<div class="label">{html.escape(lbl)}</div>'
        f'<div class="value">{html.escape(val)}</div></div>'
        for icon, lbl, val, cls in cards
    )
    st.markdown(f'<div class="kpi-grid">{inner}</div>', unsafe_allow_html=True)


def sentiment_donut(pos: int, neg: int, neu: int) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positive", "Negative", "Neutral"],
                values=[pos, neg, neu],
                hole=0.68,
                marker=dict(
                    colors=["#10b981", "#ef4444", "#cbd5e1"],
                    line=dict(color="#fff", width=3),
                ),
                textinfo="percent",
                textfont=dict(size=13, family="Plus Jakarta Sans", color="#0f172a"),
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )
    total = pos + neg + neu
    center = f"{int(100 * pos / total)}%" if total else "—"
    fig.add_annotation(
        text=f"<b>{center}</b><br><span style='font-size:11px'>positive</span>",
        x=0.5, y=0.5, font_size=14, showarrow=False,
    )
    fig.update_layout(
        margin=dict(l=8, r=8, t=8, b=8),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#64748b"),
    )
    return fig


def rating_bars(dist: dict[int, int]) -> go.Figure:
    stars = list(range(5, 0, -1))
    counts = [dist.get(s, 0) for s in stars]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=[f"{s} star" for s in stars],
            orientation="h",
            marker=dict(color=["#00b386", "#34d399", "#6ee7b7", "#fcd34d", "#ef4444"][::-1]),
            text=counts,
            textposition="outside",
            textfont=dict(family="Plus Jakarta Sans", size=11),
        )
    )
    fig.update_layout(
        margin=dict(l=8, r=36, t=8, b=8),
        height=300,
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", size=11, color="#64748b"),
    )
    return fig


def render_wow_pulse(wow: dict) -> None:
    """Week-over-week change summary."""
    headline = html.escape(wow.get("headline", ""))
    chips = []
    sd = wow.get("sentiment_delta") or {}
    delta = sd.get("positive_pct_delta", 0)
    if wow.get("has_prior_week") and delta != 0:
        cls = "wow-chip" if delta > 0 else "wow-chip down"
        sign = "+" if delta > 0 else ""
        chips.append(f'<span class="{cls}">Sentiment {sign}{delta} pts</span>')
    for t in wow.get("rising_themes") or []:
        chips.append(
            f'<span class="wow-chip">↑ {html.escape(t["name"])} (+{t["delta"]})</span>'
        )
    for name in wow.get("new_themes") or []:
        chips.append(f'<span class="wow-chip neu">New: {html.escape(name)}</span>')
    chip_html = f'<div class="wow-chips">{"".join(chips)}</div>' if chips else ""
    st.markdown(
        f'<div class="wow-banner"><div class="wow-title">Week over week</div>'
        f'<div class="wow-headline">{headline}</div>{chip_html}</div>',
        unsafe_allow_html=True,
    )


def product_map_chart(area_counts: dict[str, int]) -> go.Figure:
    """Horizontal bar chart of all Groww product areas."""
    from shared.groww_product_map import GROWW_PRODUCT_AREAS

    areas = list(GROWW_PRODUCT_AREAS)
    counts = [area_counts.get(a, 0) for a in areas]
    colors = ["#00b386" if c > 0 else "#e2e8f0" for c in counts]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=areas,
            orientation="h",
            marker=dict(color=colors),
            text=counts,
            textposition="outside",
            textfont=dict(size=10, family="Plus Jakarta Sans"),
        )
    )
    fig.update_layout(
        margin=dict(l=8, r=40, t=8, b=8),
        height=340,
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False, title=""),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", size=10, color="#64748b"),
    )
    return fig


def render_themes(themes: list[dict]) -> None:
    if not themes:
        st.caption("Product-area breakdown will appear after the next sync.")
        return
    max_count = max((t.get("review_count", 0) for t in themes), default=1) or 1
    rows = []
    for theme in themes[:6]:
        name = html.escape(theme.get("name", "Theme"))
        count = theme.get("review_count", 0)
        sent = html.escape(str(theme.get("sentiment", "")).title())
        pct = max(8, int(100 * count / max_count))
        rows.append(
            f'<div class="theme-row"><div class="head"><span>{name}</span>'
            f'<span>{count} reviews · {sent}</span></div>'
            f'<div class="theme-bar"><div class="theme-bar-fill" style="width:{pct}%"></div></div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def _rating_chip_class(rating: int) -> str:
    if rating >= 4:
        return "high"
    if rating <= 2:
        return "low"
    return "mid"


def review_card_html(review: dict, negative: bool = False) -> str:
    date_str = html.escape((review.get("date") or "")[:10])
    raw = review.get("text") or review.get("title") or ""
    if len(raw) > 240:
        raw = raw[:237] + "…"
    text = html.escape(raw)
    rating = int(review.get("rating") or 0)
    stars = "★" * rating + "☆" * (5 - rating)
    chip = _rating_chip_class(rating)
    cls = "review-card neg" if negative else "review-card"
    return (
        f'<div class="{cls}">'
        f'<span class="rating-chip {chip}">{rating} / 5</span> '
        f'<span class="stars">{stars}</span>'
        f'<div class="meta">{date_str} · Google Play Store</div>'
        f'<div class="text">{text}</div></div>'
    )


def render_reviews_grid(reviews: list[dict], negative: bool = False) -> None:
    if not reviews:
        st.caption("No reviews in this view yet.")
        return
    st.markdown(
        '<div class="reviews-grid">'
        + "".join(review_card_html(r, negative) for r in reviews)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_quotes(quotes: list[dict]) -> None:
    if not quotes:
        st.caption("Highlighted quotes appear after analysis.")
        return
    for q in quotes:
        qt = html.escape(q.get("text", ""))
        tn = html.escape(q.get("theme_name", ""))
        rating = q.get("rating", "?")
        st.markdown(
            f'<div class="quote-card"><div class="q">{qt}</div>'
            f'<div class="meta">{rating} stars · {tn}</div></div>',
            unsafe_allow_html=True,
        )


def render_actions(actions: list[dict]) -> None:
    if not actions:
        st.caption("Recommended actions appear after analysis.")
        return
    cols = st.columns(min(len(actions), 3))
    for i, action in enumerate(actions[:3]):
        pri = (action.get("priority") or "medium").lower()
        desc = html.escape(action.get("description", ""))
        with cols[i % len(cols)]:
            st.markdown(
                f'<div class="action-card {pri}">'
                f'<div class="pri">{pri} priority</div>'
                f'<div class="desc">{desc}</div></div>',
                unsafe_allow_html=True,
            )


def render_deliverables(doc_ready: bool, mail_ready: bool) -> None:
    doc_cls = "deliverable-card ready" if doc_ready else "deliverable-card"
    mail_cls = "deliverable-card ready" if mail_ready else "deliverable-card"
    st.markdown(
        f"""
        <div class="deliverables">
          <div class="{doc_cls}">
            <div class="ico">📄</div>
            <div class="title">Weekly report</div>
            <div class="status">{"Ready in Google Docs" if doc_ready else "Syncing…"}</div>
          </div>
          <div class="{mail_cls}">
            <div class="ico">✉️</div>
            <div class="title">Email draft</div>
            <div class="status">{"Ready in Gmail" if mail_ready else "After report sync"}</div>
          </div>
          <div class="deliverable-card ready">
            <div class="ico">📱</div>
            <div class="title">Play Store</div>
            <div class="status">Live listing</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
