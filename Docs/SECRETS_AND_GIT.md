# Secrets vs GitHub — do not mix them

## Latest code on GitHub

App code is pushed to: https://github.com/hemaaswath/NL-AppReviewInsights (`main` branch).

## What must NEVER be in the Git repo

| File | Where it belongs |
|------|------------------|
| `.env` | Local only (gitignored) |
| `.streamlit/secrets.toml` | Local only (gitignored) |
| `MCPServer/saksham-mcp-server/token.json` | Local only (gitignored) |
| `MCPServer/saksham-mcp-server/credentials.json` | Local only (gitignored) |

Safe to commit: `.env.example`, `.streamlit/secrets.toml.example` (placeholders only).

## Streamlit Cloud secrets

Configure in **share.streamlit.io → your app → Settings → Secrets**.

Those values are **not stored in GitHub**. Pushing code does not upload your Streamlit secrets.

If you delete something on GitHub after each push, check you are not:

- Committing `.env` or `secrets.toml` by mistake (`git add -f` overrides gitignore), or
- Confusing **Streamlit Cloud Secrets** (website UI) with **files in the repo**.

## Before you commit

```powershell
git status
.\scripts\check_no_secrets_staged.ps1
```

Only `git add` specific files — avoid `git add .` until you have confirmed no secret paths appear in `git status`.

## If secrets were ever pushed to GitHub

1. Rotate **Groq** API key, **Google OAuth** client secret, and re-run OAuth.
2. Remove the file from git history (GitHub support / `git filter-repo`) or make the repo private.
3. Do not only delete the file in the web UI on the latest commit — old commits may still contain keys.
