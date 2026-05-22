"""
Export all collected reviews to test-results folder as JSON and Markdown.
"""
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, '.')
from shared.database import DatabaseManager

db = DatabaseManager('data/reviews.db')
gp = db.get_reviews_by_source('google_play')
ap = db.get_reviews_by_source('apple_app_store')
db.close()

OUT = 'phase-1/test-results'

# ── JSON exports ──────────────────────────────────────────────────────────────
with open(f'{OUT}/raw_reviews_google_play.json', 'w', encoding='utf-8') as f:
    json.dump(gp, f, indent=2, ensure_ascii=False, default=str)

with open(f'{OUT}/raw_reviews_apple_app_store.json', 'w', encoding='utf-8') as f:
    json.dump(ap, f, indent=2, ensure_ascii=False, default=str)

with open(f'{OUT}/raw_reviews_all.json', 'w', encoding='utf-8') as f:
    json.dump(gp + ap, f, indent=2, ensure_ascii=False, default=str)

# ── Rating distribution ───────────────────────────────────────────────────────
stars = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
for r in gp:
    stars[r['rating']] += 1

# ── Markdown report ───────────────────────────────────────────────────────────
lines = []
lines.append('# Raw Review Data — Phase 1 Collection')
lines.append('')
lines.append(f'**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
lines.append('')
lines.append(f'| Metric | Value |')
lines.append(f'|--------|-------|')
lines.append(f'| Total reviews | {len(gp) + len(ap)} |')
lines.append(f'| Google Play | {len(gp)} |')
lines.append(f'| Apple App Store | {len(ap)} |')
lines.append(f'| App package | com.nextbillion.groww (Groww Stocks/MF) |')
lines.append(f'| Collection window | 52 weeks |')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## Rating Distribution — Google Play')
lines.append('')
lines.append('| Stars | Count | Bar |')
lines.append('|-------|-------|-----|')
for s in range(5, 0, -1):
    bar = '█' * stars[s]
    lines.append(f'| {s}★ | {stars[s]} | {bar} |')

lines.append('')
lines.append('---')
lines.append('')
lines.append(f'## Google Play Reviews ({len(gp)})')
lines.append('')

for i, r in enumerate(gp, 1):
    title = r['title'] if r['title'] else '(no title)'
    lines.append(f'### {i}. [{r["rating"]}★] {title}')
    lines.append('')
    lines.append(f'- **Date:** {r["date"][:10]}')
    lines.append(f'- **Version:** {r["version"] if r["version"] else "unknown"}')
    lines.append(f'- **Source:** {r["source"]}')
    lines.append(f'- **Processed:** {r["processed"]}')
    lines.append(f'- **ID:** `{r["id"]}`')
    lines.append('')
    lines.append(f'> {r["text"]}')
    lines.append('')

lines.append('---')
lines.append('')
lines.append(f'## Apple App Store Reviews ({len(ap)})')
lines.append('')

for i, r in enumerate(ap, 1):
    title = r['title'] if r['title'] else '(no title)'
    lines.append(f'### {i}. [{r["rating"]}★] {title}')
    lines.append('')
    lines.append(f'- **Date:** {r["date"][:10]}')
    lines.append(f'- **Version:** {r["version"] if r["version"] else "unknown"}')
    lines.append(f'- **Source:** {r["source"]}')
    lines.append(f'- **Processed:** {r["processed"]}')
    lines.append(f'- **ID:** `{r["id"]}`')
    lines.append('')
    lines.append(f'> {r["text"]}')
    lines.append('')

with open(f'{OUT}/raw_reviews_report.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'Exported {len(gp)} Google Play + {len(ap)} Apple reviews')
print(f'Files written to {OUT}/:')
print('  raw_reviews_google_play.json')
print('  raw_reviews_apple_app_store.json')
print('  raw_reviews_all.json')
print('  raw_reviews_report.md')
