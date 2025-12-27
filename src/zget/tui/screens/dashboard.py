"""
Dashboard screen.

Main download interface with URL input and queue display.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Rule,
)

from ...config import detect_platform
from ...queue import DownloadQueue, QueueItem, QueueStatus


class DashboardScreen(Screen):
    """Main download dashboard with URL input and queue."""

    BINDINGS = [
        Binding("d", "focus_input", "Download", show=True, priority=True),
        Binding("l", "goto_library", "Library", show=True, priority=True),
        Binding("ctrl+v", "paste", "Paste URL"),
        Binding("ctrl+l", "clear_completed", "Clear Done"),
        Binding("enter", "submit_url", "Add URL", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.queue = DownloadQueue(
            max_concurrent=32,
            on_progress=self._on_progress,
            on_complete=self._on_complete,
            on_error=self._on_error,
        )
        self._queue_rows: dict[str, int] = {}  # item_id -> row_key
        self._row_counter = 0

    def compose(self) -> ComposeResult:
        """Create the dashboard layout."""
        yield Header()

        with Container(id="dashboard"):
            # URL Input Section
            with Horizontal(id="input-section"):
                yield Input(
                    placeholder="Paste URL(s) - multiple URLs separated by newlines or commas",
                    id="url-input",
                )
                yield Button("Download", id="add-btn", variant="primary")
                yield Button("Clear Done", id="clear-btn")

            # Stats Row
            with Horizontal(id="stats-row"):
                yield Label("", id="stats-label")

            # Queue Table
            yield DataTable(id="queue-table", cursor_type="row")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the queue and table."""
        # Setup table columns
        table = self.query_one("#queue-table", DataTable)
        table.add_column("Status", width=8)
        table.add_column("Platform", width=10)
        table.add_column("Title")  # Flexible
        table.add_column("Progress", width=10)
        table.add_column("Speed", width=12)
        table.add_column("ETA", width=8)

        await self.queue.start()
        self._update_stats()

        # Blur input so keybindings work immediately
        url_input = self.query_one("#url-input", Input)
        url_input.blur()

    async def on_unmount(self) -> None:
        """Called when screen is unmounted (navigated away)."""
        # NOTE: We do NOT stop the queue here!
        # Downloads should continue in background when user navigates to Library
        # Queue will stop when app exits via action_quit or window close
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-btn":
            self.action_submit_url()
        elif event.button.id == "clear-btn":
            self.action_clear_completed()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        if event.input.id == "url-input":
            self.action_submit_url()

    def on_key(self, event) -> None:
        """Handle key events directly to ensure navigation works."""
        # Check if input is focused - if so, let it handle the key
        try:
            url_input = self.query_one("#url-input", Input)
            if url_input.has_focus:
                return  # Let input handle it
        except Exception:
            pass

        # Handle navigation keys directly
        if event.key == "l":
            event.prevent_default()
            event.stop()
            self.action_goto_library()
        elif event.key == "d":
            event.prevent_default()
            event.stop()
            self.action_focus_input()

    def action_focus_input(self) -> None:
        """Focus the URL input field."""
        url_input = self.query_one("#url-input", Input)
        url_input.focus()

    def action_goto_library(self) -> None:
        """Navigate to Library screen."""
        self.app.action_goto_library()

    def action_submit_url(self) -> None:
        """Add URL(s) from input to queue. Handles multiple URLs."""
        import re

        url_input = self.query_one("#url-input", Input)
        text = url_input.value.strip()

        if not text:
            self.notify("Please enter a URL", severity="warning")
            return

        # Split by newlines, commas, or whitespace
        potential_urls = re.split(r"[\n,\s]+", text)
        valid_urls = [u.strip() for u in potential_urls if self._is_valid_url(u.strip())]

        if not valid_urls:
            self.notify("No valid URLs found", severity="error")
            return

        # Add all valid URLs to queue
        for url in valid_urls:
            item = self.queue.add(url)
            self._add_queue_row(item)

        # Clear input and blur so keybindings work
        url_input.value = ""
        url_input.blur()  # IMPORTANT: blur so L/D keybindings work

        self._update_stats()

        if len(valid_urls) == 1:
            self.notify(f"Added: {valid_urls[0][:50]}...", timeout=2)
        else:
            self.notify(f"Added {len(valid_urls)} URLs to queue", timeout=2)

    def action_paste(self) -> None:
        """Paste URL from clipboard."""
        try:
            import pyperclip

            text = pyperclip.paste()
            if text:
                url_input = self.query_one("#url-input", Input)
                url_input.value = text.strip()
                url_input.focus()
        except Exception:
            self.notify("Could not access clipboard", severity="warning")

    def action_clear_completed(self) -> None:
        """Clear completed and failed items from queue."""
        try:
            table = self.query_one("#queue-table", DataTable)
        except Exception:
            return  # Not on dashboard screen

        # Find rows to remove
        rows_to_remove = []
        for item_id, row_key in list(self._queue_rows.items()):
            item = self.queue.get(item_id)  # Fixed: was get_item
            if item and item.status in (
                QueueStatus.COMPLETE,
                QueueStatus.FAILED,
                QueueStatus.CANCELLED,
            ):
                rows_to_remove.append((item_id, row_key))

        # Remove from table and tracking
        for item_id, row_key in rows_to_remove:
            try:
                table.remove_row(row_key)
            except Exception:
                pass
            del self._queue_rows[item_id]

        # Clear from queue
        count = self.queue.clear_completed()
        self._update_stats()

        if count > 0:
            self.notify(f"Cleared {count} items", timeout=2)

    def _add_queue_row(self, item: QueueItem) -> None:
        """Add a row to the queue table."""
        table = self.query_one("#queue-table", DataTable)

        status = self._format_status(item.status)
        platform = item.platform.capitalize() if item.platform else "—"
        title = item.title or item.url[:50]
        progress = "Pending"
        speed = "—"
        eta = "—"

        row_key = table.add_row(status, platform, title, progress, speed, eta)
        self._queue_rows[item.id] = row_key

    def _update_queue_row(self, item: QueueItem) -> None:
        """Update an existing queue row."""
        try:
            table = self.query_one("#queue-table", DataTable)
        except Exception:
            return  # Not on dashboard screen - download continues in background

        row_key = self._queue_rows.get(item.id)

        if row_key is None:
            return

        status = self._format_status(item.status)
        platform = item.platform.capitalize() if item.platform else "—"
        title = item.title or item.url[:50]

        if item.status == QueueStatus.DOWNLOADING:
            progress = f"{item.progress_percent:.1f}%"
            speed = self._format_speed(item.speed)
            eta = self._format_eta(item.eta_seconds)
        elif item.status == QueueStatus.COMPLETE:
            progress = "Done"
            speed = "—"
            eta = "—"
        elif item.status == QueueStatus.FAILED:
            progress = "Failed"
            speed = "—"
            eta = "—"
        else:
            progress = "Pending"
            speed = "—"
            eta = "—"

        # Update all cells in the row using coordinate-based update
        try:
            # Get the row index from the row key
            row_index = table.get_row_index(row_key)

            # Update each column by index (0=Status, 1=Platform, 2=Title, 3=Progress, 4=Speed, 5=ETA)
            table.update_cell_at((row_index, 0), status)
            table.update_cell_at((row_index, 1), platform)
            table.update_cell_at((row_index, 2), title)
            table.update_cell_at((row_index, 3), progress)
            table.update_cell_at((row_index, 4), speed)
            table.update_cell_at((row_index, 5), eta)
        except Exception as e:
            pass  # Row might have been removed

    def _format_status(self, status: QueueStatus) -> str:
        """Format status for display."""
        icons = {
            QueueStatus.PENDING: "...",
            QueueStatus.DOWNLOADING: ">>>",
            QueueStatus.COMPLETE: "OK",
            QueueStatus.FAILED: "ERR",
            QueueStatus.CANCELLED: "---",
        }
        return icons.get(status, "?")

    def _format_speed(self, speed: float | None) -> str:
        if not speed:
            return "—"
        if speed > 1_000_000:
            return f"{speed / 1_000_000:.1f} MB/s"
        elif speed > 1_000:
            return f"{speed / 1_000:.1f} KB/s"
        else:
            return f"{speed:.0f} B/s"

    def _format_eta(self, eta: int | None) -> str:
        if not eta:
            return "—"
        minutes, seconds = divmod(eta, 60)
        if minutes > 60:
            hours, minutes = divmod(minutes, 60)
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _on_progress(self, item: QueueItem) -> None:
        """Handle progress update from queue."""
        self._update_queue_row(item)
        self._update_stats()

    def _on_complete(self, item: QueueItem) -> None:
        """Handle download completion."""
        self._update_queue_row(item)
        self.notify(f"Downloaded: {item.title or item.url[:40]}", timeout=3)
        self._update_stats()

    def _on_error(self, item: QueueItem, error: Exception) -> None:
        """Handle download error."""
        self._update_queue_row(item)
        self.notify(f"Failed: {item.title or item.url[:40]}", severity="error", timeout=5)
        self._update_stats()

    def _update_stats(self) -> None:
        """Update stats display with queue status and rate limits."""
        try:
            stats_label = self.query_one("#stats-label", Label)
        except Exception:
            return  # Not on dashboard screen

        pending = self.queue.pending_count
        active = self.queue.active_count
        complete = self.queue.complete_count
        failed = self.queue.failed_count

        # Get rate stats from database
        try:
            rate_stats = self.app.store.get_download_rate_stats()
            today_count = rate_stats["today_count"]
            week_count = rate_stats["week_count"]
            today_size = self._format_size(rate_stats["today_size"])
            week_size = self._format_size(rate_stats["week_size"])
            rate_info = (
                f"  ║  Today: {today_count} ({today_size})  |  Week: {week_count} ({week_size})"
            )
        except Exception:
            rate_info = ""

        stats_label.update(
            f"Pending: {pending}  |  Active: {active}  |  Complete: {complete}  |  Failed: {failed}{rate_info}"
        )

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for stats display."""
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.0f}MB"
        else:
            return f"{size_bytes / 1024:.0f}KB"

    def _is_valid_url(self, url: str) -> bool:
        """Check if a string looks like a valid URL."""
        if not url:
            return False
        return url.startswith(("http://", "https://", "www."))
