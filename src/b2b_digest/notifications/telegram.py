import logging
from typing import List, Optional
import requests

from b2b_digest.config import Config
from b2b_digest.models import DailyDigest
from b2b_digest.notifications.formatter import format_to_html

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends structured digest notifications via Telegram Bot API using HTML parse mode."""

    TELEGRAM_API_BASE = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 4000  # Telegram limit is 4096, keeping safety margin

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = Config.TIMEOUT_SECONDS,
    ):
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.TELEGRAM_CHAT_ID
        self.timeout = timeout

    def _split_html_message(self, text: str) -> List[str]:
        """Split a long HTML message into chunks under 4000 chars without breaking tags."""
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        # Split by double newline or item separator
        parts = text.split("\n\n")
        current_chunk = ""

        for part in parts:
            if len(current_chunk) + len(part) + 2 > self.MAX_MESSAGE_LENGTH:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = part + "\n\n"
                else:
                    # Single block exceeds limit, cut directly
                    chunks.append(part[: self.MAX_MESSAGE_LENGTH])
                    current_chunk = part[self.MAX_MESSAGE_LENGTH :] + "\n\n"
            else:
                current_chunk += part + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def send_message(self, text: str) -> bool:
        """Send a single text message to configured chat using parse_mode="HTML"."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot token or Chat ID is missing. Message not sent.")
            return False

        url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response_json = response.json() if response.content else {}

            if response.status_code == 200 and response_json.get("ok"):
                logger.info("Successfully sent message to Telegram chat %s", self.chat_id)
                return True
            else:
                logger.error(
                    "Failed to send Telegram message. HTTP %s: %s",
                    response.status_code,
                    response_json.get("description", response.text),
                )
                return False

        except requests.RequestException as e:
            logger.error("Network error sending Telegram message: %s", e)
            return False

    def send_digest(self, digest: DailyDigest) -> bool:
        """Format and dispatch full digest to Telegram."""
        html_content = format_to_html(digest)
        chunks = self._split_html_message(html_content)

        success = True
        logger.info("Dispatching %d message chunk(s) to Telegram...", len(chunks))

        for idx, chunk in enumerate(chunks, 1):
            sent = self.send_message(chunk)
            if not sent:
                success = False
                logger.error("Failed sending chunk %d of %d to Telegram.", idx, len(chunks))

        return success
