# Demo checklist — Phases 1–4 (Google Cloud project: **Appreview**)

## One-time setup

1. **Google Cloud project**: **Appreview** (not NL-MyLearning)
2. In **Appreview**: enable Docs + Gmail APIs; OAuth **Test users** → your Gmail
3. Download Desktop OAuth **`credentials.json`** from **Appreview** → save to:
   `MCPServer\saksham-mcp-server\credentials.json`
4. **OAuth** (creates `token.json` in the same folder):

   ```powershell
   cd App-Review-Insights-Analyser\MCPServer\saksham-mcp-server
   python auth.py
   ```

5. **Google Doc** in the same Google account → `GOOGLE_DOC_ID` in `.env`
6. **`.env`**: `MCP_SERVER_URL=http://127.0.0.1:8000`, `EMAIL_RECIPIENT=your@gmail.com`

## Before each demo run

**Terminal 1 — MCP server**

```powershell
cd C:\Users\ashhe\OneDrive\Documents\Nextleap\App-Review-Insights-Analyser\MCPServer\saksham-mcp-server
$env:AUTO_APPROVE="true"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — pipeline**

```powershell
cd C:\Users\ashhe\OneDrive\Documents\Nextleap\App-Review-Insights-Analyser
python run_pipeline.py
```

Or: `run_gp_collect.py` → `run_phase2.py` → `run_phase3.py` → `run_phase4.py`

## Screenshots for submission

| # | What to capture |
|---|-----------------|
| 1 | Google Doc with appended weekly pulse (Phase 3, `source: google_docs`) |
| 2 | Gmail → **Drafts** — `Groww App - Weekly Review Pulse - {week}` |
| 3 | Terminal: Phase 4 `DISTRIBUTION COMPLETE` + Gmail `draft_id` |
| 4 | Optional: insights row with `doc_id` + `email_id` set |

## Verify success

```powershell
python -c "from shared.database import DatabaseManager; d=DatabaseManager('data/reviews.db'); i=d.get_insights(); print(i.get('week'), i.get('doc_id'), i.get('email_id')); d.close()"
```

- **Phase 3**: `doc_id` is a Google Doc ID (not a `.md` path)
- **Phase 4**: `email_id` is a non-null Gmail draft ID
