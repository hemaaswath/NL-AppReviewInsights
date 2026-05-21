"""
Tests for GoogleDocsClient — MCP calls mocked, local fallback tested for real.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from google_docs_client import GoogleDocsClient


@pytest.fixture
def client_no_mcp(tmp_path, monkeypatch):
    """Client that always uses local fallback (MCP unavailable)."""
    monkeypatch.chdir(tmp_path)
    c = GoogleDocsClient(mcp_server_url="http://localhost:9999")
    c._available = False   # force fallback
    return c


@pytest.fixture
def client_with_mcp():
    """Client with mocked MCP server that returns success."""
    c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
    c._available = True
    return c


class TestGoogleDocsClientLocalFallback:

    def test_create_document_returns_dict(self, client_no_mcp):
        result = client_no_mcp.create_document("Test Title", "Test content")
        assert isinstance(result, dict)

    def test_create_document_has_required_keys(self, client_no_mcp):
        result = client_no_mcp.create_document("Test Title", "Test content")
        for key in ("doc_id", "doc_url", "source", "title", "created_at"):
            assert key in result

    def test_local_fallback_source_is_local_file(self, client_no_mcp):
        result = client_no_mcp.create_document("Test Title", "Test content")
        assert result["source"] == "local_file"

    def test_local_fallback_creates_file(self, client_no_mcp, tmp_path):
        result = client_no_mcp.create_document("My Report", "Report content here")
        assert os.path.exists(result["doc_id"])

    def test_local_fallback_file_has_content(self, client_no_mcp, tmp_path):
        result = client_no_mcp.create_document("My Report", "Report content here")
        with open(result["doc_id"], encoding="utf-8") as f:
            content = f.read()
        assert "Report content here" in content

    def test_local_fallback_doc_url_is_file_uri(self, client_no_mcp):
        result = client_no_mcp.create_document("Test", "Content")
        assert result["doc_url"].startswith("file://")

    def test_local_fallback_title_preserved(self, client_no_mcp):
        result = client_no_mcp.create_document("My Weekly Pulse", "Content")
        assert result["title"] == "My Weekly Pulse"

    def test_local_fallback_created_at_is_iso(self, client_no_mcp):
        from datetime import datetime
        result = client_no_mcp.create_document("Test", "Content")
        # Should parse without error
        datetime.fromisoformat(result["created_at"])

    def test_special_chars_in_title_handled(self, client_no_mcp):
        result = client_no_mcp.create_document(
            "Weekly Pulse — Groww — 2026-W21", "Content"
        )
        assert os.path.exists(result["doc_id"])

    def test_multiple_docs_create_separate_files(self, client_no_mcp):
        r1 = client_no_mcp.create_document("Report Week 20", "Content A")
        r2 = client_no_mcp.create_document("Report Week 21", "Content B")
        assert r1["doc_id"] != r2["doc_id"]


class TestGoogleDocsClientMCPPath:

    def test_mcp_success_returns_google_docs_source(self, client_with_mcp, monkeypatch):
        monkeypatch.setenv("GOOGLE_DOC_ID", "doc-abc-123")

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {
            "status": "success",
            "message": "Content appended to document",
            "document_id": "doc-abc-123",
        }
        post_resp.raise_for_status = MagicMock()

        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.raise_for_status = MagicMock()

        with patch("google_docs_client.requests.post", return_value=post_resp) as mock_post, \
             patch("google_docs_client.requests.get", return_value=get_resp):
            result = client_with_mcp.create_document("Test Doc", "Content")

        assert result["source"] == "google_docs"
        assert result["doc_id"] == "doc-abc-123"
        assert "docs.google.com" in result["doc_url"]
        assert mock_post.call_args.kwargs["json"]["doc_id"] == "doc-abc-123"

    def test_mcp_failure_falls_back_to_local(self, client_with_mcp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("google_docs_client.requests.post",
                   side_effect=Exception("Connection refused")):
            result = client_with_mcp.create_document("Test Doc", "Content")
        assert result["source"] == "local_file"

    def test_mcp_unavailable_check(self):
        c = GoogleDocsClient(mcp_server_url="http://localhost:9999")
        with patch("google_docs_client.requests.get",
                   side_effect=Exception("Connection refused")):
            available = c._is_mcp_available()
        assert available is False

    def test_mcp_available_check(self):
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("google_docs_client.requests.get", return_value=mock_resp):
            available = c._is_mcp_available()
        assert available is True


class TestGoogleDocsClientGetUrl:

    def test_get_url_for_google_doc_id(self):
        c = GoogleDocsClient()
        url = c.get_document_url("abc123")
        assert "docs.google.com" in url
        assert "abc123" in url

    def test_get_url_for_file_path(self, tmp_path):
        c = GoogleDocsClient()
        path = str(tmp_path / "report.md")
        url = c.get_document_url(f"file://{path}")
        assert url == f"file://{path}"
