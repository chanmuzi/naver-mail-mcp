"""Runtime options read from environment variables."""

from __future__ import annotations

import os

READ_ONLY_ENV = "NAVER_MAIL_READ_ONLY"
MAX_MESSAGE_MB_ENV = "NAVER_MAIL_MAX_MESSAGE_MB"
DEFAULT_MAX_MESSAGE_MB = 50

_BYTES_PER_MB = 1024 * 1024
_DISABLED_VALUES = frozenset({"", "0", "false", "no", "off"})


def is_read_only() -> bool:
    """Whether the mutating tools (create_draft, send_email) are turned off.

    Any value other than an explicit "off" spelling enables read-only mode, so a
    typo in a safety switch never leaves the write tools exposed.
    """
    return os.environ.get(READ_ONLY_ENV, "").strip().lower() not in _DISABLED_VALUES


def max_message_bytes() -> int:
    """Largest encoded message (headers and MIME encoding included) to download."""
    raw = os.environ.get(MAX_MESSAGE_MB_ENV, "").strip()
    if not raw:
        return DEFAULT_MAX_MESSAGE_MB * _BYTES_PER_MB
    if not (raw.isascii() and raw.isdigit()) or int(raw) < 1:
        raise ValueError(f"{MAX_MESSAGE_MB_ENV} must be a positive integer (MiB), got '{raw}'.")
    return int(raw) * _BYTES_PER_MB
