"""
Download queue manager.

Async queue with configurable concurrency for parallel downloads.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from ..types import ProgressDict

if TYPE_CHECKING:
    from ..db import VideoStore


class QueueStatus(Enum):
    """Status of a queue item."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    """A single item in the download queue."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    url: str = ""
    platform: str = ""
    status: QueueStatus = QueueStatus.PENDING

    # Pre-fetched metadata
    title: str | None = None
    uploader: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None

    # Download options
    format_id: str | None = None
    output_dir: str | None = None
    cookies_browser: str | None = None

    # Progress
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed: float | None = None
    eta_seconds: int | None = None

    # Result
    video_id: int | None = None  # Database ID of downloaded video
    error_message: str | None = None
    local_path: str | None = None

    # Metadata preservation
    collection: str | None = None
    tags: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DownloadQueue:
    """
    Async download queue with concurrency control.

    Manages parallel downloads up to max_concurrent limit.
    """

    def __init__(
        self,
        max_concurrent: int = 32,
        store: VideoStore | None = None,
        on_progress: Callable[[QueueItem], None] | None = None,
        on_complete: Callable[[QueueItem], None] | None = None,
        on_error: Callable[[QueueItem, Exception], None] | None = None,
    ):
        """
        Initialize the download queue.

        Args:
            max_concurrent: Maximum parallel downloads
            store: Shared VideoStore instance (created if not provided)
            on_progress: Callback for progress updates
            on_complete: Callback when a download completes
            on_error: Callback when a download fails
        """
        self.max_concurrent = max_concurrent
        self._store = store
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self._items: dict[str, QueueItem] = {}
        self._pending: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._worker_task: asyncio.Task | None = None

    @property
    def items(self) -> list[QueueItem]:
        """Get all queue items."""
        return list(self._items.values())

    @property
    def pending_count(self) -> int:
        """Get count of pending items."""
        return sum(1 for item in self._items.values() if item.status == QueueStatus.PENDING)

    @property
    def active_count(self) -> int:
        """Get count of currently downloading items."""
        return sum(1 for item in self._items.values() if item.status == QueueStatus.DOWNLOADING)

    @property
    def complete_count(self) -> int:
        """Get count of completed items."""
        return sum(1 for item in self._items.values() if item.status == QueueStatus.COMPLETE)

    @property
    def failed_count(self) -> int:
        """Get count of failed items."""
        return sum(1 for item in self._items.values() if item.status == QueueStatus.FAILED)

    def add(
        self,
        url: str,
        platform: str = "",
        title: str | None = None,
        uploader: str | None = None,
        format_id: str | None = None,
        output_dir: str | None = None,
        cookies_browser: str | None = None,
        collection: str | None = None,
        tags: list[str] | None = None,
    ) -> QueueItem:
        """
        Add a URL to the download queue.

        Args:
            url: Video URL
            platform: Platform name (auto-detected if not provided)
            title: Pre-fetched title
            uploader: Pre-fetched uploader
            format_id: Specific format to download
            output_dir: Override output directory
            cookies_browser: Browser for cookies

        Returns:
            The created QueueItem
        """
        from ..config import detect_platform

        if not platform:
            platform = detect_platform(url)

        item = QueueItem(
            url=url,
            platform=platform,
            title=title,
            uploader=uploader,
            format_id=format_id,
            output_dir=output_dir,
            cookies_browser=cookies_browser,
            collection=collection,
            tags=tags or [],
        )

        self._items[item.id] = item
        self._pending.put_nowait(item.id)

        return item

    def add_batch(self, urls: list[str]) -> list[QueueItem]:
        """Add multiple URLs to the queue."""
        return [self.add(url) for url in urls]

    def remove(self, item_id: str) -> bool:
        """
        Remove an item from the queue.

        Only works for pending items. Cancels downloading items.
        """
        item = self._items.get(item_id)
        if not item:
            return False

        if item.status == QueueStatus.DOWNLOADING:
            # Cancel the running task
            task = self._tasks.get(item_id)
            if task:
                task.cancel()
            item.status = QueueStatus.CANCELLED
        elif item.status == QueueStatus.PENDING:
            item.status = QueueStatus.CANCELLED

        return True

    def remove_item(self, item_id: str) -> bool:
        """Cancel (if active) and fully remove an item from the queue."""
        self.remove(item_id)
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def clear_completed(self) -> int:
        """Remove all completed and failed items from the queue."""
        to_remove = [
            item_id
            for item_id, item in self._items.items()
            if item.status in (QueueStatus.COMPLETE, QueueStatus.FAILED, QueueStatus.CANCELLED)
        ]
        for item_id in to_remove:
            del self._items[item_id]
        return len(to_remove)

    def expire_stale(self, max_age_seconds: float = 300) -> int:
        """Remove finished items older than max_age_seconds."""
        from datetime import datetime, timedelta

        now = datetime.now()
        cutoff = timedelta(seconds=max_age_seconds)
        to_remove = [
            item_id
            for item_id, item in self._items.items()
            if item.completed_at and (now - item.completed_at) > cutoff
        ]
        for item_id in to_remove:
            del self._items[item_id]
        return len(to_remove)

    def get(self, item_id: str) -> QueueItem | None:
        """Get a queue item by ID."""
        return self._items.get(item_id)

    async def start(self):
        """Start processing the queue."""

        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())

    async def stop(self):
        """Stop processing the queue."""
        self._running = False

        # Cancel all running tasks
        for task in self._tasks.values():
            task.cancel()

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _process_queue(self):
        """Main queue processing loop."""

        while self._running:
            try:
                # Wait for an item with timeout
                try:
                    item_id = await asyncio.wait_for(self._pending.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                item = self._items.get(item_id)
                if not item or item.status != QueueStatus.PENDING:
                    continue

                # Acquire semaphore for concurrency control

                await self._semaphore.acquire()

                # Start download task
                task = asyncio.create_task(self._download_item(item))
                self._tasks[item_id] = task

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but keep processing
                print(f"Queue error: {e}")

    async def _download_item(self, item: QueueItem):
        """Download a single queue item."""

        try:
            item.status = QueueStatus.DOWNLOADING
            item.started_at = datetime.now()

            if self.on_progress:
                self.on_progress(item)

            # Import here to avoid circular imports
            from ..library.ingest import ingest_video

            # Use shared store, or create one if not provided
            if self._store is not None:
                store = self._store
            else:
                from ..config import DB_PATH
                from ..db import VideoStore

                store = VideoStore(DB_PATH)

            def progress_callback(d: ProgressDict):
                item.downloaded_bytes = d.get("downloaded_bytes", 0)
                item.total_bytes = d.get("total_bytes")
                item.speed = d.get("speed")
                item.eta_seconds = d.get("eta")

                if item.total_bytes and item.total_bytes > 0:
                    item.progress_percent = (item.downloaded_bytes / item.total_bytes) * 100

                if self.on_progress:
                    self.on_progress(item)

            # Run the actual download
            video = await ingest_video(
                url=item.url,
                store=store,
                output_dir=item.output_dir,
                format_id=item.format_id,
                cookies_from=item.cookies_browser,
                collection=item.collection,
                tags=item.tags,
                on_progress=progress_callback,
            )

            # Success
            item.status = QueueStatus.COMPLETE
            item.progress_percent = 100.0
            item.completed_at = datetime.now()
            item.video_id = video.id
            item.local_path = video.local_path
            item.title = video.title
            item.uploader = video.uploader

            if self.on_complete:
                self.on_complete(item)

        except asyncio.CancelledError:
            item.status = QueueStatus.CANCELLED
            raise
        except Exception as e:
            item.status = QueueStatus.FAILED
            item.error_message = str(e)
            item.completed_at = datetime.now()

            if self.on_error:
                self.on_error(item, e)
        finally:
            # Release semaphore
            self._semaphore.release()

            # Remove from active tasks
            self._tasks.pop(item.id, None)

            if self.on_progress:
                self.on_progress(item)
