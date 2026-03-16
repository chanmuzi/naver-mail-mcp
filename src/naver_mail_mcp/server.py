"""Naver Mail MCP Server.

Provides 9 tools for interacting with Naver Mail via IMAP/SMTP.
All logging goes to stderr — stdout is reserved for MCP JSON-RPC.
"""

from __future__ import annotations

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from . import imap_client, smtp_client
from .models import to_dict

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s - %(message)s")
logger = logging.getLogger("naver-mail-mcp")

mcp = FastMCP("naver-mail-mcp")


def _get_credentials() -> tuple[str, str, str]:
    """Get credentials from environment variables.

    Returns:
        Tuple of (email, password, full_name).

    Raises:
        ValueError: If required env vars are missing.
    """
    email_address = os.environ.get("NAVER_EMAIL_ADDRESS", "")
    password = os.environ.get("NAVER_EMAIL_PASSWORD", "")
    full_name = os.environ.get("NAVER_FULL_NAME", "")

    if not email_address or not password:
        raise ValueError(
            "Missing required environment variables: "
            "NAVER_EMAIL_ADDRESS and NAVER_EMAIL_PASSWORD must be set."
        )
    return email_address, password, full_name


@mcp.tool()
def get_profile() -> str:
    """Get Naver Mail account profile including email address, display name, total messages, and unread count."""
    email_addr, password, full_name = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.get_profile(conn, email_addr, full_name)
    return json.dumps(to_dict(result), ensure_ascii=False)


@mcp.tool()
def search_emails(
    folder: str = "INBOX",
    sender: str | None = None,
    recipient: str | None = None,
    subject: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    is_read: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Search emails in a folder with optional filters.

    Args:
        folder: Mailbox folder to search in (default: INBOX).
        sender: Filter by sender email or name.
        recipient: Filter by recipient email or name.
        subject: Filter by subject keyword.
        date_from: Filter emails after this date (DD-Mon-YYYY, e.g., 01-Jan-2026).
        date_to: Filter emails before this date (DD-Mon-YYYY, e.g., 31-Dec-2026).
        is_read: Filter by read status (true=read, false=unread, null=all).
        page: Page number for pagination (default: 1).
        page_size: Number of results per page (default: 20).

    Returns:
        JSON string with search results including email summaries and pagination info.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.search_emails(
            conn,
            folder=folder,
            sender=sender,
            recipient=recipient,
            subject=subject,
            date_from=date_from,
            date_to=date_to,
            is_read=is_read,
            page=page,
            page_size=page_size,
        )
    return json.dumps(to_dict(result), ensure_ascii=False)


@mcp.tool()
def read_email(uid: str, folder: str = "INBOX") -> str:
    """Read a full email by UID.

    Args:
        uid: The unique identifier of the email.
        folder: Mailbox folder containing the email (default: INBOX).

    Returns:
        JSON string with full email data including headers, body (text and HTML), and attachment metadata.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.read_email(conn, uid, folder)
    return json.dumps(to_dict(result), ensure_ascii=False)


@mcp.tool()
def read_thread(message_id: str, folder: str = "INBOX") -> str:
    """Read an email thread by Message-ID.

    Finds all related emails via References and In-Reply-To headers.

    Args:
        message_id: The Message-ID header value of any email in the thread.
        folder: Mailbox folder to search in (default: INBOX).

    Returns:
        JSON string with a list of all emails in the thread, sorted by date.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.read_thread(conn, message_id, folder)
    return json.dumps([to_dict(e) for e in result], ensure_ascii=False)


@mcp.tool()
def list_folders() -> str:
    """List all mailbox folders with message counts.

    Returns:
        JSON string with a list of folders, each containing name, message count, and unseen count.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.list_folders(conn)
    return json.dumps([to_dict(f) for f in result], ensure_ascii=False)


@mcp.tool()
def create_draft(
    to: list[str],
    subject: str,
    body: str,
    body_type: str = "text/plain",
    cc: list[str] | None = None,
) -> str:
    """Save an email draft to the Drafts folder.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Email body content.
        body_type: Content type — 'text/plain' (default) or 'text/html'.
        cc: Optional list of CC email addresses.

    Returns:
        JSON string confirming draft was saved.
    """
    email_addr, password, full_name = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.create_draft(
            conn, email_addr, full_name, to, subject, body, body_type, cc
        )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def list_drafts() -> str:
    """List all drafts in the Drafts folder.

    Returns:
        JSON string with a list of draft email summaries.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.list_drafts(conn)
    return json.dumps([to_dict(d) for d in result], ensure_ascii=False)


@mcp.tool()
def send_email(
    to: list[str],
    subject: str,
    body: str,
    body_type: str = "text/plain",
    cc: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> str:
    """Send an email via SMTP.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Email body content.
        body_type: Content type — 'text/plain' (default) or 'text/html'.
        cc: Optional list of CC email addresses.
        in_reply_to: Message-ID of the email being replied to (for replies).
        references: List of Message-IDs in the thread (for replies).

    Returns:
        JSON string confirming email was sent.
    """
    email_addr, password, full_name = _get_credentials()
    result = smtp_client.send_email(
        email_addr, password, full_name,
        to, subject, body, body_type, cc,
        in_reply_to, references,
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def download_attachment(uid: str, part_number: str, folder: str = "INBOX") -> str:
    """Download an email attachment by UID and MIME part number.

    The part_number can be found in the attachments list from read_email.

    Args:
        uid: The unique identifier of the email containing the attachment.
        part_number: The MIME part number of the attachment (from read_email response).
        folder: Mailbox folder containing the email (default: INBOX).

    Returns:
        JSON string with attachment metadata and base64-encoded content.
    """
    email_addr, password, _ = _get_credentials()
    with imap_client.imap_connection(email_addr, password) as conn:
        result = imap_client.download_attachment(conn, uid, part_number, folder)
    return json.dumps(to_dict(result), ensure_ascii=False)


def main():
    """Entry point for the MCP server."""
    try:
        _get_credentials()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    logger.info("Starting Naver Mail MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
