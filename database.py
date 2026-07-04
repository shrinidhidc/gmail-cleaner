"""
MailCleaner Database Module

Handles SQLite database creation and connectivity.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import config
from logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    SQLite database manager.
    """

    def __init__(self) -> None:
        self.database_path: Path = config.DATABASE_PATH

    def connect(self) -> sqlite3.Connection:
        """
        Open a SQLite connection.
        """
        connection = sqlite3.connect(self.database_path)

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def initialize(self) -> None:
        """
        Create database schema if it does not exist.
        """
        logger.info("Initializing database...")

        with self.connect() as connection:
            cursor = connection.cursor()

            # ----------------------------------------------------------
            # Messages
            # ----------------------------------------------------------

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

            # ----------------------------------------------------------
            # Senders
            # ----------------------------------------------------------

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

            # ----------------------------------------------------------
            # Sync State
            # ----------------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (

                    key TEXT PRIMARY KEY,

                    value TEXT
                )
                """
            )

            connection.commit()

        logger.info("Database initialized successfully.")