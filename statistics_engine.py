"""
MailCleaner Statistics Engine

Read-only mailbox reporting services.
"""

from __future__ import annotations

from database import DatabaseManager
from models import (
    MailboxStatistics,
    CategoryStatistics,
    SenderDomainStatistics,
)


class StatisticsEngine:
    """
    Provide read-only mailbox statistics using an injected database manager.
    """

    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    def get_mailbox_statistics(self) -> MailboxStatistics:
        """
        Return overall mailbox statistics.
        """

        mailbox_stats = self.database_manager.get_mailbox_statistics()

        # Compute unique sender count
        mailbox_stats.total_unique_senders = self.database_manager.get_unique_sender_count()

        # Compute unique domain count
        mailbox_stats.total_unique_domains = self.database_manager.get_unique_domain_count()

        # Compute top 10 sender domains
        mailbox_stats.top_10_sender_domains = self.database_manager.get_top_sender_domains(limit=10)

        return mailbox_stats

    def get_category_statistics(self) -> list[CategoryStatistics]:
        """
        Return analysis category counts sorted by descending count.
        """

        return self.database_manager.get_category_statistics()

    def get_sender_domain_statistics(
        self,
        limit: int = 25,
    ) -> list[SenderDomainStatistics]:
        """
        Return top analyzed sender domains.
        """

        return self.database_manager.get_sender_domain_statistics(limit)

    def get_unknown_sender_domains(
        self,
        limit: int = 25,
    ) -> list[SenderDomainStatistics]:
        """
        Return top sender domains with unknown analysis category.
        """

        return self.database_manager.get_unknown_sender_domain_statistics(limit)
