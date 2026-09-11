import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Automatically load environment variables from .env file if present
load_dotenv()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

class Config:
    """Central configuration class for b2b-digest-agent."""

    # Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Telegram settings
    TELEGRAM_ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Email / SMTP settings
    SMTP_ENABLED: bool = os.getenv("SMTP_ENABLED", "false").lower() in ("true", "1", "yes")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_TO_EMAIL: str = os.getenv("SMTP_TO_EMAIL", "")

    # Scraper and general settings
    USER_AGENT: str = os.getenv("USER_AGENT", DEFAULT_USER_AGENT)
    MAX_ITEMS_PER_RUN: int = int(os.getenv("MAX_ITEMS_PER_RUN", "15"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))
    SEEN_IDS_FILE: Path = Path(os.getenv("SEEN_IDS_FILE", "seen_ids.json"))

    @classmethod
    def validate_runtime(cls, dry_run: bool = False) -> None:
        """Validate that minimum required configuration exists for real runs."""
        if dry_run:
            return

        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or .env file."
            )

        if cls.TELEGRAM_ENABLED:
            if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
                raise ValueError(
                    "TELEGRAM_ENABLED is True, but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing."
                )

        if cls.SMTP_ENABLED:
            if not all([cls.SMTP_HOST, cls.SMTP_USER, cls.SMTP_PASSWORD, cls.SMTP_TO_EMAIL]):
                raise ValueError(
                    "SMTP_ENABLED is True, but one or more required SMTP settings are missing."
                )
