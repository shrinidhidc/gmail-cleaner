"""
MailCleaner Rule Engine

Deterministic email analysis rules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Final

from models import EmailAnalysis, EmailContent, EmailMetadata

RULE_ENGINE_NAME: Final[str] = "rule_engine"


class RuleEngine:
    """
    Analyze email data using ordered deterministic rules.
    """

    def analyze(
        self,
        metadata: EmailMetadata,
        content: EmailContent | None,
    ) -> EmailAnalysis:
        """
        Analyze one email and return deterministic analysis results.
        """

        sender_domain = self._extract_sender_domain(metadata.sender)
        has_html = int(bool(content and content.html_body))
        has_attachment = int(bool(content and content.attachment_count))

        for match in (
            self._match_sender(metadata),
            self._match_sender_domain(sender_domain),
            self._match_keywords(metadata, content),
            self._match_unsubscribe(content),
        ):
            if match is not None:
                category, importance, confidence, has_unsubscribe = match
                return self._build_analysis(
                    gmail_id=metadata.gmail_id,
                    sender_domain=sender_domain,
                    category=category,
                    importance=importance,
                    confidence=confidence,
                    has_unsubscribe=has_unsubscribe,
                    has_attachment=has_attachment,
                    has_html=has_html,
                )

        return self._build_analysis(
            gmail_id=metadata.gmail_id,
            sender_domain=sender_domain,
            category="Unknown",
            importance="Unknown",
            confidence=0.0,
            has_unsubscribe=0,
            has_attachment=has_attachment,
            has_html=has_html,
        )

    @staticmethod
    def _match_sender(
        metadata: EmailMetadata,
    ) -> tuple[str, str, float, int] | None:
        """
        Match automated sender addresses.
        """

        sender = (metadata.sender or "").lower()

        if any(value in sender for value in ("noreply", "no-reply", "donotreply")):
            return "System", "Low", 0.98, 0

        return None

    @staticmethod
    def _match_sender_domain(
        sender_domain: str | None,
    ) -> tuple[str, str, float, int] | None:
        """
        Match known sender domains.
        """

        if not sender_domain:
            return None

        if "github.com" in sender_domain:
            return "Development", "High", 0.99, 0

        if any(value in sender_domain for value in ("amazon", "flipkart", "myntra")):
            return "Shopping", "Medium", 0.95, 0

        return None

    @staticmethod
    def _match_keywords(
        metadata: EmailMetadata,
        content: EmailContent | None,
    ) -> tuple[str, str, float, int] | None:
        """
        Match OTP-related subject and body keywords.
        """

        text = " ".join(
            value
            for value in (
                metadata.subject,
                content.plain_text if content else None,
                content.html_body if content else None,
            )
            if value
        ).lower()

        if any(
            value in text
            for value in (
                "otp",
                "one time password",
                "verification code",
            )
        ):
            return "OTP", "High", 0.99, 0

        return None

    @staticmethod
    def _match_unsubscribe(
        content: EmailContent | None,
    ) -> tuple[str, str, float, int] | None:
        """
        Match newsletter unsubscribe text in the email body.
        """

        if content is None:
            return None

        body = " ".join(
            value
            for value in (content.plain_text, content.html_body)
            if value
        ).lower()

        if "unsubscribe" in body:
            return "Newsletter", "Low", 0.95, 1

        return None

    @staticmethod
    def _extract_sender_domain(sender: str | None) -> str | None:
        """
        Extract the normalized sender domain from an email address.
        """

        if not sender:
            return None

        _, email_address = parseaddr(sender)
        address = email_address or sender

        if "@" not in address:
            return None

        return address.rsplit("@", maxsplit=1)[1].lower()

    @staticmethod
    def _build_analysis(
        gmail_id: str,
        sender_domain: str | None,
        category: str,
        importance: str,
        confidence: float,
        has_unsubscribe: int,
        has_attachment: int,
        has_html: int,
    ) -> EmailAnalysis:
        """
        Build a complete email analysis result.
        """

        return EmailAnalysis(
            gmail_id=gmail_id,
            sender_domain=sender_domain,
            category=category,
            importance=importance,
            has_unsubscribe=has_unsubscribe,
            has_attachment=has_attachment,
            has_html=has_html,
            confidence=confidence,
            analyzed_by=RULE_ENGINE_NAME,
            analyzed_at=datetime.now(UTC).isoformat(),
        )
