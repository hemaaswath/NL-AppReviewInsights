"""Collect Google Play reviews into SQLite (incremental, deduped)."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from google_play_scraper import Sort, reviews as fetch_reviews

from shared.database import DatabaseManager
from shared.models import ReviewSource
from shared.play_store_config import resolve_play_package, validate_finance_package
from shared.review_normalizer import normalize_review_fields

# Full sweep for first-time / empty DB
FULL_FETCH_CONFIGS = [
    ("en", "in", Sort.NEWEST),
    ("en", "in", Sort.MOST_RELEVANT),
    ("en", "us", Sort.NEWEST),
    ("en", "us", Sort.MOST_RELEVANT),
    ("en", "gb", Sort.MOST_RELEVANT),
    ("en", "au", Sort.MOST_RELEVANT),
]

# Quick check on refresh — newest India storefront only
FAST_FETCH_CONFIGS = [
    ("en", "in", Sort.NEWEST),
]


def collect_play_reviews(
    database_path: str | None = None,
    *,
    fast: bool = False,
    count: int = 100,
) -> dict:
    """
    Fetch Play Store reviews and save new ones to the database.

    Returns:
        dict with keys: ok, new_reviews, total_reviews, package_name
    """
    package = resolve_play_package()
    ok, app_info = validate_finance_package(package)
    if not ok:
        return {
            "ok": False,
            "new_reviews": 0,
            "total_reviews": 0,
            "package_name": package,
            "detail": app_info,
        }

    configs = FAST_FETCH_CONFIGS if fast else FULL_FETCH_CONFIGS
    db = DatabaseManager(database_path)
    new_saved = 0

    try:
        for lang, country, sort_order in configs:
            try:
                result, _ = fetch_reviews(
                    package,
                    lang=lang,
                    country=country,
                    sort=sort_order,
                    count=count if fast else min(count, 100),
                )
            except Exception:
                continue

            if not result:
                continue

            batch: list[dict] = []
            for r in result:
                rating = r.get("score", 0)
                if rating == 0:
                    continue

                normalized = normalize_review_fields(
                    r.get("title", "") or "", r.get("content", "")
                )
                if not normalized:
                    continue
                title, text = normalized

                at_dt = r.get("at")
                if isinstance(at_dt, datetime):
                    date = at_dt if at_dt.tzinfo else at_dt.replace(tzinfo=timezone.utc)
                else:
                    date = datetime.now(timezone.utc)

                review_id_raw = r.get("reviewId", "")
                review_id = (
                    hashlib.md5(review_id_raw.encode()).hexdigest()
                    if review_id_raw
                    else hashlib.md5(
                        f"{package}_{r.get('userName', '')}_{date.isoformat()}".encode()
                    ).hexdigest()
                )

                batch.append(
                    {
                        "id": review_id,
                        "source": ReviewSource.GOOGLE_PLAY.value,
                        "rating": rating,
                        "title": title,
                        "text": text,
                        "date": date.isoformat(),
                        "version": r.get("appVersion", "")
                        or r.get("reviewCreatedVersion", "")
                        or "",
                        "processed": False,
                    }
                )

            if batch:
                new_saved += db.save_reviews_batch(batch)

        total = db.get_review_count("google_play")
    finally:
        db.close()

    return {
        "ok": True,
        "new_reviews": new_saved,
        "total_reviews": total,
        "package_name": package,
        "detail": app_info,
        "fast": fast,
    }
