"""
===========================================================================
MailCleaner

Module:
    Main

Purpose:
    Executable entry point for MailCleaner.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations

import sys
from typing import Final

import application
from console import console
from logger import get_logger, setup_logger

EXIT_SUCCESS: Final[int] = 0
EXIT_UNEXPECTED_ERROR: Final[int] = 99

logger = get_logger(__name__)


def main() -> int:
    """
    Run MailCleaner and return a process exit code.

    Returns
    -------
    int
        Process exit code returned by the application layer.
    """

    setup_logger()
    logger.info("MailCleaner process starting.")

    try:
        exit_code = application.main()

        logger.info(
            "MailCleaner process completed. exit_code=%s",
            exit_code,
        )

        return exit_code

    except KeyboardInterrupt:
        logger.warning("MailCleaner process interrupted by user.")
        console.warning("MailCleaner interrupted by user.")
        return EXIT_SUCCESS

    except Exception as ex:
        logger.exception("Unhandled top-level MailCleaner error.")
        console.error(f"Unexpected fatal error: {ex}")
        return EXIT_UNEXPECTED_ERROR

    finally:
        logger.info("MailCleaner process stopped.")


if __name__ == "__main__":
    sys.exit(main())
