"""
MailCleaner Data Models

Shared dataclasses used across the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class GmailProfile:
    """
    Represents the authenticated Gmail account.
    """

    email_address: str
    messages_total: int
    threads_total: int
    history_id: str


@dataclass(slots=True)
class EmailMetadata:
    """
    Represents Gmail email metadata stored locally.
    """

    gmail_id: str
    thread_id: Optional[str] = None
    history_id: Optional[str] = None
    internal_date: Optional[int] = None
    label_ids: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
    date_header: Optional[str] = None
    snippet: Optional[str] = None
    size_estimate: Optional[int] = None
    is_read: int = 0
    is_starred: int = 0
    is_important: int = 0
    last_synced: Optional[str] = None


@dataclass(slots=True)
class EmailContent:
    """
    Represents extracted Gmail message content.
    """

    gmail_id: str
    plain_text: str
    html_body: str
    mime_type: str
    attachment_count: int = 0

@dataclass(slots=True)
class EmailAnalysis:
    """
    Represents persisted email analysis results.
    """

    gmail_id: str
    sender_domain: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[str] = None
    has_unsubscribe: int = 0
    has_attachment: int = 0
    has_html: int = 0
    confidence: Optional[float] = None
    analyzed_by: Optional[str] = None
    analyzed_at: Optional[str] = None


@dataclass(slots=True)
class AnalysisStatistics:
    """
    Email analysis processing statistics.
    """

    total_selected: int = 0
    analyzed: int = 0
    classified: int = 0
    unknown: int = 0
    failed: int = 0


@dataclass(slots=True)
class MailboxStatistics:
    """
    Current mailbox analysis counts.
    """

    total_emails: int = 0
    total_content: int = 0
    total_analysis: int = 0
    classified: int = 0
    unknown: int = 0
    failed_analysis: int = 0
    total_unique_senders: int = 0
    total_unique_domains: int = 0
    top_10_sender_domains: list[SenderDomainStatistics] | None = None

@dataclass(slots=True)
class CategoryStatistics:
    """
    Email analysis count for one category.
    """

    category: str
    count: int


@dataclass(slots=True)
class SenderDomainStatistics:
    """
    Email analysis count for one sender domain.
    """

    sender_domain: str
    count: int


@dataclass(slots=True)
class SyncStatistics:
    """
    Metadata synchronization statistics.
    """

    processed: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(slots=True)
class SenderStatistics:
    """
    Sender analytics.
    """

    sender: str
    display_name: Optional[str]
    count: int
