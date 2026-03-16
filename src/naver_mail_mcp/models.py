"""Data models for Naver Mail MCP Server."""

from dataclasses import asdict, dataclass, field


@dataclass
class AttachmentMeta:
    """Attachment metadata returned in read_email responses."""

    filename: str
    content_type: str
    size: int
    part_number: str


@dataclass
class AttachmentContent:
    """Full attachment content returned by download_attachment."""

    filename: str
    content_type: str
    size: int
    content_base64: str


@dataclass
class Email:
    """Full email data."""

    uid: str
    message_id: str
    subject: str
    from_address: str
    to_addresses: list[str]
    cc_addresses: list[str]
    date: str
    body_text: str
    body_html: str
    flags: list[str]
    references: list[str]
    in_reply_to: str
    attachments: list[AttachmentMeta] = field(default_factory=list)


@dataclass
class EmailSummary:
    """Lightweight email summary for search results and draft listings."""

    uid: str
    subject: str
    from_address: str
    date: str
    is_read: bool
    has_attachments: bool


@dataclass
class Folder:
    """Mailbox folder information."""

    name: str
    raw_name: str
    message_count: int
    unseen_count: int


@dataclass
class Profile:
    """Account profile information."""

    email: str
    full_name: str
    total_messages: int
    unseen_messages: int


@dataclass
class SearchResult:
    """Paginated search result."""

    emails: list[EmailSummary]
    total_count: int
    page: int
    page_size: int
    has_more: bool


def to_dict(obj: object) -> dict:
    """Convert a dataclass instance to a JSON-serializable dict."""
    return asdict(obj)
