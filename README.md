# App Review Insights Analyzer (Groww)

Turn Google Play reviews into a **weekly one-page pulse**: product-map themes, user quotes, action items, **Google Doc** (MCP), and **Gmail draft** (MCP).

**Live dashboard:** [Streamlit Cloud](https://share.streamlit.io) (see [Docs/DEPLOYMENT_STREAMLIT.md](Docs/DEPLOYMENT_STREAMLIT.md))  
**Repo:** https://github.com/hemaaswath/NL-AppReviewInsights

---

## Latest deliverables (2026-W21)

| Artifact | Path |
|----------|------|
| Weekly note (MD) | [Docs/deliverables/weekly-pulse-2026-W21.md](Docs/deliverables/weekly-pulse-2026-W21.md) |
| Weekly note (HTML → PDF) | [Docs/deliverables/weekly-pulse-2026-W21.html](Docs/deliverables/weekly-pulse-2026-W21.html) |
| Reviews CSV (sample, redacted) | [Docs/deliverables/reviews-2026-W21-sample-redacted.csv](Docs/deliverables/reviews-2026-W21-sample-redacted.csv) |
| **How to re-run · Theme legend** | [Docs/deliverables/README.md](Docs/deliverables/README.md) · [THEME_LEGEND.md](Docs/deliverables/THEME_LEGEND.md) |

---

## Architecture (MCP-first)

```
Play Store → Phase 1 Collect → SQLite
                ↓
         Phase 2 Groq Analysis (product-map themes)
                ↓
    Phase 3 MCP append_to_doc → Google Docs
                ↓
    Phase 4 MCP create_email_draft → Gmail
                ↓
         Streamlit dashboard (+ week-over-week)
```

MCP server: [saksham-mcp-server](https://github.com/saksham20189575/saksham-mcp-server) in `MCPServer/saksham-mcp-server`. Setup: [Docs/MCP_SETUP.md](Docs/MCP_SETUP.md).

---

## Quick start

```powershell
pip install -r requirements.txt
copy .env.example .env   # fill GROQ_API_KEY, GOOGLE_DOC_ID, etc.

# Terminal 1 — MCP
cd MCPServer\saksham-mcp-server
.\venv\Scripts\Activate.ps1
uvicorn server:app --port 8000

# Terminal 2 — pipeline
python run_pipeline.py
```

Regenerate MD / HTML / CSV deliverables:

```powershell
python scripts/export_weekly_deliverables.py
```

---

## Security

Never commit `.env`, `token.json`, or `secrets.toml`. Install hooks:

```powershell
.\scripts\install_git_hooks.ps1
.\scripts\safe_git_push.ps1
```

See [Docs/SECRETS_AND_GIT.md](Docs/SECRETS_AND_GIT.md).

---

## Docs

- [Deliverables & weekly re-run](Docs/deliverables/README.md)
- [Theme legend](Docs/deliverables/THEME_LEGEND.md)
- [MCP setup](Docs/MCP_SETUP.md)
- [Streamlit deploy](Docs/DEPLOYMENT_STREAMLIT.md)
- [Architecture](Docs/architecture.md)
