"""
Script to collect Google Play reviews for Groww across multiple
sort orders, countries, and languages to maximise real review coverage.
"""
import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "phase-1/src")

from dotenv import load_dotenv

from shared.play_collect import collect_play_reviews

load_dotenv()

fast = os.getenv("COLLECT_FAST", "").strip() in ("1", "true", "yes")
result = collect_play_reviews(fast=fast)

if not result["ok"]:
    raise SystemExit(f"Collection failed: {result.get('detail', 'unknown error')}")

print(f"Collecting reviews for: {result.get('detail', '')}")
print(f"Package: {result.get('package_name', '')}")
print(f"\n{'='*60}")
print("COLLECTION COMPLETE")
print(f"New reviews saved this run : {result['new_reviews']}")
print(f"Google Play total in DB    : {result['total_reviews']}")
print(f"Mode                       : {'fast' if result.get('fast') else 'full'}")
print(f"{'='*60}")
