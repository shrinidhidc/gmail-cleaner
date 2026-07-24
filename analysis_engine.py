"""
MailCleaner Analysis Engine

Coordinates deterministic email analysis and persistence.
"""

from __future__ import annotations

from database import DatabaseManager
from logger import get_logger
from models import AnalysisStatistics
from rule_engine import RuleEngine
from sender_utils import parse_sender  # <-- Added import

logger = get_logger(__name__)


class AnalysisEngine:
    """
    Coordinate pending email analysis using injected dependencies.
    """

    def __init__(
        self,
        database_manager: DatabaseManager,
        rule_engine: RuleEngine,
    ) -> None:
        self.database_manager = database_manager
        self.rule_engine = rule_engine

    def analyze_pending_emails(
        self,
        limit: int = 100,
    ) -> AnalysisStatistics:
        """
        Analyze and persist results for emails without saved analysis.
        """

        logger.info("Starting email analysis. limit=%s", limit)

        pending_emails = self.database_manager.get_unanalyzed_emails(limit)
        statistics = AnalysisStatistics(total_selected=len(pending_emails))

        for metadata in pending_emails:
            try:
                logger.info("Analyzing email. gmail_id=%s", metadata.gmail_id)

                content = self.database_manager.get_email_content(
                    metadata.gmail_id
                )

                # Parse sender and extract domain
                sender = metadata.sender
                parsed_sender = parse_sender(sender)
                domain = parsed_sender.domain

                analysis = self.rule_engine.analyze(metadata, content)
                analysis.sender_domain = domain

                logger.info(
                    "Classification completed. gmail_id=%s category=%s",
                    metadata.gmail_id,
                    analysis.category,
                )
                logger.info(
                    "Saving analysis. gmail_id=%s",
                    metadata.gmail_id,
                )

                self.database_manager.save_email_analysis(analysis)
                statistics.analyzed += 1

                if analysis.category == "Unknown":
                    statistics.unknown += 1
                else:
                    statistics.classified += 1

            except Exception as ex:
                statistics.failed += 1
                logger.exception(
                    "Failed to analyze email. gmail_id=%s error=%s",
                    metadata.gmail_id,
                    ex,
                )

        logger.info(
            "Email analysis completed. total_selected=%s analyzed=%s "
            "classified=%s unknown=%s failed=%s",
            statistics.total_selected,
            statistics.analyzed,
            statistics.classified,
            statistics.unknown,
            statistics.failed,
        )

        return statistics
