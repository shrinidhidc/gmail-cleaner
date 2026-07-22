"""
MailCleaner Configuration

This module contains all application-wide configuration values.
No business logic should be placed here.

Author: MailCleaner
"""

from pathlib import Path

# ============================================================================
# Application Information
# ============================================================================

APPLICATION_NAME = "MailCleaner"
APPLICATION_VERSION = "0.2.0"

STARTUP_BANNER = "=" * 60

ENABLE_ANALYSIS = True
ENABLE_SYNC = False

ANALYSIS_LIMIT = 500

# ============================================================================
# Project Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# ============================================================================
# Gmail OAuth
# ============================================================================

CREDENTIALS_PATH = CREDENTIALS_DIR / "credentials.json"
TOKEN_PATH = CREDENTIALS_DIR / "token.json"

# OAuth Scopes
#
# gmail.modify allows us to:
#   - Read messages
#   - Archive
#   - Remove labels
#   - Add labels
#   - Trash messages
#
# We intentionally avoid broader scopes.
#

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

# ============================================================================
# Database
# ============================================================================

DATABASE_PATH = DATA_DIR / "mailcleaner.db"

# ============================================================================
# Logging
# ============================================================================

LOG_FILE = LOG_DIR / "mailcleaner.log"

LOG_LEVEL = "INFO"

LOG_MAX_BYTES = 5 * 1024 * 1024      # 5 MB

LOG_BACKUP_COUNT = 5

# ============================================================================
# Gmail API Settings
# ============================================================================

PAGE_SIZE = 500

REQUEST_TIMEOUT = 60

# ============================================================================
# Create Required Directories
# ============================================================================

DATA_DIR.mkdir(exist_ok=True)

LOG_DIR.mkdir(exist_ok=True)

# ============================================================================
# Validation
# ============================================================================


def validate_configuration() -> None:
    """
    Validate mandatory project resources.

    Raises
    ------
    FileNotFoundError
        If credentials.json is missing.
    """

    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"credentials.json not found:\n{CREDENTIALS_PATH}"
        )
