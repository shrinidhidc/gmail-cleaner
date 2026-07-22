"""
===========================================================================
MailCleaner

Module:
    Application

Purpose:
    Production application entrypoint.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from time import perf_counter
from typing import Final

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

import config
from analysis_engine import AnalysisEngine
from console import console
from database import DatabaseManager
from gmail_service import GmailService
from logger import get_logger, setup_logger
from models import AnalysisStatistics, GmailProfile
from rule_engine import RuleEngine
from statistics_engine import StatisticsEngine
from sync_engine import SyncEngine

EXIT_SUCCESS: Final[int] = 0
EXIT_CONFIGURATION_ERROR: Final[int] = 1
EXIT_AUTHENTICATION_ERROR: Final[int] = 2
EXIT_DATABASE_ERROR: Final[int] = 3
EXIT_GMAIL_ERROR: Final[int] = 4
EXIT_UNEXPECTED_ERROR: Final[int] = 99

logger = get_logger(__name__)


@dataclass(slots=True)
class Application:
    """
    Coordinates MailCleaner startup services.
    """

    database: DatabaseManager
    gmail: GmailService

    def run(self) -> int:
        """
        Run the application.

        Returns
        -------
        int
            Process exit code.
        """

        console.title(
            f"{config.APPLICATION_NAME} v{config.APPLICATION_VERSION}"
        )

        if not self._initialize_database():
            return EXIT_DATABASE_ERROR

        gmail_status = self._connect_gmail()

        if gmail_status != EXIT_SUCCESS:
            return gmail_status

        profile = self._load_gmail_profile()

        if profile is None:
            return EXIT_GMAIL_ERROR

        self._display_profile(profile)

        if config.ENABLE_SYNC:
            sync_engine = SyncEngine(
                gmail_service=self.gmail,
                database_manager=self.database,
            )
            sync_engine.sync()
        else:
            console.info("Synchronization skipped (ENABLE_SYNC=False).")
            logger.info("Synchronization skipped because ENABLE_SYNC=False.")

        self._run_analysis()

        console.success("Application started successfully.")
        logger.info("Application startup completed successfully.")

        return EXIT_SUCCESS

    def _initialize_database(self) -> bool:
        """
        Initialize local persistence.
        """

        try:
            console.info("Initializing database...")

            self.database.initialize()

            console.success("Database initialized.")
            return True

        except Exception as ex:
            logger.exception("Database initialization failed.")
            console.error(f"Database initialization failed: {ex}")
            return False

    def _connect_gmail(self) -> int:
        """
        Authenticate and verify Gmail connectivity.
        """

        try:
            console.info("Connecting to Gmail...")

            self.gmail.connect()

            if not self.gmail.verify_connection():
                console.error("Gmail connection verification failed.")
                logger.error("Gmail connection verification failed.")
                return EXIT_GMAIL_ERROR

            console.success("Gmail connection verified.")
            return EXIT_SUCCESS

        except FileNotFoundError as ex:
            logger.exception("Gmail credentials file is missing.")
            console.error(str(ex))
            return EXIT_CONFIGURATION_ERROR

        except GoogleAuthError as ex:
            logger.exception("Gmail authentication failed.")
            console.error(f"Gmail authentication failed: {ex}")
            return EXIT_AUTHENTICATION_ERROR

        except HttpError as ex:
            logger.exception("Gmail API error during connection.")
            console.error(f"Gmail API error during connection: {ex}")
            return EXIT_GMAIL_ERROR

        except Exception as ex:
            logger.exception("Gmail connection failed.")
            console.error(f"Gmail connection failed: {ex}")
            return EXIT_AUTHENTICATION_ERROR

    def _load_gmail_profile(self) -> GmailProfile | None:
        """
        Retrieve the authenticated Gmail profile.
        """

        try:
            return self.gmail.get_profile()

        except HttpError as ex:
            logger.exception("Gmail API error while retrieving profile.")
            console.error(f"Gmail API error while retrieving profile: {ex}")
            return None

        except Exception as ex:
            logger.exception("Failed to retrieve Gmail profile.")
            console.error(f"Failed to retrieve Gmail profile: {ex}")
            return None

    @staticmethod
    def _display_profile(profile: GmailProfile) -> None:
        """
        Display authenticated Gmail profile details.
        """

        print()
        print(f"Connected to : {profile.email_address}")
        print(f"Messages     : {profile.messages_total}")
        print(f"Threads      : {profile.threads_total}")
        print(f"History ID   : {profile.history_id}")
        print()

    def _run_analysis(self) -> None:
        """
        Run deterministic email analysis when enabled.
        """

        if not config.ENABLE_ANALYSIS:
            logger.info("Email analysis is disabled.")
            return

        try:
            console.info("Starting email analysis...")
            logger.info("Starting email analysis.")

            analysis_limit = config.ANALYSIS_LIMIT

            if analysis_limit is None:
                logger.info("Analysis limit: None (all pending emails)")
                analysis_limit = self.database.get_total_email_count()
            else:
                logger.info("Analysis limit: %s", analysis_limit)

            started_at = perf_counter()
            analysis_engine = AnalysisEngine(
                database_manager=self.database,
                rule_engine=RuleEngine(),
            )
            statistics = analysis_engine.analyze_pending_emails(
                limit=analysis_limit
            )
            elapsed_seconds = perf_counter() - started_at

            self._display_analysis_summary(statistics)
            self._display_mailbox_statistics()
            logger.info(
                "Email analysis completed. elapsed_seconds=%.3f "
                "total_analyzed=%s failures=%s",
                elapsed_seconds,
                statistics.analyzed,
                statistics.failed,
            )

        except Exception as ex:
            logger.exception("Email analysis failed.")
            console.error(f"Email analysis failed: {ex}")

    @staticmethod
    def _display_analysis_summary(
        statistics: AnalysisStatistics,
    ) -> None:
        """
        Display email analysis summary information.
        """

        if statistics.total_selected == 0:
            console.info("No unanalyzed emails found.")
            return

        print()
        console.title("EMAIL ANALYSIS SUMMARY")
        print(f"Emails Selected : {statistics.total_selected}")
        print(f"Analyzed        : {statistics.analyzed}")
        print(f"Classified      : {statistics.classified}")
        print(f"Unknown         : {statistics.unknown}")
        print(f"Failed          : {statistics.failed}")
        console.separator()

    def _display_mailbox_statistics(self) -> None:
        """
        Display current mailbox statistics.
        """

        try:
            statistics_engine = StatisticsEngine(self.database)
            mailbox_statistics = statistics_engine.get_mailbox_statistics()
            category_statistics = statistics_engine.get_category_statistics()
            sender_domain_statistics = (
                statistics_engine.get_sender_domain_statistics()
            )
            unknown_sender_domains = (
                statistics_engine.get_unknown_sender_domains()
            )

            print()
            console.title("MAILBOX STATISTICS")
            print(f"Total Emails          : {mailbox_statistics.total_emails}")
            print(f"Email Content         : {mailbox_statistics.total_content}")
            print(f"Analysis Records      : {mailbox_statistics.total_analysis}")
            print(f"Classified            : {mailbox_statistics.classified}")
            print(f"Unknown               : {mailbox_statistics.unknown}")
            print(f"Failed Analysis       : {mailbox_statistics.failed_analysis}")
            print("-" * 60)
            print("TOP CATEGORIES")

            for category in category_statistics:
                print(f"{category.category:<20} {category.count}")

            print("-" * 60)
            print("TOP SENDER DOMAINS")

            for sender_domain in sender_domain_statistics:
                print(f"{sender_domain.sender_domain:<20} {sender_domain.count}")

            print("-" * 60)
            print("TOP UNKNOWN DOMAINS")

            for sender_domain in unknown_sender_domains:
                print(f"{sender_domain.sender_domain:<20} {sender_domain.count}")

            console.separator()

        except Exception as ex:
            logger.exception("Failed to display mailbox statistics.")
            console.error(f"Mailbox statistics failed: {ex}")


def validate_startup() -> bool:
    """
    Validate startup configuration.
    """

    try:
        config.validate_configuration()
        return True

    except FileNotFoundError as ex:
        logger.exception("Configuration validation failed.")
        console.error(str(ex))
        return False

    except Exception as ex:
        logger.exception("Unexpected configuration validation error.")
        console.error(f"Configuration validation failed: {ex}")
        return False


def build_application() -> Application:
    """
    Build the application coordinator.
    """

    return Application(
        database=DatabaseManager(),
        gmail=GmailService(),
    )


def main() -> int:
    """
    Application process entrypoint.
    """

    setup_logger()
    logger.info("Starting MailCleaner application.")

    try:
        if not validate_startup():
            return EXIT_CONFIGURATION_ERROR

        application = build_application()

        return application.run()

    except KeyboardInterrupt:
        logger.warning("Application interrupted by user.")
        console.warning("Application interrupted by user.")
        return EXIT_SUCCESS

    except FileNotFoundError as ex:
        logger.exception("Required startup resource is missing.")
        console.error(str(ex))
        return EXIT_CONFIGURATION_ERROR

    except PermissionError as ex:
        logger.exception("Permission error during startup.")
        console.error(f"Permission error: {ex}")
        return EXIT_CONFIGURATION_ERROR

    except GoogleAuthError as ex:
        logger.exception("Unhandled Gmail authentication error.")
        console.error(f"Gmail authentication error: {ex}")
        return EXIT_AUTHENTICATION_ERROR

    except HttpError as ex:
        logger.exception("Unhandled Gmail API error.")
        console.error(f"Gmail API error: {ex}")
        return EXIT_GMAIL_ERROR

    except Exception as ex:
        logger.exception("Unhandled application error.")
        console.error(f"Unexpected application error: {ex}")
        return EXIT_UNEXPECTED_ERROR

    finally:
        logger.info("MailCleaner application stopped.")


if __name__ == "__main__":
    sys.exit(main())
