"""Resolve a writable SQLite path for local dev and Streamlit Cloud."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def is_streamlit_runtime() -> bool:
    return bool(
        os.getenv("STREAMLIT_RUNTIME_ENV")
        or os.getenv("STREAMLIT_DEPLOYMENT")
        or os.getenv("STREAMLIT_SERVER_PORT")
    )


def is_streamlit_cloud() -> bool:
    """True on Streamlit Community Cloud (*.streamlit.app), not local `streamlit run`."""
    runtime = (os.getenv("STREAMLIT_RUNTIME_ENV") or os.getenv("STREAMLIT_SERVER_ENV") or "").lower()
    if runtime in {"cloud", "community-cloud"}:
        return True
    host = (os.getenv("HOSTNAME") or os.getenv("STREAMLIT_SERVER_ADDRESS") or "").lower()
    return host.endswith(".streamlit.app") or ".streamlit.app" in host


def resolve_database_path(path: str | None = None) -> str:
    """
    Pick a SQLite file path that exists and is writable.

    On Streamlit Cloud, ``data/reviews.db`` often fails (read-only or missing dir);
    use ``/tmp`` instead unless the user sets an explicit absolute path.
    """
    raw = (path or os.getenv("DATABASE_PATH") or "data/reviews.db").strip()
    raw = raw.replace("\\", "/")

    if is_streamlit_runtime():
        if not raw or raw == "data/reviews.db" or raw.startswith("data/"):
            raw = str(Path(tempfile.gettempdir()) / "groww_reviews.db")

    abs_path = str(Path(raw).expanduser().resolve())
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return abs_path


def sqlite_url(database_path: str) -> str:
    """Build a SQLAlchemy SQLite URL (handles absolute paths on Linux)."""
    normalized = database_path.replace("\\", "/")
    if normalized.startswith("/"):
        return f"sqlite:///{normalized}"
    return f"sqlite:///{normalized}"
