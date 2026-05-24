"""Google Play package resolution for Groww (finance vs plant app)."""
from __future__ import annotations

import os
from functools import lru_cache

# Wrong ID — gardening app "Groww - Plant Care"
PLANT_APP_PACKAGE = "com.groww"
# Correct ID — "Groww Stocks, Mutual Fund, Gold"
FINANCE_APP_PACKAGE = "com.nextbillion.groww"


def resolve_play_package(explicit: str | None = None) -> str:
    """
    Return the Play package to scrape. Auto-corrects com.groww -> com.nextbillion.groww.
    """
    raw = (explicit or os.getenv("GOOGLE_PLAY_PACKAGE_NAME") or FINANCE_APP_PACKAGE).strip()
    if raw == PLANT_APP_PACKAGE:
        return FINANCE_APP_PACKAGE
    return raw


def play_app_metadata(package: str) -> dict:
    """Fetch title/genre from Play Store (no reviews)."""
    from google_play_scraper import app as play_app

    return play_app(package, lang="en", country="in")


def validate_finance_package(package: str) -> tuple[bool, str]:
    """
    Return (ok, message). Fails if package is the known plant app or non-Finance genre.
    Cached per process to avoid Play Store HTTP on every Streamlit rerun.
    """
    return _validate_finance_package_cached(package)


@lru_cache(maxsize=4)
def _validate_finance_package_cached(package: str) -> tuple[bool, str]:
    if package == PLANT_APP_PACKAGE:
        return False, (
            f"{PLANT_APP_PACKAGE} is the plant-care app, not Groww Stocks. "
            f"Use {FINANCE_APP_PACKAGE}."
        )
    try:
        meta = play_app_metadata(package)
    except Exception as exc:
        return False, f"Could not resolve Play Store app {package}: {exc}"

    title = meta.get("title", "Unknown")
    genre = (meta.get("genre") or "").lower()
    summary = (meta.get("summary") or "")[:120]

    if "plant" in summary.lower() or "garden" in summary.lower():
        return False, f"Wrong app: {title} — {summary}"

    if genre and genre not in ("finance", "business", ""):
        if genre in ("lifestyle", "house & home", "tools"):
            return False, f"Wrong app genre ({genre}): {title}. Expected Finance."

    return True, f"{title} ({genre or 'Play Store'}) — {summary}"
