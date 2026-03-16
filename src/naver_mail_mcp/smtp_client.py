"""SMTP client for Naver Mail."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


SMTP_HOST = "smtp.naver.com"
SMTP_PORT = 465


class NaverSMTPError(Exception):
    """SMTP operation failed."""


def send_email(
    email_address: str,
    password: str,
    full_name: str,
    to: list[str],
    subject: str,
    body: str,
    body_type: str = "text/plain",
    cc: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> dict:
    """Send an email via Naver SMTP.

    For replies, provide in_reply_to (Message-ID of the email being
    replied to) and references (list of Message-IDs in the thread).
    """
    msg = EmailMessage()
    if full_name:
        msg["From"] = f"{full_name} <{email_address}>"
    else:
        msg["From"] = email_address
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject

    if cc:
        msg["Cc"] = ", ".join(cc)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references)

    if body_type == "text/html":
        msg.set_content(body, subtype="html", charset="utf-8")
    else:
        msg.set_content(body, charset="utf-8")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(email_address, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise NaverSMTPError(
            "SMTP authentication failed. "
            "Check your Naver email address and app password."
        ) from e
    except smtplib.SMTPException as e:
        raise NaverSMTPError(f"Failed to send email: {e}") from e
    except OSError as e:
        raise NaverSMTPError(
            f"Cannot connect to Naver SMTP server ({SMTP_HOST}:{SMTP_PORT}). "
            f"Check your network connection. Error: {e}"
        ) from e

    return {"success": True, "message": f"Email sent to {', '.join(to)}"}
