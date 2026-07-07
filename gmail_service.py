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

from datetime import datetime, timezone
from typing import Any

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

    def get_message_ids(self, max_results: int = 500) -> list[str]:
        """
        Retrieve Gmail message IDs using paginated list requests.

        Parameters
        ----------
        max_results : int
            Maximum number of message IDs to return.

        Returns
        -------
        list[str]
        """

        if max_results <= 0:
            return []

        logger.info("Retrieving Gmail message IDs...")

        message_ids: list[str] = []
        page_token: str | None = None
        remaining = max_results

        try:
            while remaining > 0:
                request_params: dict[str, Any] = {
                    "userId": "me",
                    "maxResults": min(500, remaining),
                }

                if page_token:
                    request_params["pageToken"] = page_token

                response = (
                    self.service
                    .users()
                    .messages()
                    .list(**request_params)
                    .execute()
                )

                for message in response.get("messages", []):
                    message_ids.append(message["id"])
                    remaining -= 1
                    if remaining <= 0:
                        break

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            logger.info("Retrieved %s Gmail message IDs.", len(message_ids))
            return message_ids

        except HttpError as ex:
            logger.exception("Failed to retrieve Gmail message IDs: %s", ex)
            raise

    def get_message_metadata(self, message_id: str) -> dict[str, Any]:
        """
        Retrieve message metadata without downloading bodies or attachments.

        Parameters
        ----------
        message_id : str
            Gmail message ID.

        Returns
        -------
        dict[str, Any]
        """

        logger.debug("Retrieving metadata for message %s...", message_id)

        try:
            message = (
                self.service
                .users()
                .messages()
                .get(userId="me", id=message_id, format="metadata")
                .execute()
            )

            logger.debug("Metadata retrieved successfully for message %s.", message_id)
            return self.build_email_metadata(message)

        except HttpError as ex:
            logger.exception("Failed to retrieve metadata for message %s: %s", message_id, ex)
            raise

    def parse_headers(self, headers: list[dict[str, Any]] | None) -> dict[str, str]:
        """
        Extract selected message headers.

        Parameters
        ----------
        headers : list[dict[str, Any]] | None
            Header entries from the Gmail API payload.

        Returns
        -------
        dict[str, str]
        """

        parsed_headers: dict[str, str] = {}

        if not headers:
            return parsed_headers

        header_lookup: dict[str, str] = {}

        for header in headers:
            name = str(header.get("name", "")).strip().lower()
            value = str(header.get("value", ""))

            if name:
                header_lookup[name] = value

        required_headers = {
            "subject": "Subject",
            "from": "From",
            "to": "To",
            "cc": "Cc",
            "bcc": "Bcc",
            "date": "Date",
            "message-id": "Message-ID",
        }

        for normalized_name, display_name in required_headers.items():
            parsed_headers[display_name] = header_lookup.get(normalized_name, "")

        return parsed_headers

    def build_email_metadata(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Build a metadata dictionary for a Gmail message.

        Parameters
        ----------
        message : dict[str, Any]
            Gmail message payload from the API.

        Returns
        -------
        dict[str, Any]
        """

        if not isinstance(message, dict):
            logger.warning("Invalid Gmail message payload received.")
            return {}

        payload = message.get("payload", {})
        headers = self.parse_headers(payload.get("headers", []))

        internal_date_value = message.get("internalDate")
        internal_date = None

        if internal_date_value is not None:
            try:
                internal_date = datetime.fromtimestamp(
                    int(str(internal_date_value)) / 1000,
                    tz=timezone.utc,
                )
            except (TypeError, ValueError, OverflowError):
                logger.warning("Invalid internalDate value: %s", internal_date_value)

        return {
            "message_id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "label_ids": message.get("labelIds", []),
            "snippet": message.get("snippet", ""),
            "internal_date": internal_date,
            "size_estimate": message.get("sizeEstimate", ""),
            "history_id": message.get("historyId", ""),
            "subject": headers.get("Subject", ""),
            "sender": headers.get("From", ""),
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "bcc": headers.get("Bcc", ""),
            "date": headers.get("Date", ""),
            "message_id_header": headers.get("Message-ID", ""),
        }