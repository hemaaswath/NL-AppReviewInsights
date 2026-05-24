# Deploy on Streamlit Cloud

Host the full **App Review Insights Analyzer** on [Streamlit Community Cloud](https://share.streamlit.io). Phases 3–4 call Google Docs and Gmail **directly** in the app process — you do **not** need Railway or a separate MCP server.

---

## Architecture

```text
Streamlit Cloud (streamlit_app.py)
  Phase 1–2: google-play-scraper + Groq
  Phase 3–4: shared/google_direct.py (OAuth via GOOGLE_TOKEN_JSON)
       ↓
  Google Docs + Gmail APIs
```

Set `STREAMLIT_DEPLOYMENT=1` and `USE_DIRECT_GOOGLE=1` automatically in `streamlit_app.py`.

---

## Prerequisites (local, once)

1. **Google Cloud project Appreview** — Docs + Gmail APIs enabled; OAuth test user = your Gmail.
2. **OAuth token** on your machine:

   ```powershell
   cd App-Review-Insights-Analyser
   .\scripts\complete_oauth.ps1
   ```

3. **Google Doc** shared with that account → copy doc ID into secrets as `GOOGLE_DOC_ID`.
4. **Groq API key** for Phase 2.

---

## Export secrets for Streamlit

```powershell
.\scripts\export_streamlit_secrets.ps1
```

This writes `.streamlit/secrets_export.txt` with `GOOGLE_TOKEN_JSON` (full `token.json` on one line). Add your `GROQ_API_KEY`, `GOOGLE_DOC_ID`, and `EMAIL_RECIPIENT`.

**Local test:**

```powershell
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit secrets.toml with real values (or use secrets_export.txt)
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Your `.env` at the repo root is loaded automatically; local `token.json` is used when `GOOGLE_TOKEN_JSON` is not in secrets.

---

## Deploy on share.streamlit.io

1. Push the repo to GitHub (`https://github.com/hemaaswath/NL-AppReviewInsights`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** (or open existing app).
3. **Repository**: `hemaaswath/NL-AppReviewInsights`, branch `main`.
4. **Main file path**: `streamlit_app.py`
5. **Authorize GitHub** when Streamlit asks — this adds a **read-only deploy key** named like  
   `Streamlit - (main, streamlit_app.py)`. **That is normal.** It is not an API key leak; do not delete it if you want Cloud deploys to work.
6. **App settings → Secrets** — paste TOML from `secrets_export.txt` (minimum keys):

   | Secret | Required |
   |--------|----------|
   | `GROQ_API_KEY` | Yes |
   | `GOOGLE_TOKEN_JSON` | Yes (from `token.json`) |
   | `GOOGLE_DOC_ID` | Yes |
   | `EMAIL_RECIPIENT` | **Yes** — required for Phase 4 (e.g. `hemaaswath19@gmail.com`) |
   | `GOOGLE_PLAY_PACKAGE_NAME` | **`com.nextbillion.groww`** (NOT `com.groww` — plant app) |
   | `DATABASE_PATH` | Optional (`data/reviews.db`) |
   | `GOOGLE_CREDENTIALS_JSON` | Optional |

7. **Deploy**. The **bundled snapshot** loads immediately on Cloud. Click sidebar **Refresh insights** to run live Phases 1–2 (and 3–4 if Google secrets are set).

---

## If deploy fails after deleting the Streamlit deploy key

If you removed **Settings → Deploy keys → Streamlit - (main, streamlit_app.py)** on GitHub, Streamlit can no longer clone your repo.

1. Open [share.streamlit.io](https://share.streamlit.io) → your app → **⋮** → **Settings**.
2. **Reconnect** GitHub / re-authorize the repository (or delete the app and create **New app**).
3. Confirm a new deploy key appears under GitHub → repo **Settings → Deploy keys** (new SHA256 fingerprint is OK).
4. **Reboot app** on Streamlit Cloud.
5. Re-check **App settings → Secrets** (they are stored on Streamlit, not in GitHub).

GitHub email notifications about “secrets” are often either:
- **Secret scanning** on old commits (resolve in **Security → Secret scanning**), or
- **Deploy key added by Streamlit** (safe — required for deployment).

---

## Notes

| Topic | Detail |
|-------|--------|
| **Database** | Streamlit Cloud disk is ephemeral; data may reset on redeploy. Fine for demos. |
| **MCP server** | Not required when deployed on Streamlit. Local dev can still use `uvicorn` + `MCP_SERVER_URL`. |
| **Token refresh** | `GOOGLE_TOKEN_JSON` must include `refresh_token`. Re-run OAuth if Phase 3/4 fail with invalid_grant. |
| **Railway** | Optional legacy path; see `MCPServer/saksham-mcp-server/DEPLOYMENT.md`. |

---

## Verify after deploy

1. App shows **Google token: OK**.
2. Run **Phase 2** (after Phase 1 or if DB already has reviews).
3. **Phase 3** → `source: google_docs` in result JSON.
4. **Phase 4** → Gmail draft id in result; check Gmail **Drafts**.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| App cannot access repository / deploy failed | Reconnect GitHub on share.streamlit.io; allow Streamlit deploy key (read-only). |
| GitHub notification about Streamlit deploy key | Normal — not a leaked API key. Only delete if you are removing Streamlit Cloud entirely. |
| Google token missing | Add `GOOGLE_TOKEN_JSON` to Streamlit secrets; re-export from local `token.json`. |
| Permission denied on Doc | Share the Doc with the OAuth Gmail account. |
| Groq rate limit | Reduce reviews in Phase 2 config or run Phase 2 only after a cooldown. |
| Build fails on import | Ensure repo root `requirements.txt` is selected (not MCP subfolder). |
