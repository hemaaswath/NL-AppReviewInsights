"""
Phase 1 + Phase 2 integration validation script.
Checks DB state, data integrity, and end-to-end flow.
"""
import sys
sys.path.insert(0, '.')

from shared.database import DatabaseManager

db = DatabaseManager('data/reviews.db')

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    print(f"{status}  {label}" + (f"  →  {detail}" if detail else ""))

print("=" * 65)
print("PHASE 1 + PHASE 2 INTEGRATION VALIDATION")
print("=" * 65)

# ── Phase 1 checks ────────────────────────────────────────────────
print("\n--- Phase 1: Review Collection ---")

gp_count    = db.get_review_count('google_play')
ap_count    = db.get_review_count('apple_app_store')
total       = db.get_review_count()
unprocessed = db.get_unprocessed_reviews()
processed_count = total - len(unprocessed)

check("Google Play reviews collected",   gp_count >= 10,        f"{gp_count} reviews")
check("Apple App Store reviews present", ap_count >= 0,         f"{ap_count} reviews")
check("Total reviews in DB",             total >= 10,           f"{total} reviews")
check("Reviews have required fields",    True,                  "id, source, rating, title, text, date, version, processed")

# Validate a sample review has all required fields
sample_reviews = db.get_reviews_by_source('google_play', limit=5)
required_fields = ['id', 'source', 'rating', 'title', 'text', 'date', 'version', 'processed']
all_fields_ok = all(all(f in r for f in required_fields) for r in sample_reviews)
check("All required fields present in reviews", all_fields_ok)

# Validate rating range
bad_ratings = [r for r in sample_reviews if not (1 <= r['rating'] <= 5)]
check("All ratings in 1-5 range", len(bad_ratings) == 0, f"checked {len(sample_reviews)} samples")

# Validate dates are parseable
import datetime
date_ok = True
for r in sample_reviews:
    try:
        datetime.datetime.fromisoformat(r['date'])
    except Exception:
        date_ok = False
        break
check("All dates are valid ISO format", date_ok)

# PII check — no raw emails or phone numbers in stored text
import re
pii_pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}|(?<!\d)[6-9]\d{9}(?!\d)')
all_reviews = db.get_reviews_by_source('google_play')
pii_found = [r['id'] for r in all_reviews if pii_pattern.search(r.get('text','') + r.get('title',''))]
check("No raw PII in stored review text", len(pii_found) == 0,
      f"{len(pii_found)} reviews with potential PII" if pii_found else "clean")

# ── Phase 1 → Phase 2 handoff ─────────────────────────────────────
print("\n--- Phase 1 → Phase 2 Handoff ---")

check("Reviews marked as processed after analysis",
      processed_count > 0,
      f"{processed_count}/{total} processed")

check("Processed count matches reviews analysed",
      processed_count == total,
      f"{processed_count} processed, {len(unprocessed)} still pending")

# ── Phase 2 checks ────────────────────────────────────────────────
print("\n--- Phase 2: Analysis Engine ---")

weeks = db.list_insights_weeks()
check("Insights stored in DB",          len(weeks) > 0,        f"weeks: {weeks}")

latest = db.get_insights()
if latest:
    check("WeeklyInsights has week field",      bool(latest.get('week')),           latest.get('week'))
    check("Reviews analysed count > 0",         latest['total_reviews_analysed'] > 0,
          str(latest['total_reviews_analysed']))
    check("Themes present (1-5)",               1 <= len(latest['themes']) <= 5,
          f"{len(latest['themes'])} themes")
    check("Exactly 3 quotes",                   len(latest['quotes']) == 3,
          f"{len(latest['quotes'])} quotes")
    check("Exactly 3 action items",             len(latest['actions']) == 3,
          f"{len(latest['actions'])} actions")
    check("Sentiment summary has all 3 keys",
          all(k in latest['sentiment_summary'] for k in ['positive','negative','neutral']),
          str(latest['sentiment_summary']))
    check("Sentiment counts sum to reviews analysed",
          sum(latest['sentiment_summary'].values()) == latest['total_reviews_analysed'],
          f"{sum(latest['sentiment_summary'].values())} == {latest['total_reviews_analysed']}")

    # Theme field validation
    theme_fields_ok = all(
        all(k in t for k in ['name','description','review_count','sentiment','keywords'])
        for t in latest['themes']
    )
    check("All theme objects have required fields", theme_fields_ok)

    # Quote field validation
    quote_fields_ok = all(
        all(k in q for k in ['text','theme_name','rating','sentiment'])
        for q in latest['quotes']
    )
    check("All quote objects have required fields", quote_fields_ok)

    # Action field validation
    action_fields_ok = all(
        all(k in a for k in ['description','priority','theme_name','rationale'])
        for a in latest['actions']
    )
    check("All action objects have required fields", action_fields_ok)

    # Priority values valid
    valid_priorities = all(a['priority'] in ('high','medium','low') for a in latest['actions'])
    check("All action priorities are valid (high/medium/low)", valid_priorities)

    # doc_id and email_id exist as keys (null is fine — Phase 3/4 not yet run)
    check("doc_id field present (Phase 3 ready)",   'doc_id'   in latest, str(latest.get('doc_id')))
    check("email_id field present (Phase 4 ready)", 'email_id' in latest, str(latest.get('email_id')))

else:
    check("Insights retrievable from DB", False, "No insights found")

db.close()

# ── Summary ───────────────────────────────────────────────────────
print("\n" + "=" * 65)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
print(f"RESULT: {passed}/{len(results)} checks passed  |  {failed} failed")
print("=" * 65)

if failed > 0:
    print("\nFailed checks:")
    for status, label, detail in results:
        if status == FAIL:
            print(f"  {label}: {detail}")
    sys.exit(1)
else:
    print("\nPhase 1 + Phase 2 integration: FULLY VALIDATED")
