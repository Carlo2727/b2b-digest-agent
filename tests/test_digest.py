import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from b2b_digest.main import run_pipeline
from b2b_digest.models import DailyDigest, DigestItem, ItemCategory, PriorityLevel, RawItem
from b2b_digest.notifications.formatter import format_to_html, format_to_markdown
from b2b_digest.notifications.telegram import TelegramNotifier
from b2b_digest.scraper.base import BaseScraper
from b2b_digest.scraper.sources import PublicSourcesCollector
from b2b_digest.storage import StorageManager


class TestStorageManager(unittest.TestCase):
    """Test deduplication storage and persistence in seen_ids.json."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "test_seen_ids.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_initialization(self):
        storage = StorageManager(self.file_path)
        self.assertEqual(len(storage.seen_ids), 0)

    def test_filter_and_mark_seen(self):
        storage = StorageManager(self.file_path)
        items = [
            RawItem(id="item-1", title="Bando 1", url="http://example.com/1", source_name="Test", raw_content="A"),
            RawItem(id="item-2", title="Bando 2", url="http://example.com/2", source_name="Test", raw_content="B"),
        ]

        # Both unseen initially
        unseen = storage.filter_unseen(items)
        self.assertEqual(len(unseen), 2)

        # Mark item-1 as seen
        storage.mark_seen(["item-1"])
        self.assertTrue(storage.is_seen("item-1"))
        self.assertFalse(storage.is_seen("item-2"))

        # Re-filter: only item-2 remains
        unseen_after = storage.filter_unseen(items)
        self.assertEqual(len(unseen_after), 1)
        self.assertEqual(unseen_after[0].id, "item-2")

        # Verify disk persistence
        storage2 = StorageManager(self.file_path)
        self.assertTrue(storage2.is_seen("item-1"))
        self.assertFalse(storage2.is_seen("item-2"))


class TestBaseScraper(unittest.TestCase):
    """Test scraper headers and text cleaning."""

    def test_user_agent_header_present(self):
        scraper = BaseScraper()
        user_agent = scraper.session.headers.get("User-Agent")
        self.assertIsNotNone(user_agent)
        self.assertIn("Mozilla", user_agent)
        self.assertIn("Chrome", user_agent)

    def test_clean_html_text(self):
        raw_html = """
        <html>
            <head><style>body { color: red; }</style></head>
            <body>
                <nav><a href="/home">Home</a></nav>
                <div class="content">
                    <h1>Avviso di gara</h1>
                    <p>Fornitura di apparati server per la PA.</p>
                </div>
                <script>console.log("tracking");</script>
                <footer>Diritti riservati</footer>
            </body>
        </html>
        """
        cleaned = BaseScraper.clean_html_text(raw_html)
        self.assertIn("Avviso di gara", cleaned)
        self.assertIn("Fornitura di apparati server", cleaned)
        self.assertNotIn("color: red", cleaned)
        self.assertNotIn("console.log", cleaned)
        self.assertNotIn("Home", cleaned)
        self.assertNotIn("Diritti riservati", cleaned)


class TestTelegramAndFormatters(unittest.TestCase):
    """Test Telegram HTML output, escaping and message chunking."""

    def setUp(self):
        self.sample_digest = DailyDigest(
            date="2026-09-11",
            executive_summary="Sintesi per aziende con caratteri speciali: <test> & 'quotes'.",
            total_items_analyzed=1,
            items=[
                DigestItem(
                    title="Bando Speciale <PA & Imprese>",
                    category=ItemCategory.BANDO_GARA,
                    priority=PriorityLevel.ALTA,
                    issuer="Ministero dello Sviluppo",
                    importo_o_agevolazione="€ 1.500.000",
                    data_scadenza="15/10/2026",
                    key_takeaways=[
                        "Requisito: certificazione ISO <9001>",
                        "Contributo a fondo perduto fino al 60%",
                    ],
                    target_audience="PMI & Grandi Imprese",
                    original_url="https://example.com/bando?id=123&lang=it",
                    actionable_step="Presentare istanza telematica.",
                )
            ],
        )

    def test_format_to_html_escapes_properly(self):
        html_out = format_to_html(self.sample_digest)
        # Should not have raw unescaped <PA & Imprese> or <test>
        self.assertNotIn("<PA & Imprese>", html_out)
        self.assertIn("&lt;PA &amp; Imprese&gt;", html_out)
        self.assertNotIn("<test>", html_out)
        self.assertIn("&lt;test&gt;", html_out)
        # Standard tags must remain
        self.assertIn("<b>", html_out)
        self.assertIn("</b>", html_out)
        self.assertIn("<a href=\"https://example.com/bando?id=123&amp;lang=it\">", html_out)

    def test_telegram_message_split(self):
        notifier = TelegramNotifier()
        # Create a text longer than MAX_MESSAGE_LENGTH (4000)
        long_text = ("Paragrafo importante.\n\n" * 300)
        chunks = notifier._split_html_message(long_text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), notifier.MAX_MESSAGE_LENGTH)


class TestPipelineDryRun(unittest.TestCase):
    """Test full pipeline dry-run with sample data."""

    def test_run_pipeline_dry_run_with_samples(self):
        exit_code = run_pipeline(dry_run=True, use_sample=True, limit=2)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
