from pathlib import Path
from tempfile import TemporaryDirectory

import config
from analysis_engine import AnalysisEngine
from database import DatabaseManager
from models import EmailContent, EmailMetadata
from rule_engine import RuleEngine


def run_tests() -> None:
    original_database_path = config.DATABASE_PATH

    with TemporaryDirectory() as temporary_directory:
        config.DATABASE_PATH = Path(temporary_directory) / "mailcleaner.db"

        try:
            database = DatabaseManager()
            database.initialize()

            # Test case 1: "John Doe <john@example.com>"
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="john-doe",
                    sender="John Doe <john@example.com>",
                )
            )

            # Test case 2: "john@example.com"
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="john",
                    sender="john@example.com",
                )
            )

            # Test case 3: "Amazon India <store-news@amazon.in>"
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="amazon",
                    sender="Amazon India <store-news@amazon.in>",
                )
            )

            # Test case 4: Empty sender
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="empty",
                    sender="",
                )
            )

            # Test case 5: Invalid sender string
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="invalid",
                    sender="invalid-sender",
                )
            )

            # Add content for analysis
            database.save_email_content(
                EmailContent(
                    gmail_id="john-doe",
                    plain_text="To unsubscribe, use this link.",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="john",
                    plain_text="How are you?",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="amazon",
                    plain_text="Welcome to Amazon India!",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="empty",
                    plain_text="",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="invalid",
                    plain_text="Invalid sender",
                    html_body="",
                    mime_type="text/plain",
                )
            )

            engine = AnalysisEngine(database, RuleEngine())
            statistics = engine.analyze_pending_emails()

            assert statistics.total_selected == 5
            assert statistics.analyzed == 5
            assert statistics.classified == 4
            assert statistics.unknown == 1
            assert statistics.failed == 0

            # Verify sender domain parsing
            john_doe_analysis = database.get_email_analysis("john-doe")
            john_analysis = database.get_email_analysis("john")
            amazon_analysis = database.get_email_analysis("amazon")
            empty_analysis = database.get_email_analysis("empty")
            invalid_analysis = database.get_email_analysis("invalid")

            assert john_doe_analysis is not None
            assert john_doe_analysis.sender_domain == "example.com"
            assert john_analysis is not None
            assert john_analysis.sender_domain == "example.com"
            assert amazon_analysis is not None
            assert amazon_analysis.sender_domain == "amazon.in"
            assert empty_analysis is not None
            assert empty_analysis.sender_domain == ""
            assert invalid_analysis is not None
            assert invalid_analysis.sender_domain == ""

        finally:
            config.DATABASE_PATH = original_database_path


if __name__ == "__main__":
    run_tests()
    print("Analysis engine tests passed.")
