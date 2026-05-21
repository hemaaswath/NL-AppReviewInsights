"""
Extended corner-case tests for GoogleDocsClient.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from google_docs_client import GoogleDocsClient


@pytest.fixture
def local_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = GoogleDocsClient(mcp_server_url="http://localhost:9999")
    c._available = False
    return c


# ── Local fallback edge cases ─────────────────────────────────────────────────

class TestLocalFallbackEdgeCases:

    def test_empty_title_creates_file(self, local_client, tmp_path):
        result = local_client.create_document("", "Some content")
        assert os.path.exists(result["doc_id"])

    def test_empty_content_creates_empty_file(self, local_client, tmp_path):
        result = local_client.create_document("Empty Report", "")
        assert os.path.exists(result["doc_id"])
        with open(result["doc_id"], encoding="utf-8") as f:
            assert f.read() == ""

    def test_very_long_title_filename_capped(self, local_client, tmp_path):
        long_title = "A" * 200
        result = local_client.create_document(long_title, "Content")
        filename = os.path.basename(result["doc_id"])
        # Filename (without .md) should be ≤80 chars
        assert len(filename.replace(".md", "")) <= 80

    def test_unicode_title_handled(self, local_client, tmp_path):
        result = local_client.create_document("Rapport Hebdo — Semaine 21", "Contenu")
        assert os.path.exists(result["doc_id"])

    def test_overwrite_same_title_updates_content(self, local_client, tmp_path):
        local_client.create_document("Same Title", "First content")
        local_client.create_document("Same Title", "Updated content")
        # Find the file
        reports_dir = tmp_path / "phase-3" / "test-results" / "reports"
        files = list(reports_dir.glob("*.md"))
        assert len(files) == 1
        with open(files[0], encoding="utf-8") as f:
            assert "Updated content" in f.read()

    def test_unicode_content_written_correctly(self, local_client, tmp_path):
        content = "Résumé: 🎉 App crashes — très mauvais!"
        result = local_client.create_document("Unicode Test", content)
        with open(result["doc_id"], encoding="utf-8") as f:
            assert "Résumé" in f.read()

    def test_doc_id_is_absolute_path(self, local_client, tmp_path):
        result = local_client.create_document("Test", "Content")
        assert os.path.isabs(result["doc_id"])

    def test_availability_cached_after_first_check(self, local_client):
        """_available is already False — should not make network call."""
        with patch("google_docs_client.requests.get") as mock_get:
            local_client._is_mcp_available()
            mock_get.assert_not_called()

    def test_newlines_in_content_preserved(self, local_client, tmp_path):
        content = "Line 1\nLine 2\nLine 3"
        result = local_client.create_document("Newlines", content)
        with open(result["doc_id"], encoding="utf-8") as f:
            text = f.read()
        assert "Line 1\nLine 2" in text


# ── MCP path edge cases ───────────────────────────────────────────────────────

class TestMCPEdgeCases:

    def test_mcp_non_200_health_marks_unavailable(self):
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("google_docs_client.requests.get", return_value=mock_resp):
            available = c._is_mcp_available()
        assert available is False

    def test_mcp_error_status_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GOOGLE_DOC_ID", "doc-123")
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        c._available = True

        def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"status": "error", "message": "API error"}
            resp.raise_for_status = MagicMock()
            return resp

        with patch("google_docs_client.requests.post", side_effect=mock_post):
            result = c.create_document("Test", "Content")
        assert result["source"] == "local_file"

    def test_mcp_append_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GOOGLE_DOC_ID", "doc-123")
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        c._available = True

        with patch(
            "google_docs_client.requests.post",
            side_effect=Exception("Connection refused"),
        ):
            result = c.create_document("Test", "Content")
        assert result["source"] == "local_file"

    def test_mcp_success_uses_constructed_doc_url(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_DOC_ID", "doc-xyz")
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        c._available = True

        def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.json.return_value = {
                "status": "success",
                "document_id": "doc-xyz",
            }
            resp.raise_for_status = MagicMock()
            return resp

        with patch("google_docs_client.requests.post", side_effect=mock_post):
            result = c.create_document("Test", "Content")

        assert result["source"] == "google_docs"
        assert "doc-xyz" in result["doc_url"]

    def test_mcp_without_google_doc_id_uses_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GOOGLE_DOC_ID", raising=False)
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        c._available = True

        result = c.create_document("Test", "Content")
        assert result["source"] == "local_file"

    def test_mcp_availability_cached_true(self):
        """Once available=True is cached, no further health checks."""
        c = GoogleDocsClient()
        c._available = True
        with patch("google_docs_client.requests.get") as mock_get:
            result = c._is_mcp_available()
        mock_get.assert_not_called()
        assert result is True

    def test_mcp_timeout_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c = GoogleDocsClient(mcp_server_url="http://127.0.0.1:8000")
        c._available = True
        import requests as req
        with patch("google_docs_client.requests.post",
                   side_effect=req.exceptions.Timeout("timed out")):
            result = c.create_document("Test", "Content")
        assert result["source"] == "local_file"


# ── get_document_url edge cases ───────────────────────────────────────────────

class TestGetDocumentUrlEdgeCases:

    def test_existing_local_path_returns_file_uri(self, tmp_path):
        c = GoogleDocsClient()
        path = str(tmp_path / "report.md")
        open(path, "w").close()
        url = c.get_document_url(path)
        assert url.startswith("file://")
        assert path.replace("\\", "/") in url.replace("\\", "/")

    def test_google_doc_id_produces_edit_url(self):
        c = GoogleDocsClient()
        url = c.get_document_url("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")
        assert url == "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit"

    def test_empty_doc_id_returns_url_with_empty_id(self):
        c = GoogleDocsClient()
        url = c.get_document_url("")
        assert "docs.google.com" in url
