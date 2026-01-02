"""
Library screen.

Browse and search downloaded videos.
"""

import re
from datetime import datetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Rule,
    Static,
)

from ...db import Video
from ...config import PLATFORM_DISPLAY


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
    
    VideoDetailsModal .details-value {
        color: #ffffff;
    }
    
    VideoDetailsModal ScrollableContainer {
        height: auto;
        max-height: 100%;
    }
    
    VideoDetailsModal Scrollbar {
        background: #1a1a1a;
        color: #333333;
    }
    
    VideoDetailsModal ScrollbarSlider {
        color: #666666;
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
            yield Label(
                "ESC close | Y copy URL | U channel | O video | Cmd+click URLs",
                classes="details-label",
            )

    def _format_details(self) -> str:
        """Format all video details."""
        video = self.video

        upload_date = video.upload_date.strftime("%Y-%m-%d") if video.upload_date else "Unknown"
        downloaded = (
            video.downloaded_at.strftime("%Y-%m-%d %H:%M") if video.downloaded_at else "Unknown"
        )

        # Format file size
        size_bytes = video.file_size_bytes or 0
        if size_bytes >= 1024 * 1024 * 1024:
            size = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            size = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size = f"{size_bytes / 1024:.1f} KB"

        # Format duration
        if video.duration_seconds:
            hours, remainder = divmod(int(video.duration_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration = f"{minutes}:{seconds:02d}"
        else:
            duration = "Unknown"

        # Format view/like counts
        views = f"{video.view_count:,}" if video.view_count else "—"
        likes = f"{video.like_count:,}" if video.like_count else "—"

        # Build channel URL based on platform
        channel_url = self._get_channel_url()

        # Full description (not truncated)
        desc = video.description or "No description available"

        # Use Rich markup for URLs (cyan, underline)
        url_styled = f"[cyan underline]{video.url}[/cyan underline]"
        channel_styled = (
            f"[cyan underline]{channel_url}[/cyan underline]" if channel_url != "N/A" else "N/A"
        )
        path_styled = f"[dim]{video.local_path}[/dim]"

        # Thumbnail path
        thumb_path = video.thumbnail_path or "Not available"
        thumb_styled = f"[dim]{thumb_path}[/dim]"

        return (
            f"[bold yellow]TITLE[/bold yellow]\n{video.title}\n\n"
            f"[bold yellow]URL[/bold yellow]\n{url_styled}\n\n"
            f"[dim]─── Channel ───────────────────────────────────────[/dim]\n"
            f"Platform: {video.platform.capitalize()}\n"
            f"Uploader: [bold]{video.uploader}[/bold]\n"
            f"Channel: {channel_styled}\n\n"
            f"[dim]─── Video Stats ───────────────────────────────────[/dim]\n"
            f"Duration: [bold]{duration}[/bold]  |  Views: {views}  |  Likes: {likes}\n"
            f"Resolution: {video.resolution or '—'}  |  Codec: {video.codec or '—'}\n\n"
            f"[dim]─── File Info ─────────────────────────────────────[/dim]\n"
            f"Size: {size}  |  Downloaded: {downloaded}  |  Uploaded: {upload_date}\n"
            f"Path: {path_styled}\n"
            f"Thumbnail: {thumb_styled}  [bold cyan][T][/bold cyan] to open\n\n"
            f"[dim]─── Description ───────────────────────────────────[/dim]\n"
            f"{desc}"
        )

    def _get_channel_url(self) -> str:
        """Build channel URL based on platform."""
        video = self.video
        platform = video.platform.lower()

        if platform == "youtube":
            if video.uploader_id:
                if video.uploader_id.startswith("UC"):
                    return f"https://www.youtube.com/channel/{video.uploader_id}"
                elif video.uploader_id.startswith("@"):
                    return f"https://www.youtube.com/{video.uploader_id}"
                else:
                    return f"https://www.youtube.com/@{video.uploader_id}"
        elif platform == "twitter":
            if video.uploader_id:
                return f"https://x.com/{video.uploader_id}"
        elif platform == "tiktok":
            if video.uploader_id:
                return f"https://www.tiktok.com/@{video.uploader_id}"
        elif platform == "instagram":
            if video.uploader_id:
                return f"https://www.instagram.com/{video.uploader_id}"

        return "N/A"

    def action_open_thumbnail(self) -> None:
        """Open the thumbnail in system default image viewer."""
        import subprocess
        from pathlib import Path

        if not self.video.thumbnail_path:
            self.notify("No thumbnail available", severity="warning", timeout=2)
            return

        thumb_path = Path(self.video.thumbnail_path)
        if not thumb_path.exists():
            self.notify(f"Thumbnail not found:\n{thumb_path}", severity="error", timeout=3)
            return

        try:
            subprocess.run(["open", str(thumb_path)], check=True)
            self.notify("Opening thumbnail...", timeout=1)
        except Exception as e:
            self.notify(f"Failed to open thumbnail: {e}", severity="error", timeout=3)


class LibraryScreen(Screen):
    """Browse and search downloaded videos."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("/", "focus_search", "Search"),
        Binding("enter", "play_video", "Play", show=True),
        Binding("p", "play_video", "Play", show=False),
        Binding("o", "open_video_url", "Open URL"),
        Binding("u", "open_channel", "Channel"),
        Binding("y", "copy_url", "Copy URL"),
        Binding("t", "toggle_tor", "Tor"),
        Binding("i", "view_details", "Info"),
        Binding("c", "toggle_columns", "Columns"),
        Binding("r", "refresh", "Refresh"),
        Binding("e", "export", "Export JSON"),
        Binding("d", "goto_dashboard", "Download"),
        Binding("l", "goto_library", "Library"),
        Binding("s", "cycle_sort", "Sort"),
    ]

    # Sort options: field name, display name, reverse flag
    SORT_OPTIONS = [
        (None, "Default", False),  # Original order (by download date desc)
        ("file_size_bytes", "Size ↓", True),  # Largest first
        ("duration_seconds", "Duration ↓", True),  # Longest first
        ("upload_date", "Date ↓", True),  # Newest first
    ]

    def __init__(self):
        super().__init__()
        self._videos: list[Video] = []
        self._selected_index: int = -1
        self._compact_mode: bool = False  # Toggle for column display
        self._tor_mode: bool = False  # Toggle for Tor browser
        self._sort_index: int = 0  # Index into SORT_OPTIONS

    def compose(self) -> ComposeResult:
        """Create the library layout."""
        yield Header()

        with Container(id="library"):
            # Header with stats on left, search on right
            with Horizontal(id="search-section", classes="search-container"):
                yield Label("", id="library-info", classes="library-info")
                yield Input(
                    placeholder="Search videos... (title, uploader, tags)",
                    id="search-input",
                )

            # Video Table - full height
            yield DataTable(id="video-table", cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the library view."""
        table = self.query_one("#video-table", DataTable)
        table.zebra_stripes = True

        self._setup_columns()
        self._load_videos()
        self._update_stats()

        # Focus the table by default so arrow keys work immediately
        table.focus()

    def _setup_columns(self) -> None:
        """Set up table columns based on current mode."""
        table = self.query_one("#video-table", DataTable)
        table.clear(columns=True)

        if self._compact_mode:
            # Compact: just the essentials
            table.add_column("Uploader", width=20)
            table.add_column("Title")  # Flexible
            table.add_column("Duration", width=9)
        else:
            # Full: all columns
            table.add_column("Platform", width=10)
            table.add_column("Uploader", width=20)
            table.add_column("Title")  # Flexible
            table.add_column("Duration", width=8)
            table.add_column("Size", width=8)
            table.add_column("Uploaded", width=10)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self._search_videos(query)
            else:
                self._load_videos()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or double-click).

        RowSelected fires on Enter key press or double-click, not single click.
        Single click fires RowHighlighted which just tracks selection.
        """
        self._selected_index = event.cursor_row
        self.action_play_video()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle cursor movement - track selected row."""
        self._selected_index = event.cursor_row

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def action_refresh(self) -> None:
        """Refresh the video list."""
        query = self.query_one("#search-input", Input).value.strip()
        if query:
            self._search_videos(query)
        else:
            self._load_videos()
        self._update_stats()
        self.notify("Library refreshed", timeout=2)

    def action_cycle_sort(self) -> None:
        """Cycle through sort options."""
        self._sort_index = (self._sort_index + 1) % len(self.SORT_OPTIONS)
        field, display_name, reverse = self.SORT_OPTIONS[self._sort_index]

        if field is None:
            # Default sort - reload from database
            self._load_videos()
        else:
            # Sort the current video list
            self._videos.sort(key=lambda v: getattr(v, field) or 0, reverse=reverse)
            self._populate_table()

        self.notify(f"Sort: {display_name}", timeout=1)

    def action_goto_dashboard(self) -> None:
        """Switch to dashboard screen."""
        self.app.action_goto_dashboard()

    def action_goto_library(self) -> None:
        """Already on library - no-op."""
        pass

    def action_toggle_columns(self) -> None:
        """Toggle between compact and full column modes."""
        self._compact_mode = not self._compact_mode
        self._setup_columns()
        self._populate_table()
        mode_name = "Compact" if self._compact_mode else "Full"
        self.notify(f"{mode_name} view", timeout=2)

    def action_export(self) -> None:
        """Export library to JSON."""
        from ...library.export import export_library_json_sync
        from ...config import EXPORTS_DIR

        export_path = (
            EXPORTS_DIR / f"library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        try:
            count = export_library_json_sync(
                store=self.app.store,
                export_path=export_path,
                include_raw=False,
            )
            self.notify(f"Exported {count} videos to:\n{export_path}")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def action_view_details(self) -> None:
        """View selected video details in a modal screen."""
        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]
            self.app.push_screen(VideoDetailsModal(video))
        else:
            self.notify("No video selected", severity="warning", timeout=2)

    def action_play_video(self) -> None:
        """Play the selected video in the system default player."""
        import subprocess
        from pathlib import Path

        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]

            if not video.local_path:
                self.notify("No local file path for this video", severity="warning")
                return

            video_path = Path(video.local_path)
            if not video_path.exists():
                self.notify(f"Video file not found:\n{video_path}", severity="error")
                return

            try:
                # macOS: use 'open' command
                subprocess.Popen(["open", str(video_path)])
                self.notify(f"Playing: {video.title[:40]}...", timeout=2)
            except Exception as e:
                self.notify(f"Could not open video: {e}", severity="error")
        else:
            self.notify("No video selected", severity="warning")

    def action_copy_url(self) -> None:
        """Copy the video URL to clipboard."""
        import subprocess

        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]

            if video.url:
                try:
                    # macOS: use pbcopy
                    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    process.communicate(video.url.encode("utf-8"))
                    self.notify(f"Copied: {video.url[:50]}...", timeout=2)
                except Exception as e:
                    self.notify(f"Could not copy: {e}", severity="error")
            else:
                self.notify("No URL for this video", severity="warning")
        else:
            self.notify("No video selected", severity="warning")

    def action_open_channel(self) -> None:
        """Open the uploader's channel/profile page in browser."""
        import subprocess
        import webbrowser

        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]

            # Build channel URL based on platform
            channel_url = None
            platform = video.platform.lower()

            if platform == "youtube":
                # YouTube channel - use uploader_id if available
                if video.uploader_id:
                    if video.uploader_id.startswith("UC"):
                        channel_url = f"https://www.youtube.com/channel/{video.uploader_id}"
                    elif video.uploader_id.startswith("@"):
                        channel_url = f"https://www.youtube.com/{video.uploader_id}"
                    else:
                        channel_url = f"https://www.youtube.com/@{video.uploader_id}"
                else:
                    # Fallback: search for uploader
                    channel_url = f"https://www.youtube.com/results?search_query={video.uploader}"

            elif platform == "twitter":
                # Twitter/X - extract username from uploader or URL
                if video.uploader_id:
                    channel_url = f"https://x.com/{video.uploader_id}"
                elif "@" in video.url:
                    # Parse from URL like https://x.com/username/status/...
                    parts = video.url.split("/")
                    for i, part in enumerate(parts):
                        if part in ["x.com", "twitter.com"] and i + 1 < len(parts):
                            username = parts[i + 1]
                            channel_url = f"https://x.com/{username}"
                            break

            elif platform == "tiktok":
                if video.uploader_id:
                    channel_url = f"https://www.tiktok.com/@{video.uploader_id}"

            elif platform == "instagram":
                if video.uploader_id:
                    channel_url = f"https://www.instagram.com/{video.uploader_id}"

            if channel_url:
                try:
                    self._open_url(channel_url)
                    tor_label = " [Tor]" if self._tor_mode else ""
                    self.notify(f"Opening{tor_label}: {video.uploader[:20]}...", timeout=2)
                except Exception as e:
                    self.notify(f"Could not open browser: {e}", severity="error")
            else:
                self.notify(
                    f"Can't find channel URL for {video.uploader}", severity="warning", timeout=3
                )
        else:
            self.notify("No video selected", severity="warning", timeout=2)

    def action_open_video_url(self) -> None:
        """Open the original video URL in browser."""
        if 0 <= self._selected_index < len(self._videos):
            video = self._videos[self._selected_index]

            if video.url:
                try:
                    self._open_url(video.url)
                    tor_label = " [Tor]" if self._tor_mode else ""
                    self.notify(f"Opening URL{tor_label}: {video.title[:30]}...", timeout=2)
                except Exception as e:
                    self.notify(f"Could not open browser: {e}", severity="error")
            else:
                self.notify("No URL stored for this video", severity="warning", timeout=2)
        else:
            self.notify("No video selected", severity="warning", timeout=2)

    def action_toggle_tor(self) -> None:
        """Toggle Tor mode for browser opening."""
        self._tor_mode = not self._tor_mode
        status = "ON" if self._tor_mode else "OFF"
        self.notify(f"Tor mode: {status}", timeout=2)

    def _open_url(self, url: str) -> None:
        """Open a URL in the configured browser."""
        import subprocess
        import webbrowser
        from ...config import BROWSER_APP, BROWSER_PROFILE

        if BROWSER_APP == "brave":
            brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            cmd = [brave_path]

            if self._tor_mode:
                # Use Tor window
                cmd.append("--tor")
            elif BROWSER_PROFILE and BROWSER_PROFILE != "Default":
                # Only specify profile if it's not the default
                cmd.extend(["--profile-directory", BROWSER_PROFILE])

            cmd.append(url)
            subprocess.Popen(cmd)
        elif BROWSER_APP == "chrome":
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            cmd = [chrome_path]
            if BROWSER_PROFILE and BROWSER_PROFILE != "Default":
                cmd.extend(["--profile-directory", BROWSER_PROFILE])
            cmd.append(url)
            subprocess.Popen(cmd)
        elif BROWSER_APP == "safari":
            subprocess.Popen(["open", "-a", "Safari", url])
        elif BROWSER_APP == "firefox":
            subprocess.Popen(["open", "-a", "Firefox", url])
        else:
            # Default: use system default browser
            webbrowser.open(url)

    def action_go_back(self) -> None:
        """Go back to dashboard screen."""
        self.app.switch_screen("dashboard")

    def _load_videos(self) -> None:
        """Load recent videos from database."""
        self._videos = self.app.store.get_recent(limit=200)
        self._populate_table()
        self._update_info_label(len(self._videos), is_search=False)

    def _search_videos(self, query: str) -> None:
        """Search videos by query."""
        self._videos = self.app.store.search(query, limit=200)
        self._populate_table()
        self._update_info_label(len(self._videos), is_search=True)

    def _populate_table(self) -> None:
        """Populate the data table with videos."""
        table = self.query_one("#video-table", DataTable)
        table.clear()

        for video in self._videos:
            # Normalize for display: strip emojis and truncate
            uploader = self._normalize_for_display(video.uploader or "Unknown", max_len=20)
            title = self._normalize_for_display(video.title or "Untitled", max_len=70)
            duration = self._format_duration(video.duration_seconds)

            if self._compact_mode:
                # Compact: Uploader, Title, Duration only
                table.add_row(uploader, title, duration)
            else:
                # Full: all columns
                platform_display = self._format_platform(video.platform)
                size = self._format_size(video.file_size_bytes or 0)
                upload_date = video.upload_date.strftime("%Y-%m-%d") if video.upload_date else "--"

                table.add_row(
                    platform_display,
                    uploader,
                    title,
                    duration,
                    size,
                    upload_date,
                )

    def _update_stats(self) -> None:
        """Update library statistics in the info label."""
        stats = self.app.store.get_stats()
        self._update_info_label(stats["total_videos"], is_search=False)

    def _update_info_label(self, count: int, is_search: bool) -> None:
        """Update the combined info label with rate stats."""
        stats = self.app.store.get_stats()
        total_size = self._format_size(stats["total_size_bytes"])

        # Get rate stats
        try:
            rate_stats = self.app.store.get_download_rate_stats()
            today_count = rate_stats["today_count"]
            week_count = rate_stats["week_count"]
            today_size = self._format_size(rate_stats["today_size"])
            week_size = self._format_size(rate_stats["week_size"])
            rate_info = f" ║ Today: {today_count} ({today_size}) | Week: {week_count} ({week_size})"
        except Exception:
            rate_info = ""

        info_label = self.query_one("#library-info", Label)
        if is_search:
            info_label.update(
                f"{count} result{'s' if count != 1 else ''} | {total_size}{rate_info}"
            )
        else:
            info_label.update(f"{count} video{'s' if count != 1 else ''} | {total_size}{rate_info}")

    def _format_platform(self, platform: str) -> str:
        """Format platform name for display using centralized mapping."""
        return PLATFORM_DISPLAY.get(platform, platform.capitalize())

    def _format_duration(self, seconds: float | None) -> str:
        """Format duration in MM:SS or HH:MM:SS."""
        if not seconds:
            return "--:--"

        minutes, secs = divmod(int(seconds), 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _normalize_for_display(self, text: str, max_len: int | None = None) -> str:
        """Remove emojis and optionally truncate for clean table display.

        Emojis take 2 terminal cells but are counted as 1 character,
        causing column misalignment in DataTable. This strips them.
        """
        if not text:
            return ""

        # Remove emoji characters (Unicode ranges for common emojis)
        emoji_pattern = re.compile(
            "["
            "\U0001f1e0-\U0001f1ff"  # Flags
            "\U0001f300-\U0001f5ff"  # Symbols & pictographs
            "\U0001f600-\U0001f64f"  # Emoticons
            "\U0001f680-\U0001f6ff"  # Transport & map
            "\U0001f700-\U0001f77f"  # Alchemical symbols
            "\U0001f780-\U0001f7ff"  # Geometric shapes extended
            "\U0001f800-\U0001f8ff"  # Supplemental arrows
            "\U0001f900-\U0001f9ff"  # Supplemental symbols
            "\U0001fa00-\U0001fa6f"  # Chess symbols
            "\U0001fa70-\U0001faff"  # Symbols extended
            "\U00002702-\U000027b0"  # Dingbats
            "\U0000fe00-\U0000fe0f"  # Variation selectors
            "\U0001f000-\U0001f02f"  # Mahjong tiles
            "]+",
            flags=re.UNICODE,
        )
        cleaned = emoji_pattern.sub("", text).strip()

        # Collapse multiple spaces that may result from emoji removal
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Truncate if needed
        if max_len and len(cleaned) > max_len:
            return cleaned[: max_len - 1] + "…"
        return cleaned
