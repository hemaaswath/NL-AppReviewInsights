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

If you ever committed a real `.env` once (even if deleted later), treat keys as leaked and **rotate** them; old commits can still contain files.

---

## Install commit protection (once per clone)

```powershell
.\scripts\install_git_hooks.ps1
```

This blocks commits that stage: `.env`, `secrets.toml`, `token.json`, `credentials.json`, `secrets_export.txt`.

Before each commit:

```powershell
git status
.\scripts\check_no_secrets_staged.ps1
git add streamlit_app.py   # example: only code files
git commit -m "message"
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
