"""
Direct Google Docs / Gmail API calls (same behavior as saksham-mcp-server tools).
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from shared.google_auth import get_google_credentials

logger = logging.getLogger(__name__)


def append_to_doc(doc_id: str, content: str) -> dict:
    """Append timestamped content to a Google Doc."""
    if not doc_id or not content:
        return {"status": "error", "message": "doc_id and content are required"}

    creds = get_google_credentials()
    service = build("docs", "v1", credentials=creds)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_content = f"\n[{timestamp}]\n{content}\n"
    requests = [
        {
            "insertText": {
                "endOfSegmentLocation": {},
                "text": formatted_content,
            }
        }
    ]

    try:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        return {
            "status": "success",
            "message": "Content appended to document",
            "document_id": doc_id,
        }
    except HttpError as exc:
        logger.error("Google Docs API error: %s", exc)
        return {
            "status": "error",
            "message": "Google Docs API error",
            "details": str(exc),
        }


def create_email_draft(to: str, subject: str, body: str) -> dict:
    """Create a Gmail draft (does not send)."""
    if not to or not subject or not body:
        return {"status": "error", "message": "to, subject, and body are required"}

    creds = get_google_credentials()
    service = build("gmail", "v1", credentials=creds)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_body = f"\n[{timestamp}]\n\n{body}\n"

    message = MIMEText(formatted_body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
        return {
            "status": "success",
            "message": "Draft created",
            "draft_id": draft.get("id"),
        }
    except HttpError as exc:
        logger.error("Gmail API error: %s", exc)
        return {
            "status": "error",
            "message": "Gmail API error",
            "details": str(exc),
        }
