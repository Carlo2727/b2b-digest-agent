import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

from b2b_digest.models import RawItem

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages persistence of processed item IDs to avoid sending duplicates."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.seen_ids: Set[str] = self._load()

    def _load(self) -> Set[str]:
        """Load seen IDs from disk."""
        if not self.file_path.exists():
            logger.info("No %s found. Initializing empty seen IDs set.", self.file_path)
            return set()

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "seen_ids" in data:
                    return set(data["seen_ids"])
                elif isinstance(data, list):
                    return set(data)
                return set()
        except Exception as e:
            logger.warning("Failed to parse %s (%s). Starting with empty set.", self.file_path, e)
            return set()

    def is_seen(self, item_id: str) -> bool:
        """Check if an item ID has already been processed."""
        return item_id in self.seen_ids

    def filter_unseen(self, items: List[RawItem]) -> List[RawItem]:
        """Return only items that have not been processed yet."""
        unseen = [item for item in items if item.id not in self.seen_ids]
        logger.info("Found %d total items, %d are new and unseen.", len(items), len(unseen))
        return unseen

    def mark_seen(self, item_ids: List[str]) -> None:
        """Add item IDs to seen set and persist to disk."""
        if not item_ids:
            return

        self.seen_ids.update(item_ids)

        # Keep a max cap of 5000 IDs to prevent unbounded file growth
        capped_ids = sorted(list(self.seen_ids))
        if len(capped_ids) > 5000:
            capped_ids = capped_ids[-5000:]
            self.seen_ids = set(capped_ids)

        payload = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "seen_ids": capped_ids,
        }

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info("Saved %d seen IDs to %s.", len(capped_ids), self.file_path)
        except Exception as e:
            logger.error("Error writing to %s: %s", self.file_path, e)
