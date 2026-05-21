"""Shared configuration for saksham-mcp-server integration."""
import os
from typing import Optional

# https://github.com/saksham20189575/saksham-mcp-server
DEFAULT_MCP_SERVER_URL = "http://127.0.0.1:8000"


def resolve_mcp_server_url(specific_url: Optional[str] = None) -> str:
    """Resolve MCP base URL (no trailing slash)."""
    url = (
        specific_url
        or os.getenv("MCP_SERVER_URL")
        or os.getenv("GOOGLE_DOCS_MCP_SERVER_URL")
        or os.getenv("GMAIL_MCP_SERVER_URL")
        or DEFAULT_MCP_SERVER_URL
    )
    return url.rstrip("/")
