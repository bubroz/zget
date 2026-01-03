"""
Download queue manager.

Async queue with configurable concurrency for parallel downloads.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional
from uuid import uuid4


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
    title: Optional[str] = None
    uploader: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None

    # Download options
    format_id: Optional[str] = None
    output_dir: Optional[str] = None
    cookies_browser: Optional[str] = None

    # Progress
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta_seconds: Optional[int] = None

    # Result
    video_id: Optional[int] = None  # Database ID of downloaded video
    error_message: Optional[str] = None
    local_path: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DownloadQueue:
    """
    Async download queue with concurrency control.

    Manages parallel downloads up to max_concurrent limit.
    """

    def __init__(
        self,
        max_concurrent: int = 32,
        on_progress: Callable[[QueueItem], None] | None = None,
        on_complete: Callable[[QueueItem], None] | None = None,
        on_error: Callable[[QueueItem, Exception], None] | None = None,
    ):
        """
        Initialize the download queue.

        Args:
            max_concurrent: Maximum parallel downloads
            on_progress: Callback for progress updates
            on_complete: Callback when a download completes
            on_error: Callback when a download fails
        """
        self.max_concurrent = max_concurrent
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self._items: dict[str, QueueItem] = {}
        self._pending: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

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

    def get(self, item_id: str) -> Optional[QueueItem]:
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
            from ..db import VideoStore
            from ..config import DB_PATH

            store = VideoStore(DB_PATH)

            def progress_callback(d: dict):
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
