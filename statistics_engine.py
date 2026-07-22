"""
MailCleaner Statistics Engine

Read-only mailbox reporting services.
"""

from __future__ import annotations

from database import DatabaseManager
from models import (
    CategoryStatistics,
    MailboxStatistics,
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

        return self.database_manager.get_mailbox_statistics()

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
