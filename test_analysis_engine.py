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

            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="github",
                    sender="notifications@github.com",
                )
            )
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="newsletter",
                    sender="news@example.com",
                )
            )
            database.upsert_email_metadata(
                EmailMetadata(
                    gmail_id="unknown",
                    sender="person@example.com",
                    subject="Hello",
                )
            )

            database.save_email_content(
                EmailContent(
                    gmail_id="newsletter",
                    plain_text="To unsubscribe, use this link.",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="unknown",
                    plain_text="How are you?",
                    html_body="",
                    mime_type="text/plain",
                )
            )

            engine = AnalysisEngine(database, RuleEngine())
            statistics = engine.analyze_pending_emails()

            assert statistics.total_selected == 3
            assert statistics.analyzed == 3
            assert statistics.classified == 2
            assert statistics.unknown == 1
            assert statistics.failed == 0

            github_analysis = database.get_email_analysis("github")
            newsletter_analysis = database.get_email_analysis("newsletter")
            unknown_analysis = database.get_email_analysis("unknown")

            assert github_analysis is not None
            assert github_analysis.category == "Development"
            assert newsletter_analysis is not None
            assert newsletter_analysis.category == "Newsletter"
            assert unknown_analysis is not None
            assert unknown_analysis.category == "Unknown"

        finally:
            config.DATABASE_PATH = original_database_path


if __name__ == "__main__":
    run_tests()
    print("Analysis engine tests passed.")
