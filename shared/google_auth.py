"""
Google OAuth credentials — loaded from environment or from disk OUTSIDE the repo.

Never reads or writes token.json / credentials.json under the project folder.
"""
from __future__ import annotations

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from shared.secret_paths import credentials_path, ensure_secrets_outside_repo, token_path

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]


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


def _credentials_project_id_from_file(path) -> str:
    if not path.is_file():
        return ""
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        block = meta.get("installed", meta.get("web", {}))
        return block.get("project_id", "") or ""
    except (json.JSONDecodeError, OSError):
        return "invalid_json"


def get_google_credentials() -> Credentials:
    ensure_secrets_outside_repo()

    creds: Credentials | None = None
    env_token = _parse_env_json("GOOGLE_TOKEN_JSON")
    if env_token:
        creds = Credentials.from_authorized_user_info(env_token, SCOPES)
    else:
        tp = token_path()
        if tp.is_file():
            creds = Credentials.from_authorized_user_file(str(tp), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif _is_deployed():
            raise RuntimeError(
                "Google token missing or invalid. Set GOOGLE_TOKEN_JSON in Streamlit "
                "Secrets only — never in GitHub files."
            )
        else:
            raise RuntimeError(
                f"Google OAuth not configured. Run scripts/complete_oauth.ps1 "
                f"(stores token outside repo at {token_path().parent}) "
                "or set GOOGLE_TOKEN_JSON in .env."
            )

    return creds


def credentials_status() -> dict:
    ensure_secrets_outside_repo()
    cp = credentials_path()
    project_id = _credentials_project_id_from_env() or _credentials_project_id_from_file(cp)
    return {
        "token_present": bool(os.environ.get("GOOGLE_TOKEN_JSON")) or token_path().is_file(),
        "credentials_present": bool(os.environ.get("GOOGLE_CREDENTIALS_JSON")) or cp.is_file(),
        "credentials_project_id": project_id or None,
        "credentials_path": str(cp),
        "token_path": str(token_path()),
        "deployed_mode": _is_deployed(),
    }


def _credentials_project_id_from_env() -> str:
    data = _parse_env_json("GOOGLE_CREDENTIALS_JSON")
    if not data:
        return ""
    block = data.get("installed", data.get("web", {}))
    return block.get("project_id", "") or ""
