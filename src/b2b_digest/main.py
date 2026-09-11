import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import List

# Ensure UTF-8 output in console (especially on Windows consoles with CP1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from b2b_digest.analyzer.gemini import GeminiDigestAnalyzer
from b2b_digest.config import Config
from b2b_digest.models import DailyDigest, DigestItem, ItemCategory, PriorityLevel, RawItem
from b2b_digest.notifications.email import EmailNotifier
from b2b_digest.notifications.formatter import format_to_html, format_to_markdown
from b2b_digest.notifications.telegram import TelegramNotifier
from b2b_digest.scraper.sources import PublicSourcesCollector
from b2b_digest.storage import StorageManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("b2b-digest")


def run_pipeline(
    dry_run: bool = False,
    use_sample: bool = False,
    limit: int = Config.MAX_ITEMS_PER_RUN,
) -> int:
    """Execute the full scraping -> LLM analysis -> dispatch pipeline."""
    logger.info("Starting B2B Digest Agent pipeline (dry_run=%s, use_sample=%s)...", dry_run, use_sample)

    # 1. Initialize Deduplication Storage
    storage = StorageManager(Config.SEEN_IDS_FILE)

    # 2. Collect Items
    if use_sample:
        logger.info("Using built-in sample items for testing/offline run.")
        raw_items = PublicSourcesCollector.get_sample_items()
    else:
        collector = PublicSourcesCollector()
        raw_items = collector.collect()

    if not raw_items:
        logger.warning("No items collected from sources. Exiting pipeline.")
        return 0

    # 3. Filter Duplicates via seen_ids.json
    unseen_items: List[RawItem] = storage.filter_unseen(raw_items)
    if not unseen_items:
        logger.info("All %d items have already been processed in previous runs. Nothing new to report.", len(raw_items))
        return 0

    # Respect item limit
    target_items = unseen_items[:limit]
    logger.info("Selected %d fresh items for Gemini analysis.", len(target_items))

    # 4. LLM Analysis with Gemini Pro
    digest: DailyDigest
    if dry_run and not Config.GEMINI_API_KEY:
        logger.info("[DRY-RUN] No GEMINI_API_KEY found. Generating simulated structured digest for verification.")
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        digest = DailyDigest(
            date=today_str,
            executive_summary=(
                "Rilevate opportunità rilevanti nel settore ICT, transizione energetica PNRR "
                "e nuove norme di conformità fiscale e digitale."
            ),
            total_items_analyzed=len(target_items),
            items=[
                DigestItem(
                    title=item.title,
                    category=ItemCategory.BANDO_GARA if "bando" in item.title.lower() or "gara" in item.title.lower() else ItemCategory.NOVITA_NORMATIVA,
                    priority=PriorityLevel.ALTA if "pnrr" in item.title.lower() or "45.000.000" in item.raw_content else PriorityLevel.MEDIA,
                    issuer=item.source_name,
                    importo_o_agevolazione="€ 45.000.000" if "45.000.000" in item.raw_content else "€ 6.300.000.000 (Fondo complessivo)",
                    data_scadenza="30/11/2026",
                    key_takeaways=[
                        "Incentivo/appalto rivolto a imprese operanti sul territorio nazionale.",
                        "Requisiti di conformità e certificazione tecnica specificati nel bando.",
                        "Procedura telematica per presentazione offerte o istanze.",
                    ],
                    target_audience="PMI, Grandi Imprese, Società IT",
                    original_url=item.url,
                    actionable_step="Scaricare il capitolato e verificare l'abilitazione sui portali di e-procurement.",
                )
                for item in target_items
            ],
        )
    else:
        analyzer = GeminiDigestAnalyzer()
        digest = analyzer.analyze(target_items)

    # 5. Format & Dispatch
    if dry_run:
        logger.info("[DRY-RUN] Printing formatted Telegram HTML:")
        print("\n" + "=" * 40 + " TELEGRAM HTML OUTPUT " + "=" * 40)
        print(format_to_html(digest))
        print("=" * 102 + "\n")

        logger.info("[DRY-RUN] Printing formatted Markdown output:")
        print(format_to_markdown(digest))
        logger.info("[DRY-RUN] Completed without external dispatches or state persistence.")
        return 0

    # Production dispatch
    dispatched_any = False

    if Config.TELEGRAM_ENABLED:
        telegram = TelegramNotifier()
        if telegram.send_digest(digest):
            dispatched_any = True

    if Config.SMTP_ENABLED:
        email = EmailNotifier()
        if email.send_digest(digest):
            dispatched_any = True

    # 6. Update seen_ids.json so items are not sent again tomorrow
    if dispatched_any or not (Config.TELEGRAM_ENABLED or Config.SMTP_ENABLED):
        processed_ids = [item.id for item in target_items]
        storage.mark_seen(processed_ids)
        logger.info("Marked %d items as seen in %s", len(processed_ids), Config.SEEN_IDS_FILE)

    logger.info("Pipeline execution successfully finished.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="b2b-digest-agent: Automated B2B Intelligence & Tender Digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate pipeline without dispatching messages or altering seen_ids.json.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use built-in mock public source data instead of live network scraping.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=Config.MAX_ITEMS_PER_RUN,
        help="Maximum items to process in this run.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    sys.exit(run_pipeline(dry_run=args.dry_run, use_sample=args.sample, limit=args.limit))


if __name__ == "__main__":
    main()
