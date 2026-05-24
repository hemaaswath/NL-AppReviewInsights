"""
Secret file locations — ALWAYS outside the git repository.

OAuth tokens and credentials must never live under the project folder.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Filenames that must not exist anywhere under REPO_ROOT (except .git)
SECRET_FILENAMES = frozenset(
    {
        "token.json",
        "credentials.json",
        "secrets.toml",
        "secrets_export.txt",
        ".oauth_client_id",
        "oauth_authorize_url.txt",
    }
)

# Also purge .env from repo if someone copies it wrong — real local file is gitignored
# but we only auto-purge OAuth-named files to avoid deleting working .env during dev.
# Use explicit .env path check in purge.


def local_secrets_dir() -> Path:
    """Directory for OAuth files (outside repo)."""
    override = os.getenv("GROWW_SECRETS_DIR", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "groww-insights"
    else:
        path = Path.home() / ".config" / "groww-insights"
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_path() -> Path:
    return local_secrets_dir() / "token.json"


def credentials_path() -> Path:
    return local_secrets_dir() / "credentials.json"


def legacy_repo_oauth_paths() -> list[Path]:
    """Old locations inside the repo (must be migrated / removed)."""
    mcp = REPO_ROOT / "MCPServer" / "saksham-mcp-server"
    return [
        mcp / "token.json",
        mcp / "credentials.json",
        mcp / ".oauth_client_id",
        mcp / "oauth_authorize_url.txt",
        REPO_ROOT / ".streamlit" / "secrets.toml",
        REPO_ROOT / ".streamlit" / "secrets_export.txt",
    ]


def migrate_legacy_secrets() -> list[str]:
    """Move OAuth files from repo paths to local_secrets_dir (once)."""
    actions: list[str] = []
    dest_token = token_path()
    dest_creds = credentials_path()

    for src in legacy_repo_oauth_paths():
        if not src.is_file():
            continue
        if src.name == "token.json" and not dest_token.is_file():
            shutil.copy2(src, dest_token)
            actions.append(f"migrated {src.name} -> {dest_token}")
        elif src.name == "credentials.json" and not dest_creds.is_file():
            shutil.copy2(src, dest_creds)
            actions.append(f"migrated {src.name} -> {dest_creds}")
        try:
            src.unlink()
            actions.append(f"removed from repo: {src.relative_to(REPO_ROOT)}")
        except OSError:
            pass
    return actions


def _is_under_git(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT / ".git")
        return True
    except ValueError:
        return False


def purge_secret_files_from_repo() -> list[str]:
    """
    Delete secret-named files found anywhere under the repo tree.
    Called on app startup so secrets never accumulate for accidental git add.
    """
    removed: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or _is_under_git(path):
            continue
        if path.name not in SECRET_FILENAMES:
            continue
        # Keep example templates
        if path.name == "secrets.toml" and "example" in path.as_posix():
            continue
        try:
            rel = path.relative_to(REPO_ROOT)
            path.unlink()
            removed.append(str(rel))
        except OSError:
            pass
    return removed


def ensure_secrets_outside_repo() -> None:
    """Migrate legacy paths then purge any secret files still in the repo."""
    migrate_legacy_secrets()
    purge_secret_files_from_repo()
