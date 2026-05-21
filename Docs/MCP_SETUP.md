# MCP setup — saksham-mcp-server

This project uses [saksham-mcp-server](https://github.com/saksham20189575/saksham-mcp-server) for **Google Docs** (Phase 3) and **Gmail** (Phase 4) on a single FastAPI app (default port **8000**).

| Tool | HTTP endpoint | Used by |
|------|---------------|---------|
| Append to Doc | `POST /append_to_doc` | Phase 3 — `google_docs_client.py` |
| Create email draft | `POST /create_email_draft` | Phase 4 — `gmail_client.py` |
| Health | `GET /` | Both clients |

Implementation reference: [`docs_tool.py`](https://github.com/saksham20189575/saksham-mcp-server/blob/main/docs_tool.py), [`gmail_tool.py`](https://github.com/saksham20189575/saksham-mcp-server/blob/main/gmail_tool.py), [`server.py`](https://github.com/saksham20189575/saksham-mcp-server/blob/main/server.py).

---

## 1. Google Cloud project: **Appreview**

Use a single GCP project for OAuth, APIs, and `credentials.json`:

| Setting | Value |
|---------|--------|
| **Project name** | **Appreview** (not NL-MyLearning or other old projects) |
| **OAuth consent screen** | App name can be “Appreview” (what you see in the browser) |
| **Test users** | Your Gmail (e.g. `hemaaswath19@gmail.com`) |

All steps below must be done **inside the Appreview project** in [Google Cloud Console](https://console.cloud.google.com/).

## 2. Install the MCP server (bundled in this repo)

```powershell
cd C:\Users\ashhe\OneDrive\Documents\Nextleap\App-Review-Insights-Analyser\MCPServer\saksham-mcp-server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

(Or clone upstream separately — still place `credentials.json` from **Appreview** in this folder.)

## 3. Google Cloud credentials (Appreview project)

1. Select project **Appreview** in Google Cloud Console  
2. Enable **Google Docs API** and **Gmail API**  
3. **OAuth consent screen** → **Test users** → add your Gmail  
4. **Credentials** → **Create credentials** → **OAuth client ID** → **Desktop app**  
5. Download **`credentials.json`** from **Appreview** only  
6. Save as:

   `App-Review-Insights-Analyser\MCPServer\saksham-mcp-server\credentials.json`

**Wrong path (common):** `Documents\Nextleap\saksham-mcp-server\credentials.json` is a separate clone — the pipeline does **not** read it. Copy into `MCPServer\saksham-mcp-server\` or run:

```powershell
.\scripts\install_credentials.ps1 -SourcePath "C:\Users\ashhe\OneDrive\Documents\Nextleap\saksham-mcp-server\credentials.json"
```

Verify: `.\scripts\verify_credentials.ps1` must show `project_id` **appreview-*** (not `nl-mylearning`).

## 4. First-time OAuth (Appreview credentials)

```powershell
cd C:\Users\ashhe\OneDrive\Documents\Nextleap\App-Review-Insights-Analyser\MCPServer\saksham-mcp-server
python auth.py
```

- Browser should show the **Appreview** app (not an old “Nextleap” app from another project).  
- Sign in with a Gmail listed under **Test users**.  
- Creates `token.json` in this folder (do not commit).

## 5. Create a Google Doc for weekly reports

1. Create a blank Google Doc (e.g. “Groww Weekly Pulse”)  
2. Copy the document ID from the URL:  
   `https://docs.google.com/document/d/DOCUMENT_ID/edit`  
3. In **this** project’s `.env`:

```env
GOOGLE_DOC_ID=DOCUMENT_ID
```

## 6. Configure this analyzer’s `.env`

```env
MCP_SERVER_URL=http://127.0.0.1:8000
EMAIL_RECIPIENT=your.email@example.com
GOOGLE_DOC_ID=your_document_id
```

## 7. Start the MCP server

In `MCPServer\saksham-mcp-server`:

```powershell
# Recommended for pipeline runs (no terminal y/n prompts)
$env:AUTO_APPROVE="true"
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Verify: open http://127.0.0.1:8000/docs or run:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing
```

## 8. Run the pipeline

From `App-Review-Insights-Analyser` (Phases 1–2 as needed):

```powershell
$env:PYTHONPATH="phase-3\src"
python phase-3\src\report_orchestrator.py

$env:PYTHONPATH="phase-4\src"
python phase-4\src\distribution_orchestrator.py
```

When `AUTO_APPROVE` is not set, approve each action in the **MCP server terminal** (`y`).

---

## Behaviour notes

- **Docs**: The MCP server **appends** to an existing doc; it does not create a new document.  
- **Gmail**: The MCP server **creates a draft only** (no automatic send). Phase 4 stores the Gmail `draft_id` in `insights.email_id`. Open Gmail → Drafts to review and send.  
- **Approval**: Set `AUTO_APPROVE=true` on the MCP server process for unattended runs.
