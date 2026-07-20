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
