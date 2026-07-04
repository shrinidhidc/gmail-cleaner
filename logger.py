"""
MailCleaner Logging Module

Provides centralized application logging with both console and
rotating file handlers.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import config

_LOGGER_INITIALIZED = False


def setup_logger() -> None:
    """
    Configure the root logger.

    Safe to call multiple times.
    """
    global _LOGGER_INITIALIZED

    if _LOGGER_INITIALIZED:
        return

    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove default handlers (important if rerun)
    root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating File Handler
    file_handler = RotatingFileHandler(
        filename=config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _LOGGER_INITIALIZED = True

    logging.getLogger(__name__).info("Logger initialized.")


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger instance.

    Parameters
    ----------
    name : str
        Module name.

    Returns
    -------
    logging.Logger
    """
    return logging.getLogger(name)