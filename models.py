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
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li        top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=list)

    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li@dataclass(slots=True)
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=liclass EmailAnalysis:
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    """
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    Stores the results of deterministic email analysis.
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    """
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    gmail_id: str
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    sender_domain: Optional[str]
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    category: str
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    importance: str
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    has_unsubscribe: int
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    has_attachment: int
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    has_html: int
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    confidence: float
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    analyzed_by: str
    top_10_sender_domains: List[SenderDomainStatistics] = field(default_factory=li    analyzed_at: str
