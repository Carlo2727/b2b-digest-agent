import hashlib
import logging
import re
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

from b2b_digest.config import Config
from b2b_digest.models import RawItem

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base scraper providing configured HTTP requests with standard browser headers."""

    DEFAULT_BROWSER_HEADERS: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    def __init__(self, custom_user_agent: Optional[str] = None, timeout: int = Config.TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure headers with user agent to avoid HTTP 403 Forbidden
        headers = self.DEFAULT_BROWSER_HEADERS.copy()
        if custom_user_agent or Config.USER_AGENT:
            headers["User-Agent"] = custom_user_agent or Config.USER_AGENT
        
        self.session.headers.update(headers)

    def fetch(self, url: str) -> Optional[str]:
        """Fetch URL content with standard browser headers and error handling."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            # Ensure proper encoding
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.HTTPError as e:
            logger.error("HTTP error fetching %s: %s (Status: %s)", url, e, getattr(e.response, "status_code", None))
            return None
        except requests.RequestException as e:
            logger.error("Network error fetching %s: %s", url, e)
            return None

    @staticmethod
    def generate_item_id(url: str, title: Optional[str] = None) -> str:
        """Generate a deterministic unique ID for deduplication."""
        base = f"{url.strip().lower()}|{(title or '').strip().lower()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def clean_html_text(html_content: str, max_chars: int = 4000) -> str:
        """Strip scripts, styles, navigations, and clean whitespace from HTML."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove irrelevant and clutter tags
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form"]):
            element.decompose()

        text = soup.get_text(separator="\n")
        # Normalize whitespace and excessive newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        
        if len(cleaned) > max_chars:
            return cleaned[:max_chars] + "... [Troncato per limiti di contesto]"
        return cleaned

    def scrape(self) -> List[RawItem]:
        """Subclasses should implement source-specific scraping logic."""
        raise NotImplementedError("Subclasses must implement scrape()")
