"""SyncService — placeholder interface for future cloud synchronization.

Establishes the architecture without implementing cloud providers.
All methods are either no-ops or raise NotImplementedError.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"


class SyncEntry:
    """Represents a single entity pending synchronization."""

    def __init__(self, entity_type: str, entity_id: str, action: str = "update"):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.action = action
        self.status = SyncStatus.PENDING
        self.timestamp = datetime.now(timezone.utc).isoformat()


class SyncService:
    """Placeholder sync service. No cloud implementation yet."""

    def __init__(self):
        self._queue: list[SyncEntry] = []

    def mark_dirty(self, entity_type: str, entity_id: str, action: str = "update") -> None:
        """Mark an entity as needing synchronization."""
        entry = SyncEntry(entity_type, entity_id, action)
        self._queue.append(entry)
        logger.info("Sync queued: %s %s (%s)", action, entity_type, entity_id)

    async def push(self) -> int:
        """Push pending changes to cloud. Not implemented."""
        raise NotImplementedError("Cloud sync not yet configured")

    async def pull(self) -> int:
        """Pull changes from cloud. Not implemented."""
        raise NotImplementedError("Cloud sync not yet configured")

    async def sync(self) -> dict:
        """Full bidirectional sync. Not implemented."""
        raise NotImplementedError("Cloud sync not yet configured")

    def resolve_conflicts(self, local: dict, remote: dict) -> dict:
        """Merge local and remote versions. Default: remote wins."""
        return remote

    def get_status(self) -> dict:
        """Return current sync queue status."""
        return {
            "queued": len(self._queue),
            "pending": sum(1 for e in self._queue if e.status == SyncStatus.PENDING),
            "synced": sum(1 for e in self._queue if e.status == SyncStatus.SYNCED),
        }

    def queue_size(self) -> int:
        return len(self._queue)
