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

def _get_int(var_name: str, default: int) -> int:
    val = os.getenv(var_name)
    if not val or not val.strip():
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default

class Config:
    """Central configuration class for b2b-digest-agent."""

    # Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()

    # Telegram settings
    TELEGRAM_ENABLED: bool = (os.getenv("TELEGRAM_ENABLED") or "true").strip().lower() in ("true", "1", "yes")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # Email / SMTP settings
    SMTP_ENABLED: bool = (os.getenv("SMTP_ENABLED") or "false").strip().lower() in ("true", "1", "yes")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = _get_int("SMTP_PORT", 587)
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "").strip()
    SMTP_TO_EMAIL: str = os.getenv("SMTP_TO_EMAIL", "").strip()

    # Scraper and general settings
    USER_AGENT: str = os.getenv("USER_AGENT") or DEFAULT_USER_AGENT
    MAX_ITEMS_PER_RUN: int = _get_int("MAX_ITEMS_PER_RUN", 15)
    TIMEOUT_SECONDS: int = _get_int("TIMEOUT_SECONDS", 30)
    SEEN_IDS_FILE: Path = Path(os.getenv("SEEN_IDS_FILE") or "seen_ids.json")

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
