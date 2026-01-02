"""
Unified screen.

Single screen combining download interface and video library.
"""

import re
from datetime import datetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Rule,
    Static,
)

from ...config import detect_platform, PLATFORM_DISPLAY
from ...db import Video
from ...queue import DownloadQueue, QueueItem, QueueStatus


class VideoDetailsModal(ModalScreen):
    """Modal screen showing full video details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
        Binding("t", "open_thumbnail", "Thumbnail"),
    ]

    DEFAULT_CSS = """
    VideoDetailsModal {
        align: center middle;
    }
    
    VideoDetailsModal > Container {
        width: 90%;
        max-width: 120;
        height: auto;
        max-height: 85%;
        background: #1a1a1a;
        border: solid #ffb000;
        padding: 1 2;
    }
    
    VideoDetailsModal .details-title {
        text-style: bold;
        color: #ffb000;
        margin-bottom: 1;
    }
    
    VideoDetailsModal .details-content {
        color: #cccccc;
    }
    
    VideoDetailsModal .details-label {
        color: #666666;
    }
    
    VideoDetailsModal ScrollableContainer {
        height: auto;
        max-height: 100%;
    }
    """

    def __init__(self, video: Video):
        super().__init__()
        self.video = video

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Video Details", classes="details-title")
            yield Rule()
            with ScrollableContainer():
                yield Static(self._format_details(), markup=True, classes="details-content")
            yield Rule()
            yield Label("ESC close | T thumbnail", classes="details-label")

    def _format_details(self) -> str:
        """Format all video details."""
        video = self.video
        upload_date = video.upload_date.strftime("%Y-%m-%d") if video.upload_date else "Unknown"
        downloaded = (
            video.downloaded_at.strftime("%Y-%m-%d %H:%M") if video.downloaded_at else "Unknown"
        )
        size_bytes = video.file_size_bytes or 0
        if size_bytes >= 1024 * 1024 * 1024:
            size = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            size = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size = f"{size_bytes / 1024:.1f} KB"

        duration = "Unknown"
        if video.duration_seconds:
            hours, remainder = divmod(int(video.duration_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration = f"{minutes}:{seconds:02d}"

        views = f"{video.view_count:,}" if video.view_count else "—"
        likes = f"{video.like_count:,}" if video.like_count else "—"
        desc = video.description or "No description available"
        thumb_path = video.thumbnail_path or "Not available"

        return (
            f"[bold yellow]TITLE[/bold yellow]\n{video.title}\n\n"
            f"[bold yellow]URL[/bold yellow]\n[cyan underline]{video.url}[/cyan underline]\n\n"
            f"[dim]─── Channel ───────────────────────────────────────[/dim]\n"
            f"Platform: {video.platform.capitalize()}\n"
            f"Uploader: [bold]{video.uploader}[/bold]\n\n"
            f"[dim]─── Video Stats ───────────────────────────────────[/dim]\n"
            f"Duration: [bold]{duration}[/bold]  |  Views: {views}  |  Likes: {likes}\n"
            f"Resolution: {video.resolution or '—'}  |  Codec: {video.codec or '—'}\n\n"
            f"[dim]─── File Info ─────────────────────────────────────[/dim]\n"
            f"Size: {size}  |  Downloaded: {downloaded}  |  Uploaded: {upload_date}\n"
            f"Path: [dim]{video.local_path}[/dim]\n"
            f"Thumbnail: [dim]{thumb_path}[/dim]  [bold cyan][T][/bold cyan] to open\n\n"
            f"[dim]─── Description ───────────────────────────────────[/dim]\n"
            f"{desc}"
        )

    def action_open_thumbnail(self) -> None:
        """Open the thumbnail in system default image viewer."""
        import subprocess
        from pathlib import Path

        if not self.video.thumbnail_path:
            self.notify("No thumbnail available", severity="warning", timeout=2)
            return

        thumb_path = Path(self.video.thumbnail_path)
        if not thumb_path.exists():
            self.notify(f"Thumbnail not found", severity="error", timeout=3)
            return

        try:
            subprocess.run(["open", str(thumb_path)], check=True)
        except Exception:
            self.notify("Failed to open thumbnail", severity="error", timeout=3)


class UnifiedScreen(Screen):
    """Single unified screen with downloads and library."""

    BINDINGS = [
        Binding("d", "focus_input", "Download", priority=True),
        Binding("/", "focus_search", "Search"),
        Binding("ctrl+v", "paste", "Paste URL"),
        Binding("ctrl+l", "clear_completed", "Clear Done"),
        Binding("enter", "play_video", "Play", show=True),
        Binding("p", "play_video", "Play", show=False),
        Binding("o", "open_video_url", "Open URL"),
        Binding("i", "view_details", "Info"),
        Binding("c", "toggle_columns", "Columns"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("r", "goto_registry", "Registry"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "cancel_input", "Cancel"),
    ]

    SORT_OPTIONS = [
        (None, "Default", False),
        ("file_size_bytes", "Size ↓", True),
        ("duration_seconds", "Duration ↓", True),
        ("upload_date", "Date ↓", True),
    ]

    def __init__(self):
        super().__init__()
        self.queue = DownloadQueue(
            max_concurrent=32,
            on_progress=self._on_progress,
            on_complete=self._on_complete,
            on_error=self._on_error,
        )
        self._queue_rows: dict[str, int] = {}
        self._row_counter = 0
        self._videos: list[Video] = []
        self._selected_index: int = -1
        self._compact_mode: bool = False
        self._sort_index: int = 0

    def compose(self) -> ComposeResult:
        """Create unified layout."""
        yield Header()

        with Container(id="unified"):
            # Top bar: URL input + stats
            # Top Section: Logo + Input + Stats
            with Horizontal(id="top-section"):
                # Left: Logo Placeholder
                yield Static(
                    " [bold yellow]ZGET[/bold yellow]\n [dim]ARCHIVIST[/dim]", id="logo-placeholder"
                )

                # Right: Input and Stats
                with Vertical(id="top-right"):
                    yield Label("", id="stats-label")
                    yield Input(
                        placeholder="Paste URLs (comma/newline separated) • Press Enter to Download",
                        id="url-input",
                    )

            # Downloads section (collapsible)
            with Collapsible(title="Downloads", id="downloads-section", collapsed=True):
                yield DataTable(id="queue-table", cursor_type="row")

            # Library section
            with Horizontal(id="library-header"):
                yield Label("", id="library-info")
                yield Input(
                    placeholder="Search...",
                    id="search-input",
                )

            yield DataTable(id="library-table", cursor_type="row")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize both queue and library."""
        # Setup queue table
        queue_table = self.query_one("#queue-table", DataTable)
        queue_table.add_column("Status", width=6)
        queue_table.add_column("Platform", width=10)
        queue_table.add_column("Title")
        queue_table.add_column("Progress", width=8)
        queue_table.add_column("Speed", width=10)
        queue_table.add_column("ETA", width=6)

        # Setup library table
        self._setup_library_columns()
        self._load_videos()

        # Start queue
        await self.queue.start()
        self._update_stats()

        # Focus library table
        self.query_one("#library-table", DataTable).focus()

    def _setup_library_columns(self) -> None:
        """Set up library table columns."""
        table = self.query_one("#library-table", DataTable)
        table.clear(columns=True)
        table.zebra_stripes = True

        if self._compact_mode:
            table.add_column("Uploader", width=20)
            table.add_column("Title")
            table.add_column("Duration", width=8)
        else:
            table.add_column("Platform", width=10)
            table.add_column("Uploader", width=20)
            table.add_column("Title")
            table.add_column("Duration", width=8)
            table.add_column("Size", width=8)
            table.add_column("Uploaded", width=10)

    def _load_videos(self) -> None:
        """Load videos from database."""
        self._videos = self.app.store.get_recent(limit=200)
        self._populate_library()
        self._update_library_info(len(self._videos), is_search=False)

    def _search_videos(self, query: str) -> None:
        """Search videos."""
        self._videos = self.app.store.search(query, limit=200)
        self._populate_library()
        self._update_library_info(len(self._videos), is_search=True)

    def _populate_library(self) -> None:
        """Populate library table."""
        table = self.query_one("#library-table", DataTable)
        table.clear()

        for video in self._videos:
            # Don't truncate uploader, only strip emojis
            uploader = self._normalize(video.uploader or "Unknown", max_len=None)
            title = self._normalize(video.title or "Untitled", 70)
            duration = self._format_duration(video.duration_seconds)

            if self._compact_mode:
                table.add_row(uploader, title, duration)
            else:
                platform = self._format_platform(video.platform)
                size = self._format_size(video.file_size_bytes or 0)
                upload_date = video.upload_date.strftime("%Y-%m-%d") if video.upload_date else "--"
                table.add_row(platform, uploader, title, duration, size, upload_date)

    def _normalize(self, text: str, max_len: int | None = None) -> str:
        """Remove emojis and optionally truncate."""
        if not text:
            return ""
        emoji_pattern = re.compile(
            "[\U0001f1e0-\U0001f1ff\U0001f300-\U0001f5ff\U0001f600-\U0001f64f"
            "\U0001f680-\U0001f6ff\U0001f700-\U0001faff\U00002702-\U000027b0]+",
            flags=re.UNICODE,
        )
        cleaned = emoji_pattern.sub("", text).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if max_len and len(cleaned) > max_len:
            return cleaned[: max_len - 1] + "…"
        return cleaned

    def _format_platform(self, platform: str) -> str:
        """Format platform name for display using centralized mapping."""
        return PLATFORM_DISPLAY.get(platform, platform.capitalize())

    def _format_duration(self, seconds: float | None) -> str:
        if not seconds:
            return "--:--"
        minutes, secs = divmod(int(seconds), 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.0f}MB"
        else:
            return f"{size_bytes / 1024:.0f}KB"

    def _update_stats(self) -> None:
        """Update download queue stats."""
        try:
            stats_label = self.query_one("#stats-label", Label)
        except Exception:
            return

        pending = self.queue.pending_count
        active = self.queue.active_count

        # Format Queue Status
        if active > 0 or pending > 0:
            queue_status = f"Queue: {active} Active, {pending} Pending"
        else:
            queue_status = "Queue: Idle"

        try:
            rate_stats = self.app.store.get_download_rate_stats()
            today = rate_stats["today_count"]
            # week = rate_stats["week_count"]  # Week stats might be cluttering if identical to today
            # Let's just show Today for now as it's most relevant for rate limits
            today_size = self._format_size(rate_stats["today_size"])

            stats_label.update(f"{queue_status}  ║  Today: {today} ({today_size})")
        except Exception:
            stats_label.update(queue_status)

    def action_cancel_input(self) -> None:
        """Cancel input focus and return to library."""
        self.query_one("#url-input", Input).value = ""
        self.query_one("#library-table", DataTable).focus()

    def on_click(self, event) -> None:
        """Handle background clicks to blur input."""
        # If clicking outside input, focus library
        if not isinstance(event.widget, Input):
            self.query_one("#library-table", DataTable).focus()

    def _update_library_info(self, count: int, is_search: bool) -> None:
        """Update library header."""
        try:
            info_label = self.query_one("#library-info", Label)
            stats = self.app.store.get_stats()
            total_size = self._format_size(stats["total_size_bytes"])
            if is_search:
                info_label.update(f"{count} results | {total_size}")
            else:
                info_label.update(f"{count} videos | {total_size}")
        except Exception:
            pass

    # === Download Queue Methods ===

    def action_submit_url(self) -> None:
        """Add URL(s) to download queue."""
        url_input = self.query_one("#url-input", Input)
        text = url_input.value.strip()
        if not text:
            return

        # Parse multiple URLs
        urls = []
        for part in re.split(r"[,\n]+", text):
            url = part.strip()
            if self._is_valid_url(url):
                urls.append(url)

        if not urls:
            self.notify("No valid URLs found", severity="warning", timeout=2)
            return

        # Add to queue
        for url in urls:
            item = self.queue.add(url)
            self._add_queue_row(item)

        # Clear and blur input
        url_input.value = ""
        url_input.blur()

        # Expand downloads section
        try:
            self.query_one("#downloads-section", Collapsible).collapsed = False
        except Exception:
            pass

        self._update_stats()
        self.notify(f"Added {len(urls)} URL(s)", timeout=2)

    def _add_queue_row(self, item: QueueItem) -> None:
        """Add a row to queue table."""
        table = self.query_one("#queue-table", DataTable)
        platform = detect_platform(item.url) or "unknown"
        platform_display = self._format_platform(platform)
        title = item.title or item.url[:40]

        row_key = table.add_row("...", platform_display, title, "0%", "--", "--")
        self._queue_rows[item.id] = row_key
        self._row_counter += 1

    def _update_queue_row(self, item: QueueItem) -> None:
        """Update queue row with progress."""
        try:
            table = self.query_one("#queue-table", DataTable)
        except Exception:
            return

        row_key = self._queue_rows.get(item.id)
        if row_key is None:
            return

        status_map = {
            QueueStatus.PENDING: "...",
            QueueStatus.DOWNLOADING: ">>>",
            QueueStatus.COMPLETE: "OK",
            QueueStatus.FAILED: "ERR",
            QueueStatus.CANCELLED: "---",
        }
        status = status_map.get(item.status, "?")
        title = self._normalize(item.title or item.url[:40], 50)
        progress = f"{item.progress_percent:.0f}%" if item.progress_percent else "0%"
        speed = f"{item.speed / 1024 / 1024:.1f}MB/s" if item.speed else "--"
        eta = f"{item.eta_seconds // 60}:{item.eta_seconds % 60:02d}" if item.eta_seconds else "--"

        if item.status == QueueStatus.COMPLETE:
            progress = "Done"
            speed = "--"
            eta = "--"
        elif item.status == QueueStatus.FAILED:
            progress = "Failed"
            speed = "--"
            eta = "--"

        try:
            table.update_cell_at((row_key, 0), status)
            table.update_cell_at((row_key, 2), title)
            table.update_cell_at((row_key, 3), progress)
            table.update_cell_at((row_key, 4), speed)
            table.update_cell_at((row_key, 5), eta)
        except Exception:
            pass

    def _on_progress(self, item: QueueItem) -> None:
        """Handle progress updates (called from async context)."""
        # Use call_later since we're in the same event loop, not a different thread
        self.app.call_later(self._update_queue_row, item)
        self.app.call_later(self._update_stats)

    def _on_complete(self, item: QueueItem) -> None:
        """Handle download completion (called from async context)."""
        self.app.call_later(self._update_queue_row, item)
        self.app.call_later(self._update_stats)
        self.app.call_later(self._load_videos)
        self.app.call_later(self.notify, f"Complete: {item.title or 'Video'}", timeout=3)

    def _on_error(self, item: QueueItem, error: Exception) -> None:
        """Handle download errors (called from async context)."""
        self.app.call_later(self._update_queue_row, item)
        self.app.call_later(self._update_stats)
        self.app.call_later(
            self.notify, f"Failed: {item.title or item.url[:30]}", severity="error", timeout=5
        )

    def _is_valid_url(self, url: str) -> bool:
        return bool(url) and url.startswith(("http://", "https://", "www."))

    # === Library Methods ===

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self._search_videos(query)
            else:
                self._load_videos()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            self.action_submit_url()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key or Double Click on library table."""
        if event.data_table.id == "library-table":
            self._selected_index = event.cursor_row
            self.action_play_video()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "library-table":
            self._selected_index = event.cursor_row

    def action_focus_input(self) -> None:
        self.query_one("#url-input", Input).focus()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_toggle_columns(self) -> None:
        self._compact_mode = not self._compact_mode
        self._setup_library_columns()
        self._populate_library()
        self.notify("Compact" if self._compact_mode else "Full", timeout=1)

    def action_cycle_sort(self) -> None:
        self._sort_index = (self._sort_index + 1) % len(self.SORT_OPTIONS)
        field, display_name, reverse = self.SORT_OPTIONS[self._sort_index]
        if field is None:
            self._load_videos()
        else:
            self._videos.sort(key=lambda v: getattr(v, field) or 0, reverse=reverse)
            self._populate_library()
        self.notify(f"Sort: {display_name}", timeout=1)

    def action_refresh(self) -> None:
        query = self.query_one("#search-input", Input).value.strip()
        if query:
            self._search_videos(query)
        else:
            self._load_videos()
        self._update_stats()
        self.notify("Refreshed", timeout=1)

    def action_play_video(self) -> None:
        import subprocess
        from pathlib import Path

        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]
            if video.local_path and Path(video.local_path).exists():
                subprocess.run(["open", video.local_path])
            else:
                self.notify("Video file not found", severity="error", timeout=2)

    def action_view_details(self) -> None:
        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]
            self.app.push_screen(VideoDetailsModal(video))

    def action_open_video_url(self) -> None:
        import webbrowser

        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]
            webbrowser.open(video.url)
            self.notify("Opening URL...", timeout=1)

    def action_clear_completed(self) -> None:
        """Clear completed downloads from queue."""
        try:
            table = self.query_one("#queue-table", DataTable)
        except Exception:
            return

        items_to_remove = [
            item_id
            for item_id, row_key in self._queue_rows.items()
            if self.queue.get(item_id)
            and self.queue.get(item_id).status
            in (QueueStatus.COMPLETE, QueueStatus.FAILED, QueueStatus.CANCELLED)
        ]

        for item_id in items_to_remove:
            row_key = self._queue_rows.pop(item_id, None)
            if row_key is not None:
                try:
                    table.remove_row(row_key)
                except Exception:
                    pass
            self.queue.remove(item_id)

        self._update_stats()

    def action_paste(self) -> None:
        """Paste from clipboard."""
        try:
            import pyperclip

            text = pyperclip.paste()
            if text:
                url_input = self.query_one("#url-input", Input)
                url_input.value = text.strip()
                url_input.focus()
        except Exception:
            self.notify("Could not access clipboard", severity="warning")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_goto_registry(self) -> None:
        """Open the site registry."""
        self.app.push_screen("registry")
