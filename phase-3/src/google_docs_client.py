"""
GoogleDocsClient — integrates with saksham-mcp-server for Google Docs.

https://github.com/saksham20189575/saksham-mcp-server

When the MCP server is reachable, appends the weekly report to an existing
Google Doc (GOOGLE_DOC_ID). When unavailable or misconfigured, saves a local
Markdown file and returns a file:// URI as doc_id.
"""
import os
import requests
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

from shared.mcp_config import resolve_mcp_server_url

load_dotenv()


class GoogleDocsClient:
    """Client for saksham Google Docs MCP (append_to_doc) with local file fallback."""

    def __init__(self, mcp_server_url: Optional[str] = None):
        self.mcp_url = resolve_mcp_server_url(mcp_server_url)
        self._available: Optional[bool] = None

    def create_document(self, title: str, content: str) -> dict:
        """Append report content to Google Doc via MCP, or save locally.

        Args:
            title:   Report title (prepended to appended content).
            content: Body text (plain or markdown).

        Returns:
            dict with doc_id, doc_url, source, title, created_at
        """
        if self._is_mcp_available():
            doc_id = os.getenv("GOOGLE_DOC_ID", "").strip()
            if doc_id:
                return self._append_via_mcp(doc_id, title, content)
            print(
                "  MCP reachable but GOOGLE_DOC_ID is not set — "
                "create a Google Doc, copy its ID from the URL, and set GOOGLE_DOC_ID in .env"
            )
        return self._create_local_file(title, content)

    def get_document_url(self, doc_id: str) -> str:
        """Return the shareable URL for a document ID."""
        if doc_id.startswith("file://") or os.path.exists(doc_id):
            return doc_id if doc_id.startswith("file://") else f"file://{os.path.abspath(doc_id)}"
        return f"https://docs.google.com/document/d/{doc_id}/edit"

    def _is_mcp_available(self) -> bool:
        """Check once whether saksham MCP server is reachable (GET /)."""
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.mcp_url}/", timeout=3)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _append_via_mcp(self, doc_id: str, title: str, content: str) -> dict:
        """POST /append_to_doc — appends timestamped content to an existing doc."""
        formatted = f"# {title}\n\n{content}" if title else content
        try:
            resp = requests.post(
                f"{self.mcp_url}/append_to_doc",
                json={"doc_id": doc_id, "content": formatted},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "rejected":
                raise RuntimeError(data.get("message", "append_to_doc rejected"))

            if data.get("status") != "success":
                raise RuntimeError(
                    data.get("message", "append_to_doc failed")
                    + (f": {data.get('details', '')}" if data.get("details") else "")
                )

            resolved_id = data.get("document_id") or doc_id
            return {
                "doc_id": resolved_id,
                "doc_url": self.get_document_url(resolved_id),
                "source": "google_docs",
                "title": title,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"  MCP error: {e} — falling back to local file")
            self._available = False
            return self._create_local_file(title, content)

    def _create_local_file(self, title: str, content: str) -> dict:
        """Save report as a local Markdown file when MCP is unavailable."""
        output_dir = os.path.join("phase-3", "test-results", "reports")
        os.makedirs(output_dir, exist_ok=True)

        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)
        safe_title = safe_title.replace(" ", "_")[:80]
        filename = f"{safe_title}.md"
        filepath = os.path.abspath(os.path.join(output_dir, filename))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        doc_id = filepath
        doc_url = f"file://{filepath}"

        print(f"  [LOCAL FALLBACK] Report saved to: {filepath}")

        return {
            "doc_id": doc_id,
            "doc_url": doc_url,
            "source": "local_file",
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
