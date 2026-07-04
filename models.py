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