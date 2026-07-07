"""
===========================================================================
MailCleaner

Module:
    Sync Engine

Purpose:
    Coordinates Gmail metadata synchronization.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any, Callable, Final, Iterable, Optional

import config
from database import DatabaseManager
from gmail_service import GmailService
from logger import get_logger
from models import SyncStatistics

try:
    from googleapiclient.errors import HttpError
except ImportError:  # pragma: no cover - dependency is required at runtime.
    HttpError = None  # type: ignore[assignment]

logger = get_logger(__name__)

ProgressCallback = Callable[[SyncStatistics], None]

USER_ID: Final[str] = "me"
SYNC_STATUS_SYNCED: Final[str] = "synced"
SYNC_STATE_LAST_HISTORY_ID: Final[str] = "last_history_id"
SYNC_STATE_LAST_SYNC_STARTED_AT: Final[str] = "last_sync_started_at"
SYNC_STATE_LAST_SYNC_COMPLETED_AT: Final[str] = "last_sync_completed_at"
SYNC_STATE_LAST_SYNC_MODE: Final[str] = "last_sync_mode"

RETRYABLE_HTTP_STATUSES: Final[set[int]] = {
    429,
    500,
    502,
    503,
    504,
}


@dataclass(slots=True)
class GmailMessageMetadata:
    """
    Normalized Gmail message metadata.
    """

    gmail_id: str
    thread_id: Optional[str]
    sender: Optional[str]
    recipient: Optional[str]
    subject: Optional[str]
    received_at: Optional[str]
    labels: str
    snippet: Optional[str]
    history_id: Optional[str]
    internal_date: Optional[int]
    size_estimate: Optional[int]
    category: Optional[str]
    sync_status: str
    last_updated: str


class SyncEngine:
    """
    Coordinates Gmail synchronization and local metadata persistence.
    """

    def __init__(
        self,
        gmail_service: GmailService | None = None,
        database_manager: DatabaseManager | None = None,
        progress_callback: ProgressCallback | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.gmail_service = gmail_service or GmailService()
        self.database_manager = database_manager or DatabaseManager()
        self.progress_callback = progress_callback
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def sync(
        self,
        max_messages: int | None = None,
        query: str | None = None,
        page_size: int | None = None,
    ) -> SyncStatistics:
        """
        Run a Gmail metadata synchronization.

        Parameters
        ----------
        max_messages : int | None
            Optional maximum number of messages to synchronize.
        query : str | None
            Optional Gmail search query.
        page_size : int | None
            Optional Gmail API page size.

        Returns
        -------
        SyncStatistics
            Synchronization counters.
        """

        started_at = _utc_now()
        statistics = SyncStatistics()

        logger.info("Starting Gmail metadata synchronization.")
        self._report_progress(statistics)

        self.database_manager.initialize()
        self._connect_gmail()

        with self.database_manager.connect() as connection:
            self._set_sync_state(
                connection,
                SYNC_STATE_LAST_SYNC_STARTED_AT,
                started_at,
            )
            self._set_sync_state(
                connection,
                SYNC_STATE_LAST_SYNC_MODE,
                "full",
            )

            for message_id in self._iter_message_ids(
                max_messages=max_messages,
                query=query,
                page_size=page_size,
            ):
                self._sync_single_message(
                    connection=connection,
                    message_id=message_id,
                    statistics=statistics,
                )

            completed_at = _utc_now()
            self._set_sync_state(
                connection,
                SYNC_STATE_LAST_SYNC_COMPLETED_AT,
                completed_at,
            )

            connection.commit()

        logger.info(
            "Gmail metadata synchronization completed. "
            "processed=%s inserted=%s updated=%s skipped=%s failed=%s",
            statistics.processed,
            statistics.inserted,
            statistics.updated,
            statistics.skipped,
            statistics.failed,
        )

        self._report_progress(statistics)

        return statistics

    def sync_incremental(self) -> SyncStatistics:
        """
        Placeholder entrypoint for future Gmail history-based sync.

        The current schema records the last Gmail history ID during full syncs.
        A future milestone can use that value with the Gmail history API without
        changing callers of this method.
        """

        logger.info(
            "Incremental synchronization is not implemented yet; "
            "running full metadata synchronization."
        )

        return self.sync()

    def _connect_gmail(self) -> None:
        """
        Connect the Gmail service if it has not already been initialized.
        """

        try:
            self.gmail_service.service
            logger.info("Using existing Gmail service connection.")

        except RuntimeError:
            logger.info("Connecting Gmail service for synchronization.")
            self.gmail_service.connect()

    def _iter_message_ids(
        self,
        max_messages: int | None,
        query: str | None,
        page_size: int | None,
    ) -> Iterable[str]:
        """
        Yield Gmail message IDs page by page.
        """

        total_yielded = 0
        next_page_token: str | None = None
        resolved_page_size = page_size or config.PAGE_SIZE

        logger.info(
            "Retrieving Gmail message IDs. page_size=%s max_messages=%s",
            resolved_page_size,
            max_messages,
        )

        while True:
            remaining = None

            if max_messages is not None:
                remaining = max_messages - total_yielded

                if remaining <= 0:
                    break

            request_size = resolved_page_size

            if remaining is not None:
                request_size = min(resolved_page_size, remaining)

            request_parameters: dict[str, Any] = {
                "userId": USER_ID,
                "maxResults": request_size,
            }

            if next_page_token:
                request_parameters["pageToken"] = next_page_token

            if query:
                request_parameters["q"] = query

            response = self._execute_with_retries(
                "list_messages",
                self.gmail_service.service
                .users()
                .messages()
                .list(**request_parameters)
                .execute,
            )

            messages = response.get("messages", [])
            logger.info("Retrieved %s Gmail message IDs.", len(messages))

            for message in messages:
                message_id = message.get("id")

                if not message_id:
                    logger.warning("Skipping Gmail message without an ID.")
                    continue

                total_yielded += 1
                yield str(message_id)

            next_page_token = response.get("nextPageToken")

            if not next_page_token:
                break

        logger.info("Finished retrieving Gmail message IDs.")

    def _sync_single_message(
        self,
        connection: sqlite3.Connection,
        message_id: str,
        statistics: SyncStatistics,
    ) -> None:
        """
        Retrieve and persist one Gmail message.
        """

        try:
            message = self._get_message(message_id)
            metadata = self._build_metadata(message)

            self.database_manager.save_email_metadata(
                {
                    "gmail_id": metadata.gmail_id,
                    "thread_id": metadata.thread_id,
                    "history_id": metadata.history_id,
                    "internal_date": metadata.internal_date,
                    "label_ids": metadata.labels,
                    "sender": metadata.sender,
                    "recipient": metadata.recipient,
                    "subject": metadata.subject,
                    "date_header": metadata.received_at,
                    "snippet": metadata.snippet,
                    "size_estimate": metadata.size_estimate,
                    "is_read": 0,
                    "is_starred": 0,
                    "is_important": 0,
                    "last_synced": _utc_now(),
                }
            )

            was_inserted = self._upsert_message(connection, metadata)

            statistics.processed += 1

            if was_inserted:
                statistics.inserted += 1
            else:
                statistics.updated += 1

            if metadata.history_id:
                self._set_sync_state(
                    connection,
                    SYNC_STATE_LAST_HISTORY_ID,
                    metadata.history_id,
                )

            connection.commit()
            self._report_progress(statistics)

        except Exception as ex:
            statistics.failed += 1
            connection.rollback()

            logger.exception(
                "Failed to synchronize Gmail message. gmail_id=%s error=%s",
                message_id,
                ex,
            )

            self._report_progress(statistics)

    def _get_message(self, message_id: str) -> dict[str, Any]:
        """
        Retrieve a Gmail message in metadata format.
        """

        logger.debug("Retrieving Gmail message metadata. gmail_id=%s", message_id)

        return self._execute_with_retries(
            "get_message",
            self.gmail_service.service
            .users()
            .messages()
            .get(
                userId=USER_ID,
                id=message_id,
                format="metadata",
                metadataHeaders=[
                    "From",
                    "To",
                    "Subject",
                    "Date",
                ],
            )
            .execute,
        )

    def _build_metadata(
        self,
        message: dict[str, Any],
    ) -> GmailMessageMetadata:
        """
        Normalize a Gmail API message payload for persistence.
        """

        payload = message.get("payload", {})
        headers = _headers_to_dict(payload.get("headers", []))
        labels = message.get("labelIds", [])
        internal_date = _to_optional_int(message.get("internalDate"))
        received_at = _format_received_at(
            header_date=headers.get("Date"),
            internal_date=internal_date,
        )

        return GmailMessageMetadata(
            gmail_id=str(message["id"]),
            thread_id=_to_optional_str(message.get("threadId")),
            sender=_extract_email(headers.get("From")),
            recipient=_extract_email(headers.get("To")),
            subject=_to_optional_str(headers.get("Subject")),
            received_at=received_at,
            labels=json.dumps(labels),
            snippet=_to_optional_str(message.get("snippet")),
            history_id=_to_optional_str(message.get("historyId")),
            internal_date=internal_date,
            size_estimate=_to_optional_int(message.get("sizeEstimate")),
            category=_extract_category(labels),
            sync_status=SYNC_STATUS_SYNCED,
            last_updated=_utc_now(),
        )

    def _upsert_message(
        self,
        connection: sqlite3.Connection,
        metadata: GmailMessageMetadata,
    ) -> bool:
        """
        Insert or update a message row.

        Returns
        -------
        bool
            True when a row was inserted, False when an existing row was
            updated.
        """

        exists = self._message_exists(connection, metadata.gmail_id)

        connection.execute(
            """
            INSERT INTO messages (
                gmail_id,
                thread_id,
                sender,
                recipient,
                subject,
                received_at,
                labels,
                snippet,
                history_id,
                internal_date,
                size_estimate,
                category,
                sync_status,
                last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gmail_id) DO UPDATE SET
                thread_id = excluded.thread_id,
                sender = excluded.sender,
                recipient = excluded.recipient,
                subject = excluded.subject,
                received_at = excluded.received_at,
                labels = excluded.labels,
                snippet = excluded.snippet,
                history_id = excluded.history_id,
                internal_date = excluded.internal_date,
                size_estimate = excluded.size_estimate,
                category = excluded.category,
                sync_status = excluded.sync_status,
                last_updated = excluded.last_updated
            """,
            (
                metadata.gmail_id,
                metadata.thread_id,
                metadata.sender,
                metadata.recipient,
                metadata.subject,
                metadata.received_at,
                metadata.labels,
                metadata.snippet,
                metadata.history_id,
                metadata.internal_date,
                metadata.size_estimate,
                metadata.category,
                metadata.sync_status,
                metadata.last_updated,
            ),
        )

        return not exists

    @staticmethod
    def _message_exists(
        connection: sqlite3.Connection,
        gmail_id: str,
    ) -> bool:
        """
        Return whether a Gmail message already exists locally.
        """

        cursor = connection.execute(
            """
            SELECT 1
            FROM messages
            WHERE gmail_id = ?
            LIMIT 1
            """,
            (gmail_id,),
        )

        return cursor.fetchone() is not None

    @staticmethod
    def _set_sync_state(
        connection: sqlite3.Connection,
        key: str,
        value: str,
    ) -> None:
        """
        Persist a sync state value.
        """

        connection.execute(
            """
            INSERT INTO sync_state (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value
            """,
            (key, value),
        )

    def _execute_with_retries(
        self,
        operation_name: str,
        operation: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute a Gmail API operation with retry handling.
        """

        attempt = 1

        while True:
            try:
                return operation()

            except Exception as ex:
                if not self._should_retry(ex, attempt):
                    logger.exception(
                        "Gmail API operation failed. operation=%s attempt=%s",
                        operation_name,
                        attempt,
                    )
                    raise

                delay = self.retry_delay_seconds * (2 ** (attempt - 1))

                logger.warning(
                    "Retrying Gmail API operation. operation=%s "
                    "attempt=%s delay_seconds=%s error=%s",
                    operation_name,
                    attempt,
                    delay,
                    ex,
                )

                time.sleep(delay)
                attempt += 1

    def _should_retry(self, ex: Exception, attempt: int) -> bool:
        """
        Return whether an exception should be retried.
        """

        if attempt >= self.max_retries:
            return False

        if HttpError is not None and isinstance(ex, HttpError):
            status = getattr(ex.resp, "status", None)
            return status in RETRYABLE_HTTP_STATUSES

        return isinstance(ex, (ConnectionError, TimeoutError))

    def _report_progress(self, statistics: SyncStatistics) -> None:
        """
        Report synchronization progress.
        """

        logger.info(
            "Sync progress. processed=%s inserted=%s updated=%s "
            "skipped=%s failed=%s",
            statistics.processed,
            statistics.inserted,
            statistics.updated,
            statistics.skipped,
            statistics.failed,
        )

        if self.progress_callback is not None:
            self.progress_callback(statistics)


def fetch_message_ids(service: Any, max_results: int = 100) -> list[dict[str, Any]]:
    """
    Backward-compatible helper for older entrypoints.
    """

    logger.info("Fetching Gmail message IDs. max_results=%s", max_results)

    response = (
        service
        .users()
        .messages()
        .list(
            userId=USER_ID,
            maxResults=max_results,
        )
        .execute()
    )

    messages = response.get("messages", [])

    logger.info("Fetched %s Gmail message IDs.", len(messages))

    return messages


def _headers_to_dict(headers: list[dict[str, Any]]) -> dict[str, str]:
    """
    Convert Gmail header objects to a case-sensitive dictionary.
    """

    normalized: dict[str, str] = {}

    for header in headers:
        name = header.get("name")
        value = header.get("value")

        if name and value:
            normalized[str(name)] = str(value)

    return normalized


def _extract_email(value: str | None) -> str | None:
    """
    Extract an email address from a header value.
    """

    if not value:
        return None

    _, email_address = parseaddr(value)

    return email_address or value


def _extract_category(labels: Iterable[str]) -> str | None:
    """
    Extract a Gmail category label, when present.
    """

    for label in labels:
        if label.startswith("CATEGORY_"):
            return label.removeprefix("CATEGORY_").lower()

    return None


def _format_received_at(
    header_date: str | None,
    internal_date: int | None,
) -> str | None:
    """
    Return a stable timestamp string for message receipt time.
    """

    if header_date:
        return header_date

    if internal_date is None:
        return None

    return datetime.fromtimestamp(
        internal_date / 1000,
        tz=UTC,
    ).isoformat()


def _to_optional_int(value: Any) -> int | None:
    """
    Convert a value to int when possible.
    """

    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def _to_optional_str(value: Any) -> str | None:
    """
    Convert a value to str when present.
    """

    if value is None:
        return None

    return str(value)


def _utc_now() -> str:
    """
    Return the current UTC timestamp.
    """

    return datetime.now(UTC).isoformat()
