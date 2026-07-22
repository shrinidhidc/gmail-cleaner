"""
MailCleaner Database Module

Handles SQLite database creation, migration, and connectivity.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, TypeVar

import config
from logger import get_logger
from models import (
    CategoryStatistics,
    EmailAnalysis,
    EmailContent,
    EmailMetadata,
    MailboxStatistics,
    SenderDomainStatistics,
)

logger = get_logger(__name__)

T = TypeVar("T")

EMAIL_COLUMNS: tuple[str, ...] = (
    "gmail_id",
    "thread_id",
    "history_id",
    "internal_date",
    "label_ids",
    "sender",
    "recipient",
    "subject",
    "date_header",
    "snippet",
    "size_estimate",
    "is_read",
    "is_starred",
    "is_important",
    "last_synced",
)

EMAIL_UPDATE_COLUMNS: tuple[str, ...] = (
    "thread_id",
    "history_id",
    "internal_date",
    "label_ids",
    "sender",
    "recipient",
    "subject",
    "date_header",
    "snippet",
    "size_estimate",
    "is_read",
    "is_starred",
    "is_important",
    "last_synced",
)

EMAIL_COLUMN_DEFINITIONS: dict[str, str] = {
    "gmail_id": "TEXT",
    "thread_id": "TEXT",
    "history_id": "TEXT",
    "internal_date": "INTEGER",
    "label_ids": "TEXT",
    "sender": "TEXT",
    "recipient": "TEXT",
    "subject": "TEXT",
    "date_header": "TEXT",
    "snippet": "TEXT",
    "size_estimate": "INTEGER",
    "is_read": "INTEGER DEFAULT 0",
    "is_starred": "INTEGER DEFAULT 0",
    "is_important": "INTEGER DEFAULT 0",
    "last_synced": "TIMESTAMP",
}

EMAIL_CONTENT_COLUMNS: tuple[str, ...] = (
    "id",
    "gmail_id",
    "plain_text",
    "html_body",
    "mime_type",
    "content_size",
    "extracted_at",
)

EMAIL_CONTENT_COLUMN_DEFINITIONS: dict[str, str] = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "gmail_id": "TEXT UNIQUE NOT NULL",
    "plain_text": "TEXT",
    "html_body": "TEXT",
    "mime_type": "TEXT",
    "content_size": "INTEGER",
    "extracted_at": "TIMESTAMP",
}

EMAIL_ANALYSIS_COLUMNS: tuple[str, ...] = (
    "gmail_id",
    "sender_domain",
    "category",
    "importance",
    "has_unsubscribe",
    "has_attachment",
    "has_html",
    "confidence",
    "analyzed_by",
    "analyzed_at",
)

EMAIL_ANALYSIS_UPDATE_COLUMNS: tuple[str, ...] = (
    "sender_domain",
    "category",
    "importance",
    "has_unsubscribe",
    "has_attachment",
    "has_html",
    "confidence",
    "analyzed_by",
    "analyzed_at",
)

EMAIL_ANALYSIS_COLUMN_DEFINITIONS: dict[str, str] = {
    "gmail_id": "TEXT PRIMARY KEY",
    "sender_domain": "TEXT",
    "category": "TEXT",
    "importance": "TEXT",
    "has_unsubscribe": "INTEGER DEFAULT 0",
    "has_attachment": "INTEGER DEFAULT 0",
    "has_html": "INTEGER DEFAULT 0",
    "confidence": "REAL",
    "analyzed_by": "TEXT",
    "analyzed_at": "TIMESTAMP",
}

class DatabaseManager:
    """
    SQLite database manager.
    """

    def __init__(self) -> None:
        self.database_path: Path = config.DATABASE_PATH
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Open a SQLite connection.
        """

        try:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        except sqlite3.Error as ex:
            logger.exception("Failed to open database connection.")
            raise RuntimeError("Failed to open database connection.") from ex

    def initialize(self) -> None:
        """
        Create or migrate database schema if it does not exist.
        """

        logger.info("Initializing database...")

        try:
            with self.connect() as connection:
                cursor = connection.cursor()

                self._create_messages_table(cursor)
                self._create_senders_table(cursor)
                self._create_sync_state_table(cursor)
                self._create_emails_table(cursor)
                self._migrate_emails_table(connection)
                self._create_emails_indexes(cursor)

                # Migrate email_content table
                self._create_email_content_table(cursor)
                self._migrate_email_content_table(connection)

                self._create_email_analysis_table(cursor)
                self._migrate_email_analysis_table(connection)
                self._create_email_analysis_indexes(cursor)

                connection.commit()

        except sqlite3.Error as ex:
            logger.exception("Database initialization failed.")
            raise RuntimeError("Database initialization failed.") from ex

        logger.info("Database initialized successfully.")

    def save_email_metadata(self, email: dict[str, Any]) -> None:
        """
        Insert or update email metadata using the existing UPSERT helper.

        Parameters
        ----------
        email : dict[str, Any]
            Email metadata payload to persist.
        """

        if not isinstance(email, dict):
            raise TypeError("email must be a dictionary.")

        gmail_id = email.get("gmail_id")

        try:
            self.upsert_email_metadata(email)
            logger.debug("Saved email metadata. gmail_id=%s", gmail_id)

        except Exception:
            logger.exception("Failed to save email metadata. gmail_id=%s", gmail_id)
            raise

    def save_email_content(
        self,
        content: EmailContent,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """
        Insert or update extracted email content.

        Parameters
        ----------
        content : EmailContent
            Extracted Gmail message content to persist.

        Returns
        -------
        int
            Number of rows inserted or updated.
        """

        if not isinstance(content, EmailContent):
            raise TypeError("content must be an EmailContent instance.")

        if not content.gmail_id:
            raise ValueError("gmail_id is required.")

        plain_text = content.plain_text or ""
        html_body = content.html_body or ""
        content_size = (
            len(plain_text.encode("utf-8"))
            + len(html_body.encode("utf-8"))
        )
        extracted_at = _utc_now()

        query = """
            INSERT INTO email_content (
                gmail_id,
                plain_text,
                html_body,
                mime_type,
                content_size,
                extracted_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(gmail_id) DO UPDATE SET
                plain_text = excluded.plain_text,
                html_body = excluded.html_body,
                mime_type = excluded.mime_type,
                content_size = excluded.content_size,
                extracted_at = excluded.extracted_at
        """

        values = (
            content.gmail_id,
            plain_text,
            html_body,
            content.mime_type,
            content_size,
            extracted_at,
        )

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(query, values)
            row_count = (
                int(cursor.rowcount)
                if cursor.rowcount not in (None, -1)
                else 1
            )
            logger.info(
                "Saved email content. gmail_id=%s",
                content.gmail_id,
            )
            return row_count

        if connection is not None:
            return operation(connection)

        return self._execute_write(operation)

    def save_email_analysis(
        self,
        analysis: EmailAnalysis | Mapping[str, Any],
    ) -> int:
        """
        Insert or update email analysis results.

        Parameters
        ----------
        analysis : EmailAnalysis | Mapping[str, Any]
            Email analysis results to persist.

        Returns
        -------
        int
            Number of rows inserted or updated.
        """

        data = self._normalize_email_analysis_data(analysis)
        column_list = ", ".join(EMAIL_ANALYSIS_COLUMNS)
        placeholders = ", ".join("?" for _ in EMAIL_ANALYSIS_COLUMNS)
        update_assignments = ", ".join(
            f"{column} = excluded.{column}"
            for column in EMAIL_ANALYSIS_UPDATE_COLUMNS
        )
        values = tuple(data.get(column) for column in EMAIL_ANALYSIS_COLUMNS)

        query = f"""
            INSERT INTO email_analysis ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(gmail_id) DO UPDATE
            SET {update_assignments}
        """

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(query, values)
            row_count = (
                int(cursor.rowcount)
                if cursor.rowcount not in (None, -1)
                else 1
            )
            logger.info(
                "Saved email analysis. gmail_id=%s",
                data["gmail_id"],
            )
            return row_count

        return self._execute_write(operation)

    def insert_email(self, email: EmailMetadata | Mapping[str, Any]) -> int:
        """
        Insert one email metadata row.

        Parameters
        ----------
        email : EmailMetadata | Mapping[str, Any]
            Email metadata to insert.

        Returns
        -------
        int
            Inserted row ID.
        """

        data = self._normalize_email_data(email)
        placeholders = ", ".join("?" for _ in EMAIL_COLUMNS)
        column_list = ", ".join(EMAIL_COLUMNS)
        values = tuple(data.get(column) for column in EMAIL_COLUMNS)

        query = f"""
            INSERT INTO emails ({column_list})
            VALUES ({placeholders})
        """

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(query, values)
            row_id = int(cursor.lastrowid)
            logger.info("Inserted email metadata. gmail_id=%s", data["gmail_id"])
            return row_id

        return self._execute_write(operation)

    def upsert_email_metadata(
        self,
        email: EmailMetadata | Mapping[str, Any],
    ) -> int:
        """
        Insert or update one email metadata row using an UPSERT.

        Parameters
        ----------
        email : EmailMetadata | Mapping[str, Any]
            Email metadata to persist.

        Returns
        -------
        int
            Number of rows inserted or updated.
        """

        data = self._normalize_email_data(email)
        column_list = ", ".join(EMAIL_COLUMNS)
        placeholders = ", ".join("?" for _ in EMAIL_COLUMNS)
        update_assignments = ", ".join(
            f"{column} = excluded.{column}"
            for column in EMAIL_UPDATE_COLUMNS
        )
        values = tuple(data.get(column) for column in EMAIL_COLUMNS)

        query = f"""
            INSERT INTO emails ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(gmail_id) DO UPDATE
            SET {update_assignments}
        """

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(query, values)
            row_count = (
                int(cursor.rowcount)
                if cursor.rowcount not in (None, -1)
                else 1
            )
            logger.info("Upserted email metadata. gmail_id=%s", data["gmail_id"])
            return row_count

        return self._execute_write(operation)

    def upsert_email_metadata_batch(
        self,
        emails: Iterable[EmailMetadata | Mapping[str, Any]],
    ) -> int:
        """
        Insert or update multiple email metadata rows within a transaction.

        Parameters
        ----------
        emails : Iterable[EmailMetadata | Mapping[str, Any]]
            Email metadata rows to persist.

        Returns
        -------
        int
            Number of rows inserted or updated.
        """

        email_list = list(emails)

        if not email_list:
            return 0

        self.begin_transaction()

        try:
            total_rows = 0

            for email in email_list:
                total_rows += self.upsert_email_metadata(email)

            self.commit()
            logger.info("Upserted %s email metadata rows.", total_rows)
            return total_rows

        except Exception:
            self.rollback()
            raise

    def update_email(
        self,
        gmail_id: str,
        email: EmailMetadata | Mapping[str, Any],
    ) -> bool:
        """
        Update one email metadata row by Gmail ID.

        Parameters
        ----------
        gmail_id : str
            Gmail message ID.
        email : EmailMetadata | Mapping[str, Any]
            Email metadata fields to update.

        Returns
        -------
        bool
            True if a row was updated.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        data = self._normalize_partial_email_data(email)
        assignments = [
            f"{column} = ?"
            for column in EMAIL_UPDATE_COLUMNS
            if column in data
        ]

        if not assignments:
            logger.warning("No email metadata fields supplied for update.")
            return False

        values = tuple(
            data[column]
            for column in EMAIL_UPDATE_COLUMNS
            if column in data
        )
        query = f"""
            UPDATE emails
            SET {", ".join(assignments)}
            WHERE gmail_id = ?
        """

        def operation(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(query, (*values, gmail_id))
            updated = cursor.rowcount > 0

            if updated:
                logger.info("Updated email metadata. gmail_id=%s", gmail_id)
            else:
                logger.info("No email metadata row found. gmail_id=%s", gmail_id)

            return updated

        return self._execute_write(operation)

    def email_exists(self, gmail_id: str) -> bool:
        """
        Return whether an email exists by Gmail ID.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        def operation(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(
                """
                SELECT 1
                FROM emails
                WHERE gmail_id = ?
                LIMIT 1
                """,
                (gmail_id,),
            )

            return cursor.fetchone() is not None

        return self._execute_read(operation)

    def email_content_exists(
        self,
        gmail_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> bool:
        """
        Return whether extracted email content exists by Gmail ID.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        def operation(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(
                """
                SELECT 1
                FROM email_content
                WHERE gmail_id = ?
                LIMIT 1
                """,
                (gmail_id,),
            )

            return cursor.fetchone() is not None

        if connection is not None:
            return operation(connection)

        return self._execute_read(operation)

    def get_email_content(self, gmail_id: str) -> EmailContent | None:
        """
        Return extracted email content by Gmail ID.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        def operation(connection: sqlite3.Connection) -> EmailContent | None:
            cursor = connection.execute(
                """
                SELECT gmail_id, plain_text, html_body, mime_type
                FROM email_content
                WHERE gmail_id = ?
                """,
                (gmail_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return EmailContent(
                gmail_id=str(row["gmail_id"]),
                plain_text=row["plain_text"] or "",
                html_body=row["html_body"] or "",
                mime_type=row["mime_type"] or "",
            )

        return self._execute_read(operation)

    def analysis_exists(self, gmail_id: str) -> bool:
        """
        Return whether email analysis exists by Gmail ID.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        def operation(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(
                """
                SELECT 1
                FROM email_analysis
                WHERE gmail_id = ?
                LIMIT 1
                """,
                (gmail_id,),
            )

            return cursor.fetchone() is not None

        return self._execute_read(operation)

    def get_email_analysis(self, gmail_id: str) -> EmailAnalysis | None:
        """
        Return email analysis results by Gmail ID.
        """

        if not gmail_id:
            raise ValueError("gmail_id is required.")

        def operation(connection: sqlite3.Connection) -> EmailAnalysis | None:
            cursor = connection.execute(
                """
                SELECT gmail_id, sender_domain, category, importance,
                       has_unsubscribe, has_attachment, has_html,
                       confidence, analyzed_by, analyzed_at
                FROM email_analysis
                WHERE gmail_id = ?
                """,
                (gmail_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return EmailAnalysis(
                gmail_id=str(row["gmail_id"]),
                sender_domain=row["sender_domain"],
                category=row["category"],
                importance=row["importance"],
                has_unsubscribe=int(row["has_unsubscribe"]),
                has_attachment=int(row["has_attachment"]),
                has_html=int(row["has_html"]),
                confidence=row["confidence"],
                analyzed_by=row["analyzed_by"],
                analyzed_at=row["analyzed_at"],
            )

        return self._execute_read(operation)

    def get_unanalyzed_emails(self, limit: int) -> list[EmailMetadata]:
        """
        Return email metadata rows without persisted analysis results.
        """

        if limit <= 0:
            return []

        def operation(
            connection: sqlite3.Connection,
        ) -> list[EmailMetadata]:
            cursor = connection.execute(
                """
                SELECT e.gmail_id, e.thread_id, e.history_id,
                       e.internal_date, e.label_ids, e.sender,
                       e.recipient, e.subject, e.date_header,
                       e.snippet, e.size_estimate, e.is_read,
                       e.is_starred, e.is_important, e.last_synced
                FROM emails AS e
                LEFT JOIN email_analysis AS a
                    ON a.gmail_id = e.gmail_id
                WHERE a.gmail_id IS NULL
                ORDER BY e.internal_date DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [
                EmailMetadata(
                    gmail_id=str(row["gmail_id"]),
                    thread_id=row["thread_id"],
                    history_id=row["history_id"],
                    internal_date=row["internal_date"],
                    label_ids=row["label_ids"],
                    sender=row["sender"],
                    recipient=row["recipient"],
                    subject=row["subject"],
                    date_header=row["date_header"],
                    snippet=row["snippet"],
                    size_estimate=row["size_estimate"],
                    is_read=int(row["is_read"]),
                    is_starred=int(row["is_starred"]),
                    is_important=int(row["is_important"]),
                    last_synced=row["last_synced"],
                )
                for row in cursor.fetchall()
            ]

        return self._execute_read(operation)

    def get_total_email_count(self) -> int:
        """
        Return the total number of email metadata rows.
        """

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM emails
                """
            )
            row = cursor.fetchone()
            return int(row["total"])

        return self._execute_read(operation)

    def get_mailbox_statistics(self) -> MailboxStatistics:
        """
        Return aggregate mailbox statistics.
        """

        def operation(connection: sqlite3.Connection) -> MailboxStatistics:
            cursor = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM emails) AS total_emails,
                    (SELECT COUNT(*) FROM email_content) AS total_content,
                    (SELECT COUNT(*) FROM email_analysis) AS total_analysis,
                    (
                        SELECT COUNT(*)
                        FROM email_analysis
                        WHERE category IS NOT NULL
                          AND category != 'Unknown'
                    ) AS classified,
                    (
                        SELECT COUNT(*)
                        FROM email_analysis
                        WHERE category = 'Unknown'
                    ) AS unknown
                """
            )
            row = cursor.fetchone()

            return MailboxStatistics(
                total_emails=int(row["total_emails"]),
                total_content=int(row["total_content"]),
                total_analysis=int(row["total_analysis"]),
                classified=int(row["classified"]),
                unknown=int(row["unknown"]),
                failed_analysis=0,
            )

        return self._execute_read(operation)

    def get_category_statistics(self) -> list[CategoryStatistics]:
        """
        Return email analysis category counts.
        """

        def operation(
            connection: sqlite3.Connection,
        ) -> list[CategoryStatistics]:
            cursor = connection.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM email_analysis
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC, category ASC
                """
            )

            return [
                CategoryStatistics(
                    category=str(row["category"]),
                    count=int(row["count"]),
                )
                for row in cursor.fetchall()
            ]

        return self._execute_read(operation)

    def get_sender_domain_statistics(
        self,
        limit: int = 25,
    ) -> list[SenderDomainStatistics]:
        """
        Return top analyzed sender domains.
        """

        if limit <= 0:
            return []

        def operation(
            connection: sqlite3.Connection,
        ) -> list[SenderDomainStatistics]:
            cursor = connection.execute(
                """
                SELECT sender_domain, COUNT(*) AS count
                FROM email_analysis
                WHERE sender_domain IS NOT NULL
                  AND sender_domain != ''
                GROUP BY sender_domain
                ORDER BY count DESC, sender_domain ASC
                LIMIT ?
                """,
                (limit,),
            )

            return [
                SenderDomainStatistics(
                    sender_domain=str(row["sender_domain"]),
                    count=int(row["count"]),
                )
                for row in cursor.fetchall()
            ]

        return self._execute_read(operation)

    def get_unknown_sender_domain_statistics(
        self,
        limit: int = 25,
    ) -> list[SenderDomainStatistics]:
        """
        Return top sender domains with unknown analysis category.
        """

        if limit <= 0:
            return []

        def operation(
            connection: sqlite3.Connection,
        ) -> list[SenderDomainStatistics]:
            cursor = connection.execute(
                """
                SELECT sender_domain, COUNT(*) AS count
                FROM email_analysis
                WHERE category = 'Unknown'
                  AND sender_domain IS NOT NULL
                  AND sender_domain != ''
                GROUP BY sender_domain
                ORDER BY count DESC, sender_domain ASC
                LIMIT ?
                """,
                (limit,),
            )

            return [
                SenderDomainStatistics(
                    sender_domain=str(row["sender_domain"]),
                    count=int(row["count"]),
                )
                for row in cursor.fetchall()
            ]

        return self._execute_read(operation)

    def begin_transaction(self) -> sqlite3.Connection:
        """
        Begin an explicit database transaction.

        Returns
        -------
        sqlite3.Connection
            Active managed database connection.
        """

        if self._connection is None:
            self._connection = self.connect()

        try:
            if not self._connection.in_transaction:
                self._connection.execute("BEGIN")
                logger.info("Database transaction started.")

            return self._connection

        except sqlite3.Error as ex:
            logger.exception("Failed to begin database transaction.")
            raise RuntimeError("Failed to begin database transaction.") from ex

    def commit(self) -> None:
        """
        Commit the active transaction.
        """

        if self._connection is None:
            logger.warning("Commit requested with no active database connection.")
            return

        try:
            self._connection.commit()
            logger.info("Database transaction committed.")

        except sqlite3.Error as ex:
            logger.exception("Failed to commit database transaction.")
            raise RuntimeError("Failed to commit database transaction.") from ex

    def rollback(self) -> None:
        """
        Roll back the active transaction.
        """

        if self._connection is None:
            logger.warning("Rollback requested with no active database connection.")
            return

        try:
            self._connection.rollback()
            logger.info("Database transaction rolled back.")

        except sqlite3.Error as ex:
            logger.exception("Failed to roll back database transaction.")
            raise RuntimeError("Failed to roll back database transaction.") from ex

    def close(self) -> None:
        """
        Close the active managed database connection.
        """

        if self._connection is None:
            return

        try:
            self._connection.close()
            logger.info("Database connection closed.")

        except sqlite3.Error as ex:
            logger.exception("Failed to close database connection.")
            raise RuntimeError("Failed to close database connection.") from ex

        finally:
            self._connection = None

    @staticmethod
    def _create_messages_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the legacy messages table.
        """

        logger.info("Creating messages table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                gmail_id TEXT UNIQUE NOT NULL,

                thread_id TEXT,

                sender TEXT,

                recipient TEXT,

                subject TEXT,

                received_at TEXT,

                labels TEXT,

                snippet TEXT,

                history_id TEXT,

                internal_date INTEGER,

                size_estimate INTEGER,

                category TEXT,

                sync_status TEXT,

                last_updated TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_sender
            ON messages(sender)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_category
            ON messages(category)
            """
        )

    @staticmethod
    def _create_senders_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the senders table.
        """

        logger.info("Creating senders table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS senders (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                email TEXT UNIQUE NOT NULL,

                display_name TEXT,

                message_count INTEGER DEFAULT 0,

                category TEXT,

                first_seen TEXT,

                last_seen TEXT
            )
            """
        )

    @staticmethod
    def _create_sync_state_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the sync state table.
        """

        logger.info("Creating sync_state table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_state (

                key TEXT PRIMARY KEY,

                value TEXT
            )
            """
        )

    @staticmethod
    def _create_emails_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the emails metadata table.
        """

        logger.info("Creating emails table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                gmail_id TEXT UNIQUE NOT NULL,

                thread_id TEXT,

                history_id TEXT,

                internal_date INTEGER,

                label_ids TEXT,

                sender TEXT,

                recipient TEXT,

                subject TEXT,

                date_header TEXT,

                snippet TEXT,

                size_estimate INTEGER,

                is_read INTEGER DEFAULT 0,

                is_starred INTEGER DEFAULT 0,

                is_important INTEGER DEFAULT 0,

                last_synced TIMESTAMP
            )
            """
        )

    @staticmethod
    def _migrate_emails_table(connection: sqlite3.Connection) -> None:
        """
        Add missing emails table columns for existing databases.
        """

        logger.info("Checking emails table migrations.")

        cursor = connection.execute("PRAGMA table_info(emails)")
        existing_columns = {
            str(row["name"])
            for row in cursor.fetchall()
        }

        for column, definition in EMAIL_COLUMN_DEFINITIONS.items():
            if column in existing_columns:
                continue

            logger.info("Adding emails column. column=%s", column)

            connection.execute(
                f"""
                ALTER TABLE emails
                ADD COLUMN {column} {definition}
                """
            )

    @staticmethod
    def _create_emails_indexes(cursor: sqlite3.Cursor) -> None:
        """
        Create indexes used by future metadata synchronization.
        """

        logger.info("Creating emails indexes if needed.")

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_emails_gmail_id
            ON emails(gmail_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_thread_id
            ON emails(thread_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_history_id
            ON emails(history_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_internal_date
            ON emails(internal_date)
            """
        )

    @staticmethod
    def _create_email_content_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the email_content table if needed.
        """

        logger.info("Creating email_content table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_id TEXT UNIQUE NOT NULL,
                plain_text TEXT,
                html_body TEXT,
                mime_type TEXT,
                content_size INTEGER,
                extracted_at TIMESTAMP
            )
            """
        )

    @staticmethod
    def _migrate_email_content_table(connection: sqlite3.Connection) -> None:
        """
        Migrate email_content table for existing databases.
        """

        logger.info("Checking email_content table migrations.")

        cursor = connection.execute("PRAGMA table_info(email_content)")
        existing_columns = {
            str(row["name"])
            for row in cursor.fetchall()
        }

        safe_column_definitions = {
            column: definition
            for column, definition in EMAIL_CONTENT_COLUMN_DEFINITIONS.items()
            if "PRIMARY KEY" not in definition
            and "UNIQUE" not in definition
            and "NOT NULL" not in definition
        }

        for column, definition in safe_column_definitions.items():
            if column in existing_columns:
                continue

            logger.info("Adding email_content column. column=%s", column)

            connection.execute(
                f"""
                ALTER TABLE email_content
                ADD COLUMN {column} {definition}
                """
            )

    @staticmethod
    def _create_email_analysis_table(cursor: sqlite3.Cursor) -> None:
        """
        Create the email_analysis table if needed.
        """

        logger.info("Creating email_analysis table if needed.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_analysis (
                gmail_id TEXT PRIMARY KEY,
                sender_domain TEXT,
                category TEXT,
                importance TEXT,
                has_unsubscribe INTEGER DEFAULT 0,
                has_attachment INTEGER DEFAULT 0,
                has_html INTEGER DEFAULT 0,
                confidence REAL,
                analyzed_by TEXT,
                analyzed_at TIMESTAMP,
                FOREIGN KEY(gmail_id) REFERENCES emails(gmail_id)
            )
            """
        )

    @staticmethod
    def _migrate_email_analysis_table(connection: sqlite3.Connection) -> None:
        """
        Add missing email_analysis columns for existing databases.
        """

        logger.info("Checking email_analysis table migrations.")

        cursor = connection.execute("PRAGMA table_info(email_analysis)")
        existing_columns = {
            str(row["name"])
            for row in cursor.fetchall()
        }

        for column, definition in EMAIL_ANALYSIS_COLUMN_DEFINITIONS.items():
            if column in existing_columns:
                continue

            if "PRIMARY KEY" in definition or "NOT NULL" in definition:
                continue

            logger.info("Adding email_analysis column. column=%s", column)

            connection.execute(
                f"""
                ALTER TABLE email_analysis
                ADD COLUMN {column} {definition}
                """
            )

    @staticmethod
    def _create_email_analysis_indexes(cursor: sqlite3.Cursor) -> None:
        """
        Create indexes used by email analysis queries.
        """

        logger.info("Creating email_analysis indexes if needed.")

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_email_analysis_sender_domain
            ON email_analysis(sender_domain)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_email_analysis_category
            ON email_analysis(category)
            """
        )

    def _execute_read(
        self,
        operation: Callable[[sqlite3.Connection], T],
    ) -> T:
        """
        Execute a read operation with managed error handling.
        """

        if self._connection is not None:
            try:
                return operation(self._connection)

            except sqlite3.Error as ex:
                logger.exception("Database read operation failed.")
                raise RuntimeError("Database read operation failed.") from ex

        try:
            with self.connect() as connection:
                return operation(connection)

        except sqlite3.Error as ex:
            logger.exception("Database read operation failed.")
            raise RuntimeError("Database read operation failed.") from ex

    def _execute_write(
        self,
        operation: Callable[[sqlite3.Connection], T],
    ) -> T:
        """
        Execute a write operation with managed error handling.
        """

        if self._connection is not None:
            try:
                return operation(self._connection)

            except sqlite3.Error as ex:
                logger.exception("Database write operation failed.")
                raise RuntimeError("Database write operation failed.") from ex

        try:
            with self.connect() as connection:
                result = operation(connection)
                connection.commit()
                return result

        except sqlite3.Error as ex:
            logger.exception("Database write operation failed.")
            raise RuntimeError("Database write operation failed.") from ex

    @staticmethod
    def _normalize_email_data(
        email: EmailMetadata | Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize full email metadata for insertion.
        """

        data = DatabaseManager._metadata_to_dict(email)

        if not data.get("gmail_id"):
            raise ValueError("gmail_id is required.")

        normalized = {
            column: data.get(column)
            for column in EMAIL_COLUMNS
        }

        normalized["is_read"] = int(bool(normalized.get("is_read", 0)))
        normalized["is_starred"] = int(bool(normalized.get("is_starred", 0)))
        normalized["is_important"] = int(bool(normalized.get("is_important", 0)))

        if normalized.get("last_synced") is None:
            normalized["last_synced"] = _utc_now()

        return normalized

    @staticmethod
    def _normalize_partial_email_data(
        email: EmailMetadata | Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize partial email metadata for updates.
        """

        data = DatabaseManager._metadata_to_dict(email)
        normalized = {
            column: data[column]
            for column in EMAIL_UPDATE_COLUMNS
            if column in data
        }

        for boolean_column in ("is_read", "is_starred", "is_important"):
            if boolean_column in normalized:
                normalized[boolean_column] = int(bool(normalized[boolean_column]))

        if "last_synced" not in normalized:
            normalized["last_synced"] = _utc_now()

        return normalized

    @staticmethod
    def _normalize_email_analysis_data(
        analysis: EmailAnalysis | Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize full email analysis data for insertion.
        """

        data = DatabaseManager._analysis_to_dict(analysis)

        if not data.get("gmail_id"):
            raise ValueError("gmail_id is required.")

        normalized = {
            column: data.get(column)
            for column in EMAIL_ANALYSIS_COLUMNS
        }

        for boolean_column in (
            "has_unsubscribe",
            "has_attachment",
            "has_html",
        ):
            normalized[boolean_column] = int(
                bool(normalized.get(boolean_column, 0))
            )

        if normalized.get("analyzed_at") is None:
            normalized["analyzed_at"] = _utc_now()

        return normalized

    @staticmethod
    @staticmethod
    def _metadata_to_dict(
        email: EmailMetadata | Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Convert email metadata input to a dictionary.
        """

        if isinstance(email, EmailMetadata):
            return asdict(email)

        return dict(email)

    @staticmethod
    def _analysis_to_dict(
        analysis: EmailAnalysis | Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Convert email analysis input to a dictionary.
        """

        if isinstance(analysis, EmailAnalysis):
            return asdict(analysis)

        return dict(analysis)


def _utc_now() -> str:
    """
    Return the current UTC timestamp.
    """

    return datetime.now(UTC).isoformat()
