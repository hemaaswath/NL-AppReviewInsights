"""
Script to collect Google Play reviews for Groww across multiple
sort orders, countries, and languages to maximise real review coverage.
"""
import os
import sys
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, '.')
sys.path.insert(0, 'phase-1/src')

from dotenv import load_dotenv
from google_play_scraper import Sort, reviews as fetch_reviews
from shared.database import DatabaseManager
from shared.models import ReviewSource
from shared.play_store_config import resolve_play_package, validate_finance_package
from shared.review_normalizer import normalize_review_fields

load_dotenv()

PACKAGE_NAME = resolve_play_package()
ok, app_info = validate_finance_package(PACKAGE_NAME)
if not ok:
    raise SystemExit(f"Wrong Google Play app configured:\n  {app_info}\n  Set GOOGLE_PLAY_PACKAGE_NAME=com.nextbillion.groww")
print(f"Collecting reviews for: {app_info}")
print(f"Package: {PACKAGE_NAME}")

# Combinations to try: (lang, country, sort_label, Sort)
# English storefronts only — Hindi/other locales filtered at normalization too
FETCH_CONFIGS = [
    ('en', 'in',  'NEWEST',       Sort.NEWEST),
    ('en', 'in',  'MOST_RELEVANT', Sort.MOST_RELEVANT),
    ('en', 'us',  'NEWEST',       Sort.NEWEST),
    ('en', 'us',  'MOST_RELEVANT', Sort.MOST_RELEVANT),
    ('en', 'gb',  'MOST_RELEVANT', Sort.MOST_RELEVANT),
    ('en', 'au',  'MOST_RELEVANT', Sort.MOST_RELEVANT),
]

db = DatabaseManager('data/reviews.db')
grand_total_saved = 0

for lang, country, sort_label, sort_order in FETCH_CONFIGS:
    print(f"\n{'='*60}")
    print(f"Fetching: lang={lang}, country={country}, sort={sort_label}")
    print(f"{'='*60}")

    try:
        result, _ = fetch_reviews(
            PACKAGE_NAME,
            lang=lang,
            country=country,
            sort=sort_order,
            count=100,
        )
    except Exception as e:
        print(f"  ERROR: {e}")
        continue

    if not result:
        print("  No results returned.")
        continue

    print(f"  API returned {len(result)} reviews")

    batch_data = []
    skipped = 0
    for r in result:
        rating = r.get('score', 0)
        if rating == 0:
            continue

        normalized = normalize_review_fields(r.get('title', '') or '', r.get('content', ''))
        if not normalized:
            skipped += 1
            continue
        title, text = normalized

        at_dt = r.get('at')
        if isinstance(at_dt, datetime):
            date = at_dt if at_dt.tzinfo else at_dt.replace(tzinfo=timezone.utc)
        else:
            date = datetime.now(timezone.utc)

        review_id_raw = r.get('reviewId', '')
        review_id = (
            hashlib.md5(review_id_raw.encode()).hexdigest()
            if review_id_raw
            else hashlib.md5(
                f"{PACKAGE_NAME}_{r.get('userName','')}_{date.isoformat()}".encode()
            ).hexdigest()
        )

        batch_data.append({
            'id': review_id,
            'source': ReviewSource.GOOGLE_PLAY.value,
            'rating': rating,
            'title': title,
            'text': text,
            'date': date.isoformat(),
            'version': r.get('appVersion', '') or r.get('reviewCreatedVersion', '') or '',
            'processed': False
        })

    if batch_data:
        saved = db.save_reviews_batch(batch_data)
        grand_total_saved += saved
        print(
            f"  Valid reviews: {len(batch_data)} | Skipped (normalize): {skipped} | "
            f"New saved (deduped): {saved}"
        )

        # Show a couple of samples from this batch
        for rev in batch_data[:2]:
            print(f"    [{rev['rating']}star] {rev['date'][:10]} | {rev['text'][:80]}")
    else:
        print("  No valid reviews after filtering.")

print(f"\n{'='*60}")
print(f"COLLECTION COMPLETE")
print(f"New reviews saved this run : {grand_total_saved}")
print(f"Google Play total in DB    : {db.get_review_count('google_play')}")
print(f"Total reviews in DB        : {db.get_review_count()}")
print(f"{'='*60}")

# Rating distribution
from shared.database import ReviewModel
with db.get_session() as session:
    print("\nRating distribution (Google Play):")
    for stars in range(5, 0, -1):
        count = session.query(ReviewModel).filter_by(
            source='google_play', rating=stars
        ).count()
        bar = '█' * count
        print(f"  {stars}★  {bar} ({count})")

db.close()
