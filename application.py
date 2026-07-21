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
from typing import Final

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

import config
from console import console
from database import DatabaseManager
from gmail_service import GmailService
from logger import get_logger, setup_logger
from models import GmailProfile
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

        sync_engine = SyncEngine(
            gmail_service=self.gmail,
            database_manager=self.database,
        )
        sync_engine.sync()

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
