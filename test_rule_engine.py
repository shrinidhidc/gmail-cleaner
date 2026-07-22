from models import EmailContent, EmailMetadata
from rule_engine import RuleEngine


def run_tests() -> None:
    engine = RuleEngine()

    system_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="system",
            sender="noreply@example.com",
        ),
        None,
    )
    assert system_analysis.category == "System"
    assert system_analysis.importance == "Low"
    assert system_analysis.confidence == 0.98

    development_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="development",
            sender="GitHub <notifications@github.com>",
        ),
        None,
    )
    assert development_analysis.category == "Development"
    assert development_analysis.importance == "High"
    assert development_analysis.confidence == 0.99

    shopping_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="shopping",
            sender="orders@amazon.in",
        ),
        None,
    )
    assert shopping_analysis.category == "Shopping"
    assert shopping_analysis.importance == "Medium"
    assert shopping_analysis.confidence == 0.95

    otp_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="otp",
            sender="security@example.com",
            subject="Your Verification Code",
        ),
        None,
    )
    assert otp_analysis.category == "OTP"
    assert otp_analysis.importance == "High"
    assert otp_analysis.confidence == 0.99

    newsletter_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="newsletter",
            sender="news@example.com",
        ),
        EmailContent(
            gmail_id="newsletter",
            plain_text="To unsubscribe, use this link.",
            html_body="",
            mime_type="text/plain",
        ),
    )
    assert newsletter_analysis.category == "Newsletter"
    assert newsletter_analysis.importance == "Low"
    assert newsletter_analysis.has_unsubscribe == 1

    unknown_analysis = engine.analyze(
        EmailMetadata(
            gmail_id="unknown",
            sender="person@example.com",
            subject="Hello",
        ),
        EmailContent(
            gmail_id="unknown",
            plain_text="How are you?",
            html_body="<p>How are you?</p>",
            mime_type="multipart/alternative",
        ),
    )
    assert unknown_analysis.category == "Unknown"
    assert unknown_analysis.importance == "Unknown"
    assert unknown_analysis.confidence == 0.0
    assert unknown_analysis.has_html == 1


if __name__ == "__main__":
    run_tests()
    print("Rule engine tests passed.")
