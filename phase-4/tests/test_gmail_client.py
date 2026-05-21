"""
Tests for GmailMCPClient (saksham-mcp-server).
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import requests

from gmail_client import GmailMCPClient


def workspace_test_dir() -> Path:
    directory = Path.cwd() / "phase-4" / "test-results" / "unit" / uuid4().hex
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def mock_response(data=None, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.content = b"{}"
    response.json.return_value = data or {}
    response.raise_for_status = MagicMock()
    return response


class TestGmailMCPClientAvailability:
    def test_mcp_available_check(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        with patch("gmail_client.requests.get", return_value=mock_response({"message": "running"})):
            assert client._is_mcp_available() is True

    def test_mcp_unavailable_without_fallback_raises(self):
        client = GmailMCPClient(mcp_server_url="http://localhost:9999")
        with patch("gmail_client.requests.get", side_effect=Exception("down")):
            with pytest.raises(ConnectionError, match="Gmail MCP server is unavailable"):
                client.create_draft("to@example.com", "Subject", "Body")

    def test_non_200_health_is_unavailable(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        with patch("gmail_client.requests.get", return_value=mock_response(status_code=503)):
            assert client._is_mcp_available() is False

    def test_env_enables_local_fallback(self, monkeypatch):
        monkeypatch.setenv("GMAIL_ALLOW_LOCAL_FALLBACK", "true")
        client = GmailMCPClient(mcp_server_url="http://localhost:9999")

        assert client.allow_local_fallback is True


class TestGmailMCPClientDrafts:
    def test_create_draft_via_mcp_returns_gmail_source(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        client._available = True

        with patch(
            "gmail_client.requests.post",
            return_value=mock_response({"status": "success", "draft_id": "draft-123"}),
        ) as post:
            result = client.create_draft("to@example.com", "Subject", "Body", "<p>Body</p>")

        assert result["source"] == "gmail"
        assert result["draft_id"] == "draft-123"
        payload = post.call_args.kwargs["json"]
        assert payload["to"] == "to@example.com"
        assert "HTML summary" in payload["body"]

    def test_create_draft_missing_draft_id_raises(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        client._available = True

        with patch(
            "gmail_client.requests.post",
            return_value=mock_response({"status": "success"}),
        ):
            with pytest.raises(ValueError, match="draft_id"):
                client.create_draft("to@example.com", "Subject", "Body")

        assert client._available is False

    def test_create_draft_rejected_raises(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        client._available = True

        with patch(
            "gmail_client.requests.post",
            return_value=mock_response({"status": "rejected", "message": "User rejected"}),
        ):
            with pytest.raises(RuntimeError, match="rejected"):
                client.create_draft("to@example.com", "Subject", "Body")

    def test_create_draft_error_status_raises(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        client._available = True

        with patch(
            "gmail_client.requests.post",
            return_value=mock_response(
                {"status": "error", "message": "Gmail API error", "details": "invalid_grant"}
            ),
        ):
            with pytest.raises(ValueError, match="Gmail API error"):
                client.create_draft("to@example.com", "Subject", "Body")

        assert client._available is False

    def test_explicit_local_fallback_creates_eml(self, monkeypatch):
        monkeypatch.chdir(workspace_test_dir())
        client = GmailMCPClient(
            mcp_server_url="http://localhost:9999",
            allow_local_fallback=True,
        )
        client._available = False

        result = client.create_draft("to@example.com", "Subject", "Body", "<p>Body</p>")
        filepath = result["draft_id"].replace("local://", "")

        assert result["source"] == "local_file"
        assert os.path.exists(filepath)

    def test_mcp_create_failure_uses_fallback_only_when_enabled(self, monkeypatch):
        monkeypatch.chdir(workspace_test_dir())
        client = GmailMCPClient(allow_local_fallback=True)
        client._available = True

        with patch("gmail_client.requests.post", side_effect=requests.Timeout("slow")):
            result = client.create_draft("to@example.com", "Subject", "Body")

        assert result["source"] == "local_file"
        assert client._available is False


class TestGmailMCPClientSend:
    def test_send_draft_returns_draft_created(self):
        client = GmailMCPClient(mcp_server_url="http://127.0.0.1:8000")
        client._available = True

        result = client.send_draft("draft-123")

        assert result["status"] == "draft_created"
        assert result["message_id"] == "draft-123"

    def test_send_non_local_draft_raises_when_mcp_unavailable(self):
        client = GmailMCPClient(mcp_server_url="http://localhost:9999")
        client._available = False

        with pytest.raises(ConnectionError, match="became unavailable"):
            client.send_draft("draft-123")

    def test_local_draft_is_not_reported_as_sent(self):
        client = GmailMCPClient()
        result = client.send_draft("local://tmp/report.eml")

        assert result["status"] == "draft_saved"
        assert result["message_id"] is None
