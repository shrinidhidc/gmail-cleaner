"""
===========================================================================
MailCleaner

Module:
    Authentication

Purpose:
    Handles Gmail OAuth authentication.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config
from logger import get_logger

logger = get_logger(__name__)


def authenticate() -> Credentials:
    """
    Authenticate with Gmail.

    Returns
    -------
    Credentials
        Valid Google credentials.
    """

    logger.info("Starting Gmail authentication...")

    credentials: Optional[Credentials] = None

    # -------------------------------------------------------------
    # Load existing token
    # -------------------------------------------------------------

    if config.TOKEN_PATH.exists():
        logger.info("Loading existing token.")

        credentials = Credentials.from_authorized_user_file(
            str(config.TOKEN_PATH),
            config.GMAIL_SCOPES
        )

    # -------------------------------------------------------------
    # Refresh expired token
    # -------------------------------------------------------------

    if credentials and credentials.expired and credentials.refresh_token:
        logger.info("Refreshing expired token...")

        credentials.refresh(Request())

        logger.info("Token refreshed successfully.")

    # -------------------------------------------------------------
    # Launch OAuth flow
    # -------------------------------------------------------------

    if credentials is None or not credentials.valid:

        logger.info("Launching OAuth browser authentication...")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(config.CREDENTIALS_PATH),
            config.GMAIL_SCOPES
        )

        credentials = flow.run_local_server(port=0)

        logger.info("OAuth authentication successful.")

        config.TOKEN_PATH.write_text(credentials.to_json())

        logger.info("Token saved successfully.")

    logger.info("Authentication completed.")

    return credentials