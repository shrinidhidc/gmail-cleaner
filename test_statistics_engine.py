from pathlib import Path
from tempfile import TemporaryDirectory

import config
from database import DatabaseManager
from models import EmailAnalysis, EmailContent, EmailMetadata
from statistics_engine import StatisticsEngine


def run_tests() -> None:
    original_database_path = config.DATABASE_PATH

    with TemporaryDirectory() as temporary_directory:
        config.DATABASE_PATH = Path(temporary_directory) / "mailcleaner.db"

        try:
            database = DatabaseManager()
            database.initialize()

            for gmail_id in ("shopping-one", "shopping-two", "unknown"):
                database.upsert_email_metadata(
                    EmailMetadata(gmail_id=gmail_id)
                )

            database.save_email_content(
                EmailContent(
                    gmail_id="shopping-one",
                    plain_text="Order update",
                    html_body="",
                    mime_type="text/plain",
                )
            )
            database.save_email_content(
                EmailContent(
                    gmail_id="unknown",
                    plain_text="Hello",
                    html_body="",
                    mime_type="text/plain",
                )
            )

            database.save_email_analysis(
                EmailAnalysis(
                    gmail_id="shopping-one",
                    sender_domain="amazon.in",
                    category="Shopping",
                )
            )
            database.save_email_analysis(
                EmailAnalysis(
                    gmail_id="shopping-two",
                    sender_domain="amazon.in",
                    category="Shopping",
                )
            )
            database.save_email_analysis(
                EmailAnalysis(
                    gmail_id="unknown",
                    sender_domain="example.com",
                    category="Unknown",
                )
            )

            engine = StatisticsEngine(database)
            mailbox_statistics = engine.get_mailbox_statistics()
            category_statistics = engine.get_category_statistics()
            sender_domain_statistics = engine.get_sender_domain_statistics()
            unknown_sender_domains = engine.get_unknown_sender_domains()

            assert mailbox_statistics.total_emails == 3
            assert mailbox_statistics.total_content == 2
            assert mailbox_statistics.total_analysis == 3
            assert mailbox_statistics.classified == 2
            assert mailbox_statistics.unknown == 1
            assert mailbox_statistics.failed_analysis == 0
            assert [
                (category.category, category.count)
                for category in category_statistics
            ] == [("Shopping", 2), ("Unknown", 1)]
            assert [
                (domain.sender_domain, domain.count)
                for domain in sender_domain_statistics
            ] == [("amazon.in", 2), ("example.com", 1)]
            assert [
                (domain.sender_domain, domain.count)
                for domain in unknown_sender_domains
            ] == [("example.com", 1)]

        finally:
            config.DATABASE_PATH = original_database_path


if __name__ == "__main__":
    run_tests()
    print("Statistics engine tests passed.")
