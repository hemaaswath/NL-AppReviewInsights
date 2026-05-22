# Weekly deliverables — 2026-W21

| File | Format | Description |
|------|--------|-------------|
| [weekly-pulse-2026-W21.md](./weekly-pulse-2026-W21.md) | Markdown | Latest one-page weekly note |
| [weekly-pulse-2026-W21.html](./weekly-pulse-2026-W21.html) | HTML | Same note — **Print → Save as PDF** or open in Word |
| [reviews-2026-W21-sample-redacted.csv](./reviews-2026-W21-sample-redacted.csv) | CSV | 40-row sample; IDs redacted, text truncated |
| [THEME_LEGEND.md](./THEME_LEGEND.md) | Markdown | Product-area definitions & keyword hints |

---

## How to re-run for a new week

### Prerequisites

- Python 3.10+ and `pip install -r requirements.txt`
- `.env` with `GROQ_API_KEY`, `GOOGLE_PLAY_PACKAGE_NAME=com.nextbillion.groww`, `GOOGLE_DOC_ID`, `EMAIL_RECIPIENT`
- **Local MCP path:** Terminal 1 — start saksham-mcp-server (`MCPServer/saksham-mcp-server`, port 8000). See [../MCP_SETUP.md](../MCP_SETUP.md).
- **Streamlit Cloud:** Secrets in app UI; MCP optional (`USE_DIRECT_GOOGLE=1`).

### Option A — Full pipeline (recommended)

```powershell
cd App-Review-Insights-Analyser

# 1) Collect new Play Store reviews
python run_gp_collect.py

# 2) Analyse (sentiment, product-map themes, quotes, actions)
python run_phase2.py

# 3) Publish weekly note → Google Doc (MCP append_to_doc)
python run_phase3.py

# 4) Create Gmail draft (MCP create_email_draft)
python run_phase4.py
```

Or one shot:

```powershell
python run_pipeline.py
```

### Option B — Streamlit dashboard

```powershell
streamlit run streamlit_app.py
```

Click **Refresh insights** (clears DB and re-runs Phases 1–4). Use for demos; local `.env` or Streamlit Secrets required.

### Option C — Regenerate deliverable files only

After Phase 2 has run for the new week:

```powershell
python scripts/export_weekly_deliverables.py
```

Writes updated `weekly-pulse-<week>.md`, sample CSV, and HTML under `Docs/deliverables/`.

### ISO week behaviour

- Insights are keyed by **ISO week** (e.g. `2026-W22`) from analysis run date.
- Re-running Phase 2 in the **same calendar week** **updates** that week’s row in SQLite.
- For **week-over-week** comparison, run analysis in two different ISO weeks (or keep prior week’s DB backup).

### Export PDF or Word from Markdown

**PDF**

1. Open `weekly-pulse-2026-W21.html` in a browser → Print → Save as PDF, **or**
2. Open `weekly-pulse-2026-W21.md` in VS Code / Typora / GitHub → Export PDF, **or**
3. `pandoc Docs/deliverables/weekly-pulse-2026-W21.md -o weekly-pulse-2026-W21.pdf` (if Pandoc installed)

**Word (.docx)**

```powershell
pandoc Docs/deliverables/weekly-pulse-2026-W21.md -o weekly-pulse-2026-W21.docx
```

**Google Doc (production path)**

Phase 3 appends the report via MCP to the Doc ID in `GOOGLE_DOC_ID`.

---

## MCP quick reference

| Phase | MCP endpoint | Env |
|-------|----------------|-----|
| 3 | `POST /append_to_doc` | `MCP_SERVER_URL`, `GOOGLE_DOC_ID` |
| 4 | `POST /create_email_draft` | `MCP_SERVER_URL`, `EMAIL_RECIPIENT` |

Health: `GET http://127.0.0.1:8000/`

---

## Theme legend

See **[THEME_LEGEND.md](./THEME_LEGEND.md)** for all nine Groww product areas, keywords, and sentiment/priority rules.

---

## Data note (2026-W21)

- **124** reviews in local `data/reviews.db` from `com.nextbillion.groww`.
- Product-area counts in the weekly note use the **Groww product map** (keyword analysis aligned with Phase 2 taxonomy).
- If Groq rate limit hit during Phase 2, re-run `python run_phase2.py` after quota resets for LLM-refined themes.
