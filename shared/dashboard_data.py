"""Instant dashboard data: live SQLite or bundled seed snapshot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from shared.week_over_week import compute_week_over_week

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "dashboard_seed.json"


def load_seed_snapshot() -> dict:
    """Bundled snapshot for instant first paint (Streamlit Cloud cold starts)."""
    if not SEED_PATH.is_file():
        return _empty_snapshot()
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    data.setdefault("insights", {})
    data.setdefault("prior_insights", None)
    data.setdefault("total", 0)
    data.setdefault("positive", [])
    data.setdefault("negative", [])
    data.setdefault("recent", [])
    data.setdefault("rating_dist", {i: 0 for i in range(1, 6)})
    data["wow"] = compute_week_over_week(data.get("insights"), data.get("prior_insights"))
    return data


def _empty_snapshot() -> dict:
    return {
        "insights": None,
        "prior_insights": None,
        "total": 0,
        "positive": [],
        "negative": [],
        "recent": [],
        "rating_dist": {i: 0 for i in range(1, 6)},
        "wow": compute_week_over_week(None, None),
    }


def has_live_data(snap: dict) -> bool:
    return bool(snap.get("total", 0) > 0 and snap.get("insights"))


def resolve_dashboard(live: dict | None) -> tuple[dict, Literal["live", "seed"]]:
    """Prefer live DB; fall back to seed so the UI is never blank."""
    if live and has_live_data(live):
        return live, "live"
    seed = load_seed_snapshot()
    if has_live_data(seed):
        return seed, "seed"
    return live or seed, "live" if live and has_live_data(live) else "seed"
