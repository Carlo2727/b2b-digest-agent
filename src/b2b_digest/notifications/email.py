import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from b2b_digest.config import Config
from b2b_digest.models import DailyDigest
from b2b_digest.notifications.formatter import format_to_email_html, format_to_markdown

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends digest notifications via standard SMTP (compatible with SendGrid, Mailgun, Brevo, Gmail)."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
    ):
        self.host = host or Config.SMTP_HOST
        self.port = port or Config.SMTP_PORT
        self.user = user or Config.SMTP_USER
        self.password = password or Config.SMTP_PASSWORD
        self.from_email = from_email or Config.SMTP_FROM_EMAIL or self.user
        self.to_email = to_email or Config.SMTP_TO_EMAIL

    def send_digest(self, digest: DailyDigest) -> bool:
        """Send multipart text/html email with daily digest."""
        if not self.host or not self.to_email:
            logger.warning("SMTP host or recipient email not configured. Email skipped.")
            return False

        subject = f"📊 B2B Digest Intelligence — {digest.date} ({digest.total_items_analyzed} Nuovi Bandi/Norme)"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = self.to_email

        plain_text = format_to_markdown(digest)
        html_body = format_to_email_html(digest)

        part_plain = MIMEText(plain_text, "plain", "utf-8")
        part_html = MIMEText(html_body, "html", "utf-8")

        msg.attach(part_plain)
        msg.attach(part_html)

        try:
            logger.info("Connecting to SMTP server %s:%d...", self.host, self.port)
            if self.port == 465:
                # SSL Direct
                with smtplib.SMTP_SSL(self.host, self.port, timeout=Config.TIMEOUT_SECONDS) as server:
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                # STARTTLS (typically port 587 or 25)
                with smtplib.SMTP(self.host, self.port, timeout=Config.TIMEOUT_SECONDS) as server:
                    server.ehlo()
                    try:
                        server.starttls()
                        server.ehlo()
                    except smtplib.SMTPNotSupportedError:
                        logger.debug("STARTTLS not supported by server, proceeding without it.")

                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(msg)

            logger.info("Digest email successfully sent to %s", self.to_email)
            return True

        except Exception as e:
            logger.error("Failed to send digest email: %s", e)
            return False
