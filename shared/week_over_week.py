"""
Week-over-week delta between stored weekly insights snapshots.
"""
from __future__ import annotations

from typing import Any, Optional


def _iso_week_sort_key(week: str) -> tuple[int, int]:
    try:
        year_s, w_s = week.upper().split("-W")
        return int(year_s), int(w_s)
    except ValueError:
        return (0, 0)


def previous_week_id(week: str) -> str:
    """ISO week string for the calendar week before `week`."""
    from datetime import datetime, timedelta

    try:
        year_s, w_s = week.upper().split("-W")
        dt = datetime.strptime(f"{year_s}-W{w_s}-1", "%G-W%V-%u")
        prev = dt - timedelta(days=7)
        return prev.strftime("%G-W%V")
    except ValueError:
        return week


def _theme_counts(themes: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in themes or []:
        name = (t.get("name") or "Unknown").strip()
        out[name] = out.get(name, 0) + int(t.get("review_count", 0))
    return out


def _positive_pct(summary: dict) -> int:
    pos = summary.get("positive", 0)
    neg = summary.get("negative", 0)
    neu = summary.get("neutral", 0)
    total = pos + neg + neu
    return int(round(100 * pos / total)) if total else 0


def compute_week_over_week(
    current: Optional[dict],
    prior: Optional[dict],
) -> dict[str, Any]:
    """
    Build WoW pulse for dashboard and reports.

    Returns dict with headline, sentiment_delta, rising_themes, new_themes, etc.
    """
    if not current:
        return {
            "has_prior_week": False,
            "headline": "Run a second weekly sync to unlock week-over-week trends.",
            "prior_week": None,
            "current_week": None,
            "sentiment_delta": {},
            "rising_themes": [],
            "falling_themes": [],
            "new_themes": [],
            "stable_top": [],
        }

    cur_week = current.get("week")
    cur_sent = current.get("sentiment_summary") or {}
    cur_themes = _theme_counts(current.get("themes") or [])
    cur_pos_pct = _positive_pct(cur_sent)

    if not prior:
        prior_week = previous_week_id(cur_week) if cur_week else None
        return {
            "has_prior_week": False,
            "headline": (
                f"No saved insights for {prior_week or 'last week'} yet. "
                "After next week's sync, you'll see what changed."
            ),
            "prior_week": prior_week,
            "current_week": cur_week,
            "sentiment_delta": {
                "positive_pct": cur_pos_pct,
                "positive_pct_delta": 0,
            },
            "rising_themes": [],
            "falling_themes": [],
            "new_themes": [],
            "stable_top": sorted(cur_themes.items(), key=lambda x: x[1], reverse=True)[:3],
        }

    prior_week = prior.get("week")
    prior_sent = prior.get("sentiment_summary") or {}
    prior_themes = _theme_counts(prior.get("themes") or [])
    prior_pos_pct = _positive_pct(prior_sent)

    pos_delta = cur_pos_pct - prior_pos_pct
    all_names = set(cur_themes) | set(prior_themes)
    deltas: list[dict] = []
    for name in all_names:
        cur_c = cur_themes.get(name, 0)
        pri_c = prior_themes.get(name, 0)
        delta = cur_c - pri_c
        if cur_c > 0 or pri_c > 0:
            deltas.append(
                {
                    "name": name,
                    "current": cur_c,
                    "prior": pri_c,
                    "delta": delta,
                }
            )

    rising = sorted(
        [d for d in deltas if d["delta"] > 0],
        key=lambda x: x["delta"],
        reverse=True,
    )[:3]
    falling = sorted(
        [d for d in deltas if d["delta"] < 0],
        key=lambda x: x["delta"],
    )[:3]
    new_themes = [d["name"] for d in deltas if d["prior"] == 0 and d["current"] > 0]

    headline = _build_headline(pos_delta, rising, new_themes, cur_week, prior_week)

    return {
        "has_prior_week": True,
        "headline": headline,
        "prior_week": prior_week,
        "current_week": cur_week,
        "sentiment_delta": {
            "positive_pct": cur_pos_pct,
            "positive_pct_delta": pos_delta,
            "positive": cur_sent.get("positive", 0) - prior_sent.get("positive", 0),
            "negative": cur_sent.get("negative", 0) - prior_sent.get("negative", 0),
        },
        "rising_themes": rising,
        "falling_themes": falling,
        "new_themes": new_themes[:3],
        "stable_top": sorted(cur_themes.items(), key=lambda x: x[1], reverse=True)[:3],
    }


def _build_headline(
    pos_delta: int,
    rising: list[dict],
    new_themes: list[str],
    cur_week: str | None,
    prior_week: str | None,
) -> str:
    parts: list[str] = []
    if pos_delta > 2:
        parts.append(f"Positive sentiment up {pos_delta} pts vs {prior_week}")
    elif pos_delta < -2:
        parts.append(f"Positive sentiment down {abs(pos_delta)} pts vs {prior_week}")
    else:
        parts.append(f"Sentiment stable vs {prior_week}")

    if rising:
        top = rising[0]
        parts.append(
            f"biggest rise: {top['name']} (+{top['delta']} review mentions)"
        )
    elif new_themes:
        parts.append(f"new focus area: {new_themes[0]}")
    return " · ".join(parts) + f" ({cur_week})."
