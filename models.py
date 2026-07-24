"""
MailCleaner Data Models

Shared dataclasses used across the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from models import SenderDomainStatistics


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
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=list)
