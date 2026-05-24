"""
Google OAuth credentials for Phases 3–4 (direct API, no MCP HTTP).

Secrets are read from environment variables ONLY — never written into the repo
(MCPServer/saksham-mcp-server/credentials.json or token.json).
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


def _parse_env_json(key: str) -> dict | None:
    raw = os.environ.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{key} is not valid JSON") from exc


def _credentials_project_id_from_env() -> str:
    data = _parse_env_json("GOOGLE_CREDENTIALS_JSON")
    if not data:
        return ""
    block = data.get("installed", data.get("web", {}))
    return block.get("project_id", "") or ""


def _credentials_project_id_from_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        block = meta.get("installed", meta.get("web", {}))
        return block.get("project_id", "") or ""
    except (json.JSONDecodeError, OSError):
        return "invalid_json"


def get_google_credentials() -> Credentials:
    """Load and refresh Google credentials (non-interactive on cloud)."""
    creds: Credentials | None = None
    env_token = _parse_env_json("GOOGLE_TOKEN_JSON")
    if env_token:
        creds = Credentials.from_authorized_user_info(env_token, SCOPES)
    elif TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Do NOT write refreshed token to disk — keeps secrets out of the repo.
        elif _is_deployed():
            raise RuntimeError(
                "Google token missing or invalid. Set GOOGLE_TOKEN_JSON in Streamlit "
                "Secrets only (not in GitHub). Re-export locally with "
                "scripts/export_streamlit_secrets.ps1 if needed."
            )
        else:
            raise RuntimeError(
                "Google OAuth not configured. Run scripts/complete_oauth.ps1 locally "
                f"(creates gitignored {TOKEN_PATH.name}) or set GOOGLE_TOKEN_JSON in .env."
            )

    return creds


def credentials_status() -> dict:
    """Lightweight check for UI / health (no API calls, no disk writes)."""
    project_id = _credentials_project_id_from_env() or _credentials_project_id_from_file(
        CREDENTIALS_PATH
    )
    return {
        "token_present": bool(os.environ.get("GOOGLE_TOKEN_JSON")) or TOKEN_PATH.is_file(),
        "credentials_present": bool(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
        or CREDENTIALS_PATH.is_file(),
        "credentials_project_id": project_id or None,
        "deployed_mode": _is_deployed(),
    }
