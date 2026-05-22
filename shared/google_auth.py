"""
Google OAuth credentials for Phases 3–4 (direct API, no MCP HTTP).

Uses GOOGLE_TOKEN_JSON / GOOGLE_CREDENTIALS_JSON from the environment
(Streamlit secrets, Railway, or local .env). Falls back to
MCPServer/saksham-mcp-server/token.json when present.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "MCPServer" / "saksham-mcp-server"
TOKEN_PATH = MCP_DIR / "token.json"
CREDENTIALS_PATH = MCP_DIR / "credentials.json"


def _is_deployed() -> bool:
    return bool(
        os.environ.get("RENDER")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("STREAMLIT_DEPLOYMENT")
        or os.environ.get("IS_DEPLOYED")
    )


def _write_credentials_from_env() -> None:
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not raw:
        return
    overwrite = os.getenv("GOOGLE_CREDENTIALS_JSON_OVERWRITE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if overwrite or not CREDENTIALS_PATH.is_file():
        MCP_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_PATH.write_text(raw, encoding="utf-8")


def get_google_credentials() -> Credentials:
    """Load and refresh Google credentials (non-interactive on cloud)."""
    _write_credentials_from_env()

    creds: Credentials | None = None
    env_token = os.environ.get("GOOGLE_TOKEN_JSON")
    if env_token:
        creds = Credentials.from_authorized_user_info(json.loads(env_token), SCOPES)
    elif TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif _is_deployed():
            raise RuntimeError(
                "Google token missing or invalid. Set GOOGLE_TOKEN_JSON in Streamlit "
                "secrets (run scripts/export_streamlit_secrets.ps1 locally first)."
            )
        else:
            raise RuntimeError(
                f"Google OAuth not configured. Run scripts/complete_oauth.ps1 or set "
                f"GOOGLE_TOKEN_JSON. Expected token at {TOKEN_PATH}"
            )

    return creds


def credentials_status() -> dict:
    """Lightweight check for UI / health (no API calls)."""
    _write_credentials_from_env()
    project_id = ""
    if CREDENTIALS_PATH.is_file():
        try:
            meta = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
            block = meta.get("installed", meta.get("web", {}))
            project_id = block.get("project_id", "")
        except json.JSONDecodeError:
            project_id = "invalid_json"

    return {
        "token_present": bool(os.environ.get("GOOGLE_TOKEN_JSON")) or TOKEN_PATH.is_file(),
        "credentials_present": bool(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
        or CREDENTIALS_PATH.is_file(),
        "credentials_project_id": project_id or None,
        "deployed_mode": _is_deployed(),
    }
