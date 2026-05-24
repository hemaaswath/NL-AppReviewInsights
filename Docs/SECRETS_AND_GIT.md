# Secrets vs GitHub — verified safe workflow

## Is the GitHub repo leaking secrets?

**Checked on `main` (May 2026):**

| File | On GitHub? |
|------|------------|
| `.env` | **No** (404) |
| `.streamlit/secrets.toml` | **No** (404) |
| `token.json` / `credentials.json` | **Never committed** in history |
| `.streamlit/secrets_export.txt` | **No** (gitignored) |

Only **placeholders** are public: `.env.example`, `.streamlit/secrets.toml.example`.

**Pushing code does not upload your Streamlit Cloud Secrets.** Those live only on [share.streamlit.io](https://share.streamlit.io) → App → **Settings → Secrets**.

---

## Why it feels like secrets appear on GitHub

1. **Streamlit Cloud Secrets** — configured on Streamlit’s website, not in the git repo. Deleting “secrets” there is correct for Cloud, but unrelated to `git push`.
2. **Accidental commit** — `git add .` or `git add -f .env` can override `.gitignore`.
3. **`secrets_export.txt`** — created by `export_streamlit_secrets.ps1`; must stay local (gitignored).
4. **Example files** — `secrets.toml.example` looks similar but has fake values only.

---

## Security: was anything compromised?

| Exposure | Risk | Action |
|----------|------|--------|
| Secrets in **this GitHub repo** | **Low** — not found on `main` | None required for Git alone |
| Secrets pasted in **chat / screenshots** | **High** if you shared real keys | **Rotate** Groq key, Google OAuth client secret, re-run OAuth |
| **Streamlit Cloud** Secrets UI | OK if only you have access | Don’t paste into GitHub files |

If you ever committed a real `.env` once (even if deleted later), treat keys as leaked and **rotate** them; old commits can still contain files until history is rewritten (BFG Repo-Cleaner / `git filter-repo`). Deleting a file on GitHub’s website does **not** remove it from git history.

---

## Root cause (fixed permanently)

1. **OAuth files inside the repo folder** — the app used to write `credentials.json` under `MCPServer/`. Git then showed them as modified; `git add .` could push them.
2. **Fix:** Secrets live only in **`%LOCALAPPDATA%\groww-insights\`** (outside the repo). On every app start, `purge_repo_secrets.py` **deletes** any `token.json` / `credentials.json` / `secrets.toml` found under the project folder.
3. **MCP server folder** is no longer tracked by git (`MCPServer/saksham-mcp-server/` is gitignored). Clone it locally if needed.

**Streamlit Cloud secrets** are on share.streamlit.io — **not** in the GitHub repo. Deleting files on GitHub does not remove Streamlit secrets.

---

## Where secrets live (never GitHub)

| Secret | Location |
|--------|----------|
| Groq, doc ID, email | Local `.env` (gitignored) or **Streamlit Cloud → Secrets** |
| Google OAuth | **`%LOCALAPPDATA%\groww-insights\token.json`** (outside repo) |
| Google client JSON | **`%LOCALAPPDATA%\groww-insights\credentials.json`** |
| Export helper | `.streamlit/secrets_export.txt` (gitignored) — paste into Streamlit UI only |

---

## One-time setup on your PC

```powershell
.\scripts\install_git_hooks.ps1
python scripts/purge_repo_secrets.py
```

If GitHub ever had tracked secrets:

```powershell
python scripts/untrack_secrets.py
git commit -m "Stop tracking secret files"
```

**Always push with:**

```powershell
.\scripts\safe_git_push.ps1
```

**Never:** `git add .`

---

## Root cause we fixed earlier (May 2026)

Running the app **used to write** `GOOGLE_CREDENTIALS_JSON` into  
`MCPServer/saksham-mcp-server/credentials.json` inside the repo. That made git show
secret files as modified and led to accidental pushes.

**Now:** `shared/google_auth.py` reads secrets from **environment only** — never writes
OAuth files into the repository.

If secrets were ever pushed, run:

```powershell
python scripts/untrack_secrets.py
git commit -m "Stop tracking secret files"
```

Then **rotate** Groq + Google OAuth keys.

---

## Permanent protection (install once per clone)

```powershell
.\scripts\install_git_hooks.ps1
```

This installs **pre-commit** and **pre-push** hooks that block:

- Secret **paths**: `.env`, `secrets.toml`, `token.json`, `credentials.json`, `secrets_export.txt`, etc.
- Secret **content** in any staged/pushed file: `gsk_…` Groq keys, `sk-…`, real `refresh_token` / `client_secret` values, large `GOOGLE_TOKEN_JSON` blobs.

**Push safely (recommended):**

```powershell
.\scripts\safe_git_push.ps1
```

**Manual checks:**

```powershell
python scripts/secret_scan.py staged
python scripts/secret_scan.py tracked
```

GitHub Actions workflow `.github/workflows/block-secrets.yml` runs the same scan on every push/PR to `main`.

Before each commit, add **only code files** — never `git add .`:

```powershell
git status
git add streamlit_app.py shared/week_over_week.py
git commit -m "your message"
```

---

## Where secrets should live

| Secret | Location |
|--------|----------|
| Groq, doc ID, email | Local `.env` (gitignored) |
| Same values on Cloud | Streamlit **Settings → Secrets** (website UI) |
| Google OAuth token | Local `MCPServer/.../token.json` (gitignored) |
| Export helper | `.streamlit/secrets_export.txt` (gitignored) — copy into Streamlit UI, **never** `git add` |

```powershell
.\scripts\export_streamlit_secrets.ps1
# Optional: -IncludeCredentials (usually not needed on Cloud)
```

---

## Never do this

```powershell
git add .env
git add .streamlit/secrets.toml
git add -f MCPServer/saksham-mcp-server/token.json
git add .streamlit/secrets_export.txt
```
