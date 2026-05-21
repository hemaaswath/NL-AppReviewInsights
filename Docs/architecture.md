# Architecture — App Review Insights Analyzer for Groww

## System Overview

The App Review Insights Analyzer is an AI-powered pipeline that collects Groww app reviews from Google Play Store and Apple App Store, analyses them with an LLM to extract sentiment, themes, quotes, and action items, then formats and distributes a weekly one-page pulse report via Google Docs and Gmail using MCP (Model Context Protocol) servers.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          AI Agent Layer                               │
├──────────────────┬───────────────────┬───────────────┬───────────────┤
│  Phase 1         │  Phase 2          │  Phase 3      │  Phase 4      │
│  Review          │  Analysis         │  Report       │  Distribution │
│  Collector       │  Engine           │  Generator    │  (Email)      │
└──────────────────┴───────────────────┴───────────────┴───────────────┘
         │                   │                 │               │
         ▼                   ▼                 ▼               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                    │
├──────────────────────────────────────────────────────────────────────┤
│   SQLite DB (reviews table)  │  SQLite DB (insights table)           │
└──────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        MCP Server Layer                               │
├──────────────────────────────────────────────────────────────────────┤
│         Google Docs MCP Server  │  Gmail MCP Server                  │
└──────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     External Services Layer                           │
├──────────────────────────────────────────────────────────────────────┤
│  Google Play Store API  │  Apple RSS Feed  │  Google Docs  │  Gmail  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Review Collection ✅ Implemented

### Purpose
Fetch app reviews from Google Play Store and Apple App Store, scrub PII, and store them in a local SQLite database for downstream analysis.

### Components

#### `GooglePlayCollector` (`phase-1/src/google_play_collector.py`)
- Uses `google-play-scraper` library to fetch reviews for `com.groww`
- Fetches in batches of 100, sorted by newest first, `lang=en`, `country=in`
- Parses native scraper fields: `reviewId`, `userName`, `content`, `score`, `at` (datetime), `appVersion`
- Generates a deterministic MD5 review ID from the native `reviewId`
- Filters reviews older than the configurable `weeks_back` cutoff (default 12 weeks)
- **Retry logic**: `tenacity` with 3 attempts, exponential backoff 2–10s on network failures
- **PII scrubbing**: calls `shared/pii_scrubber.py` on title and text at parse time

#### `AppleAppStoreCollector` (`phase-1/src/apple_app_store_collector.py`)
- Fetches Apple RSS feed: `https://itunes.apple.com/us/rss/customerreviews/page/{n}/id/{app_id}/sortby=mostrecent/xml`
- Parses XML with BeautifulSoup (`lxml` parser), handles `im:` namespace tags
- Skips first entry (app info), processes review entries
- **Retry logic**: `tenacity` with 3 attempts, exponential backoff 2–10s
- **PII scrubbing**: calls `shared/pii_scrubber.py` on title and text at parse time
- Saves raw XML pages to `data/raw/apple_app_store/` for debugging

#### `ReviewCollectionOrchestrator` (`phase-1/src/review_collection_orchestrator.py`)
- Entry point for Phase 1; reads config from `.env`
- Runs both collectors sequentially, saves results via `DatabaseManager.save_reviews_batch()`
- Prints collection summary and database statistics

#### `PII Scrubber` (`shared/pii_scrubber.py`)
Strips the following from review text and title before storage:

| Pattern | Replacement |
|---------|-------------|
| Email addresses | `[EMAIL]` |
| Indian mobile numbers (+91, 10-digit) | `[PHONE]` |
| International phone numbers | `[PHONE]` |
| HTTP/HTTPS URLs | `[URL]` |
| `www.` URLs | `[URL]` |
| `@mentions` | `[USER]` |
| Aadhaar-style 12-digit numbers | `[ID]` |

### Data Model — `reviews` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | MD5 hash of native review ID |
| `source` | String | `google_play` or `apple_app_store` |
| `rating` | Integer | 1–5 stars |
| `title` | Text | Review title (PII-scrubbed) |
| `text` | Text | Review content (PII-scrubbed) |
| `date` | DateTime | Review date (UTC) |
| `version` | String | App version at time of review |
| `processed` | Boolean | False until Phase 2 analysis runs |
| `created_at` | DateTime | Row insertion timestamp |

### Data Collected (Groww — `com.groww`)

| Source | Reviews | Notes |
|--------|---------|-------|
| Google Play Store | 70 | Real reviews, `en/in`, newest sort |
| Apple App Store | 3 | Sample data (real app ID not configured) |
| **Total** | **73** | |

**Google Play rating distribution:**
```
5★  █████████████████████  21
4★  █████████               9
3★  ██████                  6
2★  ███████                 7
1★  ███████████████████████████  27
```

### Test Coverage — Phase 1

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_google_play_collector.py` | 30 | Init, parse, collect, retry, PII scrubbing |
| `test_apple_app_store_collector.py` | 18 | Init, parse, collect, edge cases |
| `test_database.py` | 22 | CRUD, dedup, batch ops, count |
| `test_pii_scrubber.py` | 21 | All PII pattern types, edge cases |
| **Total** | **91/91 passing** | |

---

## Phase 2 — Analysis Engine ✅ Implemented

### Purpose
Load collected reviews from the database, run LLM-based analysis to extract sentiment, cluster themes, pick representative quotes, and generate prioritised action items. Store structured `WeeklyInsights` back to the database as JSON.

### Corpus size (2,400 stored → 1,000 analysed)

| Layer | Count | Notes |
|-------|-------|-------|
| Phase 1 DB | Up to **~2,400** normalized reviews | English, ≥6 words, no emoji |
| Phase 2 analysis | **≤ 1,000** per run | `PHASE2_MAX_REVIEWS` — stratified by star rating |
| LLM theme digest | **200** reviews | `PHASE2_THEME_SAMPLE_SIZE` |
| LLM quote pick | **30** reviews | `PHASE2_QUOTE_SAMPLE_SIZE` |

Full Groq budget: `Docs/implementationplan.md`.

### LLM Provider
- **Provider**: Groq
- **Model**: `llama-3.3-70b-versatile` (`GROQ_MODEL` in `.env`)
- **Client**: `langchain-groq` (`ChatGroq`)
- **Limits**: 30 RPM · 1K RPD · 12K TPM · 100K TPD
- **Throttle**: `shared/groq_throttle.py` (~2.1s between calls)
- **Config**: `shared/phase2_config.py` · `shared/phase2_sampling.py`
- **Fallback**: Rating-based sentiment at scale; static fallbacks for themes/quotes/actions

### Groq call budget (weekly @ 1,000 reviews)

| Step | LLM calls | Notes |
|------|-----------|-------|
| Sentiment | **0** (default) | Rating-based when `N > 150` |
| Sentiment (small N) | 4–8 | LLM batches of 20 if `N ≤ 150` |
| Themes | **1** | 200-review digest only |
| Quotes | **1** | 30-review sample |
| Actions | **1** | Compact structured prompt |
| **Typical total** | **3–11** | **~20–40K tokens** (under 100K TPD) |

Do **not** run 100+ sentiment batches on 1,000 reviews (~160K+ tokens — exceeds daily cap).

### Components

#### `SentimentAnalyser` (`phase-2/src/sentiment_analyser.py`)
- At scale (>150 reviews): orchestrator uses **rating-based** sentiment (no Groq)
- Small runs: LLM batches of 20, 80-char truncation
- **Fallback**: star rating if LLM fails

#### `ThemeClusterer` (`phase-2/src/theme_clusterer.py`)
- Up to 5 themes from **200-review** digest (80 chars/review), one LLM call
- **Fallback**: "General Feedback" theme

#### `QuoteExtractor` (`phase-2/src/quote_extractor.py`)
- 3 quotes from **30-review** sample
- **Fallback**: first 3 non-empty reviews

#### `ActionGenerator` (`phase-2/src/action_generator.py`)
- 3 actions from themes + quotes + sentiment summary
- **Fallback**: 3 static actions

#### `AnalysisOrchestrator` (`phase-2/src/analysis_orchestrator.py`)
- Stratified cap at 1,000; sentiment → themes (200) → quotes (30) → actions
- Persists `WeeklyInsights`; marks reviews `processed=True`

### Data Model — `insights` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | Same as `week` (e.g. `2026-W21`) |
| `week` | String | ISO week identifier |
| `generated_at` | DateTime | Analysis run timestamp |
| `total_reviews_analysed` | Integer | Number of reviews processed |
| `themes` | JSON | Array of up to 5 theme objects |
| `quotes` | JSON | Array of 3 quote objects |
| `actions` | JSON | Array of 3 action item objects |
| `sentiment_summary` | JSON | `{positive: N, negative: N, neutral: N}` |
| `doc_id` | String | Google Docs ID (populated in Phase 3) |
| `email_id` | String | Gmail draft ID (populated in Phase 4) |

### Pydantic Models (`shared/models.py`)

```
WeeklyInsights
├── week: str                        # "2026-W21"
├── generated_at: datetime
├── total_reviews_analysed: int
├── themes: list[Theme]              # max 5
│   ├── name: str
│   ├── description: str
│   ├── review_count: int
│   ├── sentiment: SentimentLabel
│   └── keywords: list[str]
├── quotes: list[Quote]              # max 3
│   ├── text: str
│   ├── theme_name: str
│   ├── rating: int
│   └── sentiment: SentimentLabel
├── actions: list[ActionItem]        # max 3
│   ├── description: str
│   ├── priority: str                # high / medium / low
│   ├── theme_name: str
│   └── rationale: str
├── sentiment_summary: dict          # {positive, negative, neutral}
├── doc_id: Optional[str]
└── email_id: Optional[str]
```

### Sample Output — Week 2026-W21 (73 Groww reviews)

**Sentiment summary:** 31 positive / 36 negative / 6 neutral

**Themes identified:**
| Theme | Reviews | Sentiment |
|-------|---------|-----------|
| Positive User Experience | 24 | positive |
| Crashing and Technical Issues | 15 | negative |
| Subscription and Fees | 8 | negative |
| Language and Navigation | 7 | negative |
| Gardening and Plant Care | 6 | positive |

**Action items:**
1. `[HIGH]` Implement crash reporting system to identify and fix frequent crashes
2. `[MEDIUM]` Review and revise subscription model — provide clear cancellation options
3. `[LOW]` Add language selection feature and improve in-app navigation

### Performance

| Corpus | LLM calls | Approx. wall time |
|--------|-----------|-------------------|
| 73 reviews (LLM sentiment) | ~7 | ~40s |
| 1,000 reviews (rating sentiment) | **3** | ~15s (+ 2.1s throttle between calls) |

### Test Coverage — Phase 2

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_sentiment_analyser.py` | 14 | Single + batch, fallbacks, markdown JSON, known sentiments |
| `test_theme_clusterer.py` | 9 | Max 5 enforcement, field validation, fallback, token truncation |
| `test_quote_extractor.py` | 10 | Max 3 enforcement, field validation, fallback, review cap |
| `test_action_generator.py` | 10 | Exactly 3 actions, padding, capping, fallback, prompt content |
| `test_analysis_orchestrator.py` | 22 | Full pipeline, DB persistence, insights retrieval, edge cases |
| **Total** | **65/65 passing** | |

---

## Phase 3 — Report Generation ✅ Implemented

### Purpose
Format `WeeklyInsights` into a one-page weekly pulse document (≤250 words) and create it in Google Docs via the Google Docs MCP Server (with a local Markdown file fallback when MCP is unavailable).

### Components

#### `ReportFormatter` (`phase-3/src/report_formatter.py`)
Converts a `WeeklyInsights` object into two representations:

- **`plain_text`** — clean text for Google Docs insertion (≤250 words enforced)
- **`markdown`** — rich format with tables, blockquotes, emoji icons for local preview

**Report structure (plain_text):**
```
WEEKLY PULSE — GROWW APP REVIEWS
Week: YYYY-WNN  |  Reviews analysed: N

SENTIMENT OVERVIEW
Positive: N (N%)  |  Negative: N (N%)  |  Neutral: N

TOP THEMES
1. Theme Name 😞 (N reviews)
2. ...

USER VOICES
"Quote text..." — N★ (Theme Name)
...

ACTION IDEAS
🔴 [HIGH] Action description
🟡 [MEDIUM] Action description
🟢 [LOW] Action description

Generated: YYYY-MM-DD HH:MM UTC  |  Powered by Groww Review Insights Analyzer
```

**Word count enforcement:**
- Quote text truncated at 120 chars (adds `...`)
- Themes section shows name + count only (no description) in plain_text
- Actions section shows description only (rationale in markdown only)
- Typical output: ~200 words for 5 themes, 3 quotes, 3 actions

**Edge cases handled:**
- Zero sentiment counts → no division error (denominator clamped to 1)
- Empty themes/quotes/actions → sections render with just the heading
- `None` generated_at → falls back to current UTC time
- Unknown priority value → uses `▶` fallback icon
- Long quotes (>120 chars) → truncated with `...`
- Unicode/emoji in content → written correctly via UTF-8

#### `GoogleDocsClient` (`phase-3/src/google_docs_client.py`)
MCP-aware client with automatic local file fallback.

**MCP path** (when `GOOGLE_DOCS_MCP_SERVER_URL` is reachable):
```
POST /docs/create        → { document_id, title }
POST /docs/insert_text   → { document_id, content, position }
POST /docs/format_text   → { document_id, text_range, style: "HEADING_1" }
GET  /docs/{document_id} → { document_id, title, url }
```

**Local file fallback** (when MCP unavailable):
- Saves report as `.md` file to `phase-3/test-results/reports/`
- Returns `file://` URI as `doc_id` so pipeline continues unblocked
- Filename sanitised from title (special chars → `_`, capped at 80 chars)
- Same-title re-runs overwrite the existing file

**Availability check:**
- `GET /health` with 3s timeout on first use; result cached for lifetime of instance
- Non-200 response → marks unavailable → uses local fallback
- Any exception during MCP call → falls back to local file, marks unavailable

#### `ReportOrchestrator` (`phase-3/src/report_orchestrator.py`)
Entry point for Phase 3. Pipeline:
1. Load `WeeklyInsights` from DB (`get_insights(week)` or latest)
2. Reconstruct Pydantic model from DB dict (`_dict_to_insights`)
3. Format report via `ReportFormatter.format()`
4. Create document via `GoogleDocsClient.create_document()`
5. Save `doc_id` back to `insights` table (upsert — preserves `email_id`)

**Re-run behaviour:** Running Phase 3 twice for the same week overwrites `doc_id` but preserves `email_id` (set by Phase 4).

### Report Output — Week 2026-W21

```
Word count : 201 / 250 max
Source     : local_file (MCP not configured)
Doc URL    : file://...phase-3/test-results/reports/Weekly_Pulse___Groww_App_Reviews___2026-W21.md
```

### Test Coverage — Phase 3

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_report_formatter.py` | 29 | Output structure, all sections, markdown, basic edge cases |
| `test_report_formatter_extended.py` | 32 | Word count constraints, quote truncation, sentiment edge cases, markdown structure |
| `test_google_docs_client.py` | 16 | Local fallback, MCP success/failure, URL generation |
| `test_google_docs_client_extended.py` | 19 | Empty/long titles, unicode, MCP error variants, caching, timeout |
| `test_report_orchestrator.py` | 18 | Full pipeline, DB persistence, section content, error handling |
| `test_report_orchestrator_extended.py` | 30 | Re-run idempotency, email_id preservation, multiple weeks, dict conversion edge cases |
| **Total** | **144/144 passing** | |

---

## Phase 4 — Distribution 🔲 Planned

### Purpose
Send the Google Docs report link to a configured recipient via Gmail using the Gmail MCP Server.

### Planned Components
- `GmailMCPClient` — calls Gmail MCP Server to create and send email drafts
- `DistributionOrchestrator` — loads `doc_id` from insights, composes email, sends draft

### MCP Operations (Gmail)
```python
gmail.create_draft(
    to="recipient@example.com",
    subject="Groww App — Weekly Pulse — Week 2026-W21",
    body="Hi,\n\nThis week's review insights are ready:\n{doc_url}\n\n..."
)
gmail.send_draft(draft_id)
```

---

## Shared Infrastructure

### `shared/models.py` — Pydantic Data Models
All phases share a single models file:
- `ReviewSource` (enum) — `google_play`, `apple_app_store`
- `Review` — single review with all fields
- `ReviewCollection` — list of reviews with metadata
- `SentimentLabel` (enum) — `positive`, `negative`, `neutral`
- `ReviewSentiment` — per-review sentiment result
- `Theme` — clustered theme with keywords and sentiment
- `Quote` — representative user quote
- `ActionItem` — prioritised action with rationale
- `WeeklyInsights` — full analysis output for one week

### `shared/database.py` — DatabaseManager
SQLAlchemy-based SQLite manager with two tables:

**`reviews` table** — managed by Phase 1
- `save_review()`, `save_reviews_batch()` — insert with dedup
- `get_reviews_by_source()`, `get_unprocessed_reviews()` — query
- `mark_review_as_processed()` — update flag
- `get_review_count()` — stats

**`insights` table** — managed by Phase 2
- `save_insights()` — upsert by week
- `get_insights(week)` — retrieve by week or latest
- `list_insights_weeks()` — list all stored weeks

### `shared/pii_scrubber.py` — PII Protection
- `scrub(text)` — strips emails, phones, URLs, mentions, Aadhaar IDs
- `scrub_review_dict(review)` — scrubs title + text fields of a review dict, returns copy

---

## Data Flow

```
Phase 1: Review Collection
  GooglePlayCollector ──┐
                        ├──► PII Scrubber ──► DatabaseManager.save_reviews_batch()
  AppleCollector ───────┘                          │
                                                   ▼
                                          reviews table (SQLite)

Phase 2: Analysis
  DatabaseManager.get_unprocessed_reviews()
          │
          ▼
  SentimentAnalyser.analyse_batch()   ──► sentiment_summary dict
          │
  ThemeClusterer.cluster()            ──► list[Theme] (max 5)
          │
  QuoteExtractor.extract()            ──► list[Quote] (max 3)
          │
  ActionGenerator.generate()          ──► list[ActionItem] (exactly 3)
          │
          ▼
  WeeklyInsights (Pydantic model)
          │
  DatabaseManager.save_insights()     ──► insights table (SQLite)
  DatabaseManager.mark_review_as_processed() ──► reviews.processed = True

Phase 3: Report Generation (planned)
  DatabaseManager.get_insights()
          │
  ReportFormatter.format()            ──► plain text ≤250 words
          │
  GoogleDocsMCPClient.create_doc()    ──► doc_id
          │
  DatabaseManager.save_insights()     ──► insights.doc_id updated

Phase 4: Distribution (planned)
  DatabaseManager.get_insights()      ──► doc_id
          │
  GmailMCPClient.send_draft()         ──► email_id
          │
  DatabaseManager.save_insights()     ──► insights.email_id updated
```

---

## Technology Stack

### Implemented
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.14.4 |
| LLM Provider | Groq | Free tier |
| LLM Model | llama-3.3-70b-versatile | via langchain-groq 1.1.2 |
| LLM Client | LangChain Groq | langchain-groq 1.1.2 |
| Database | SQLite | via SQLAlchemy 2.0 |
| Data Models | Pydantic | v2 |
| Review Scraper | google-play-scraper | 1.2.7 |
| HTTP Client | requests + tenacity | retry logic |
| XML Parser | BeautifulSoup4 + lxml | Apple RSS |
| Testing | pytest | 9.0.3 |
| Environment | python-dotenv | .env config |

### Planned (Phase 3–4)
| Component | Technology |
|-----------|-----------|
| Google Docs integration | Google Docs MCP Server |
| Gmail integration | Gmail MCP Server |
| MCP Client | Official MCP SDK |
| Authentication | OAuth 2.0 (managed by MCP servers) |

---

## Security & Privacy

### PII Protection (Implemented)
- `shared/pii_scrubber.py` strips emails, phone numbers, URLs, @mentions, and Aadhaar IDs from all review text at parse time — before storage and before any LLM call
- No raw usernames are stored in the database
- Review IDs are MD5 hashes of native IDs — not personally identifiable

### API Key Management
- All secrets stored in `.env` (gitignored)
- `GROQ_API_KEY` — Groq LLM access
- `DATABASE_PATH` — configurable DB location
- No API keys hardcoded in source files

### Data Security (Planned — Phase 3–4)
- OAuth tokens managed by MCP servers (not stored in application code)
- Encrypted communication with Google services via MCP protocol

---

## Project Structure

```
App-Review-Insights-Analyser/
├── shared/
│   ├── models.py              # All Pydantic data models (Phase 1 + 2)
│   ├── database.py            # SQLAlchemy DB manager (reviews + insights tables)
│   ├── pii_scrubber.py        # PII stripping utility
│   ├── review_normalizer.py   # Phase 1 filters (English, word count, emoji)
│   ├── phase2_config.py       # Groq limits + Phase 2 env defaults
│   ├── phase2_sampling.py     # Stratified cap (1,000 reviews)
│   └── groq_throttle.py       # RPM spacing between LLM calls
├── phase-1/
│   ├── src/
│   │   ├── google_play_collector.py
│   │   ├── apple_app_store_collector.py
│   │   └── review_collection_orchestrator.py
│   ├── tests/                 # 91 tests, all passing
│   └── test-results/
├── phase-2/
│   ├── src/
│   │   ├── sentiment_analyser.py
│   │   ├── theme_clusterer.py
│   │   ├── quote_extractor.py
│   │   ├── action_generator.py
│   │   └── analysis_orchestrator.py
│   ├── tests/                 # 65 tests, all passing
│   └── test-results/
│       └── insights.json      # Latest analysis output
├── phase-3/                   # Planned — Report Generation
├── phase-4/                   # Planned — Distribution
├── data/
│   └── reviews.db             # SQLite database (reviews + insights tables)
├── run_phase2.py              # Phase 2 entry point script
├── run_gp_collect.py          # Phase 1 collection script
└── .env                       # API keys and config (gitignored)
```

---

## Implementation Status

| Phase | Status | Tests | Notes |
|-------|--------|-------|-------|
| Phase 1 — Review Collection | ✅ Complete | 91/91 | 73 real reviews collected |
| Phase 2 — Analysis Engine | ✅ Complete | 65/65 | llama-3.3-70b, 1K cap, 3–11 Groq calls/run |
| Phase 3 — Report Generation | ✅ Complete | 126/126 | Google Docs MCP + local fallback |
| Phase 4 — Distribution | 🔲 Planned | — | Gmail via MCP |
