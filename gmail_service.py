"""
===========================================================================
MailCleaner

Module:
    Gmail Service

Purpose:
    Handles Gmail API communication.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth import authenticate
from logger import get_logger
from models import GmailProfile

logger = get_logger(__name__)


class GmailService:
    """
    Gmail API wrapper.
    """

    def __init__(self) -> None:
        self._service = None

    @property
    def service(self):
        """
        Return the Gmail service object.
        """
        if self._service is None:
            raise RuntimeError("Gmail service has not been initialized.")

        return self._service

    def connect(self) -> None:
        """
        Authenticate and build the Gmail API service.
        """
        logger.info("Connecting to Gmail...")

        credentials = authenticate()

        self._service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        logger.info("Gmail connection established.")

    def verify_connection(self) -> bool:
        """
        Verify Gmail connectivity.

        Returns
        -------
        bool
        """

        try:
            self.service.users().getProfile(userId="me").execute()
            return True

        except HttpError as ex:
            logger.exception(ex)
            return False

    def get_profile(self) -> GmailProfile:
        """
        Retrieve Gmail profile information.

        Returns
        -------
        GmailProfile
        """

        logger.info("Retrieving Gmail profile...")

        profile = (
            self.service
            .users()
            .getProfile(userId="me")
            .execute()
        )

        logger.info("Profile retrieved successfully.")

        return GmailProfile(
            email_address=profile["emailAddress"],
            messages_total=int(profile["messagesTotal"]),
            threads_total=int(profile["threadsTotal"]),
            history_id=str(profile["historyId"]),
        )