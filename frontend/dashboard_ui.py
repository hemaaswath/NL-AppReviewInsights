"""Premium dashboard styling and render helpers for Streamlit."""
from __future__ import annotations

import html
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ── Global CSS ────────────────────────────────────────────────────────────────

DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --groww: #00b386;
  --groww-dark: #00956f;
  --groww-glow: rgba(0, 179, 134, 0.15);
  --ink: #0f172a;
  --ink-muted: #64748b;
  --surface: #ffffff;
  --surface-2: #f8fafc;
  --border: #e2e8f0;
  --danger: #ef4444;
  --warn: #f59e0b;
  --ok: #10b981;
}

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
  color: var(--ink);
}

.block-container {
  padding: 1rem 2rem 3rem !important;
  max-width: 1320px !important;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stButton button {
  background: var(--groww) !important; color: #fff !important;
  border: none !important; border-radius: 10px !important; font-weight: 600 !important;
}

/* Top bar */
.app-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.85rem 1.25rem; margin: -1rem -2rem 1.75rem;
  background: var(--surface); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 99;
}
.app-brand { display: flex; align-items: center; gap: 0.75rem; }
.app-logo {
  width: 42px; height: 42px; border-radius: 12px;
  background: linear-gradient(135deg, var(--groww) 0%, #34d399 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.25rem; box-shadow: 0 4px 14px var(--groww-glow);
}
.app-brand h2 { margin: 0; font-size: 1.15rem; font-weight: 800; letter-spacing: -0.03em; }
.app-brand span { font-size: 0.78rem; color: var(--ink-muted); font-weight: 500; }
.badge-week {
  background: #ecfdf5; color: var(--groww-dark); padding: 0.35rem 0.85rem;
  border-radius: 999px; font-size: 0.8rem; font-weight: 700;
  border: 1px solid #a7f3d0;
}
.badge-live {
  background: #fef3c7; color: #b45309; padding: 0.35rem 0.75rem;
  border-radius: 999px; font-size: 0.75rem; font-weight: 600;
}

/* KPI grid */
.kpi-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;
  margin-bottom: 1.5rem;
}
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 1.1rem 1.25rem;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15,23,42,0.08);
}
.kpi-card .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--ink-muted); font-weight: 600; margin-bottom: 0.35rem; }
.kpi-card .value { font-size: 1.75rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }
.kpi-card.positive .value { color: var(--ok); }
.kpi-card.negative .value { color: var(--danger); }
.kpi-card.accent .value { color: var(--groww-dark); }

/* Panels */
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 18px; padding: 1.25rem 1.35rem;
  box-shadow: 0 1px 3px rgba(15,23,42,0.05); height: 100%;
}
.panel-title {
  font-size: 0.95rem; font-weight: 700; margin: 0 0 1rem;
  display: flex; align-items: center; gap: 0.5rem;
}
.panel-title::before {
  content: ''; width: 4px; height: 1.1rem; background: var(--groww);
  border-radius: 4px;
}

/* Theme bars */
.theme-row { margin-bottom: 0.85rem; }
.theme-row .head {
  display: flex; justify-content: space-between; font-size: 0.82rem;
  font-weight: 600; margin-bottom: 0.35rem;
}
.theme-bar {
  height: 8px; background: #f1f5f9; border-radius: 999px; overflow: hidden;
}
.theme-bar-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, var(--groww) 0%, #34d399 100%);
}

/* Review cards */
.reviews-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
@media (max-width: 900px) { .reviews-grid { grid-template-columns: 1fr; } }
.review-card {
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 14px; padding: 1rem 1.1rem; position: relative;
}
.review-card.neg { border-color: #fecaca; background: #fffbfb; }
.review-card .rating-chip {
  display: inline-block; font-size: 0.7rem; font-weight: 700;
  padding: 0.2rem 0.55rem; border-radius: 6px; margin-bottom: 0.5rem;
}
.review-card .rating-chip.high { background: #d1fae5; color: #047857; }
.review-card .rating-chip.low { background: #fee2e2; color: #b91c1c; }
.review-card .rating-chip.mid { background: #fef3c7; color: #b45309; }
.review-card .stars { color: #fbbf24; letter-spacing: 1px; font-size: 0.85rem; }
.review-card .meta { color: var(--ink-muted); font-size: 0.72rem; margin: 0.35rem 0; }
.review-card .text { font-size: 0.88rem; line-height: 1.5; color: #334155; }

.quote-card {
  background: linear-gradient(135deg, #ecfdf5 0%, #f8fafc 100%);
  border: 1px solid #a7f3d0; border-radius: 14px;
  padding: 1.15rem 1.25rem; margin-bottom: 0.75rem;
}
.quote-card .q { font-size: 0.95rem; font-style: italic; color: #134e4a; line-height: 1.5; }
.quote-card .meta { margin-top: 0.65rem; font-size: 0.75rem; color: var(--ink-muted); }

/* Actions */
.action-card {
  border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: 0.75rem;
  border: 1px solid var(--border); background: var(--surface);
}
.action-card.high { border-left: 4px solid var(--danger); }
.action-card.medium { border-left: 4px solid var(--warn); }
.action-card.low { border-left: 4px solid var(--ok); }
.action-card .pri {
  font-size: 0.68rem; font-weight: 800; letter-spacing: 0.08em;
  text-transform: uppercase; margin-bottom: 0.35rem;
}
.action-card.high .pri { color: var(--danger); }
.action-card.medium .pri { color: var(--warn); }
.action-card.low .pri { color: var(--ok); }

/* CTA strip */
.cta-strip {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;
  margin-top: 1.5rem; padding: 1.25rem;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
  border-radius: 18px;
}
.cta-strip .cta-item {
  text-align: center; color: #e2e8f0; font-size: 0.85rem;
}
.cta-strip .cta-item strong { display: block; color: #fff; font-size: 0.95rem; margin-bottom: 0.25rem; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: var(--surface-2);
  padding: 6px; border-radius: 12px; border: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
  border-radius: 8px; font-weight: 600; font-size: 0.82rem;
  padding: 0.5rem 1rem;
}
.stTabs [aria-selected="true"] { background: var(--surface) !important;
  color: var(--groww-dark) !important; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

div[data-testid="stPlotlyChart"] { border-radius: 12px; overflow: hidden; }
</style>
"""


def inject_styles() -> None:
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


def render_topbar(week: str, syncing: bool = False) -> None:
    live = "Syncing…" if syncing else "Live"
    live_cls = "badge-live" if syncing else "badge-week"
    st.markdown(
        f"""
        <div class="app-topbar">
          <div class="app-brand">
            <div class="app-logo">📈</div>
            <div>
              <h2>Groww Review Pulse</h2>
              <span>Google Play insights · auto-synced pipeline</span>
            </div>
          </div>
          <div style="display:flex;gap:0.65rem;align-items:center;">
            <span class="badge-week">Week {html.escape(week)}</span>
            <span class="{live_cls}">{html.escape(live)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(total: int, analysed: int, pos: int, neg: int, neu: int) -> None:
    cards = [
        ("Total reviews", str(total), ""),
        ("Analysed", str(analysed), "accent"),
        ("Positive", str(pos), "positive"),
        ("Negative", str(neg), "negative"),
        ("Neutral", str(neu), ""),
    ]
    inner = "".join(
        f'<div class="kpi-card {cls}"><div class="label">{html.escape(lbl)}</div>'
        f'<div class="value">{html.escape(val)}</div></div>'
        for lbl, val, cls in cards
    )
    st.markdown(f'<div class="kpi-grid">{inner}</div>', unsafe_allow_html=True)


def sentiment_donut(pos: int, neg: int, neu: int) -> go.Figure:
    labels = ["Positive", "Negative", "Neutral"]
    values = [pos, neg, neu]
    colors = ["#10b981", "#ef4444", "#94a3b8"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="#fff", width=2)),
                textinfo="percent",
                textfont=dict(size=12, family="Plus Jakarta Sans"),
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=280,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
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
            y=[f"{s} ★" for s in stars],
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, "#e2e8f0"], [0.5, "#6ee7b7"], [1, "#00b386"]],
            ),
            text=counts,
            textposition="outside",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=30, t=10, b=10),
        height=280,
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title=""),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", size=11, color="#64748b"),
    )
    return fig


def render_themes(themes: list[dict]) -> None:
    if not themes:
        st.caption("Themes appear after analysis.")
        return
    max_count = max((t.get("review_count", 0) for t in themes), default=1) or 1
    rows = []
    for theme in themes[:6]:
        name = html.escape(theme.get("name", "Theme"))
        count = theme.get("review_count", 0)
        sent = html.escape(str(theme.get("sentiment", "")))
        pct = int(100 * count / max_count)
        rows.append(
            f'<div class="theme-row"><div class="head"><span>{name}</span>'
            f'<span>{count} · {sent}</span></div>'
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
    if len(raw) > 220:
        raw = raw[:217] + "…"
    text = html.escape(raw)
    rating = int(review.get("rating") or 0)
    stars = "★" * rating + "☆" * (5 - rating)
    chip = _rating_chip_class(rating)
    cls = "review-card neg" if negative else "review-card"
    return (
        f'<div class="{cls}">'
        f'<span class="rating-chip {chip}">{rating}/5</span> '
        f'<span class="stars">{stars}</span>'
        f'<div class="meta">{date_str} · Google Play</div>'
        f'<div class="text">{text}</div></div>'
    )


def render_reviews_grid(reviews: list[dict], negative: bool = False) -> None:
    if not reviews:
        st.caption("No reviews in this category yet.")
        return
    st.markdown(
        '<div class="reviews-grid">'
        + "".join(review_card_html(r, negative) for r in reviews)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_quotes(quotes: list[dict]) -> None:
    if not quotes:
        st.caption("AI highlights appear after analysis.")
        return
    for q in quotes:
        qt = html.escape(q.get("text", ""))
        tn = html.escape(q.get("theme_name", ""))
        rating = q.get("rating", "?")
        st.markdown(
            f'<div class="quote-card"><div class="q">"{qt}"</div>'
            f'<div class="meta">{rating}★ · {tn}</div></div>',
            unsafe_allow_html=True,
        )


def render_actions(actions: list[dict]) -> None:
    if not actions:
        st.caption("Action items appear after analysis.")
        return
    cols = st.columns(min(len(actions), 3))
    for i, action in enumerate(actions[:3]):
        pri = (action.get("priority") or "medium").lower()
        desc = html.escape(action.get("description", ""))
        with cols[i % len(cols)]:
            st.markdown(
                f'<div class="action-card {pri}">'
                f'<div class="pri">{pri}</div><div>{desc}</div></div>',
                unsafe_allow_html=True,
            )


def render_cta_strip(doc_url: str | None, email_id: str | None, play_url: str) -> None:
    doc_txt = "Report ready" if doc_url else "Pending sync"
    mail_txt = "Draft in Gmail" if email_id else "Set EMAIL_RECIPIENT"
    st.markdown(
        f"""
        <div class="cta-strip">
          <div class="cta-item"><strong>📄 Weekly report</strong>{html.escape(doc_txt)}</div>
          <div class="cta-item"><strong>✉️ Distribution</strong>{html.escape(mail_txt)}</div>
          <div class="cta-item"><strong>📱 Play Store</strong>com.groww</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
