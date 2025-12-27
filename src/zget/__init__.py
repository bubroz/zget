"""
zget - Personal Media Command Center.

A TUI-driven video acquisition and library management tool.
Wraps yt-dlp with a beautiful terminal interface, searchable database,
and account monitoring capabilities.
"""

from zget.core import (
    download,
    extract_info,
    list_formats,
    compute_file_hash,
    get_recent_videos_from_channel,
)
from zget.cookies import get_cookies_from_browser
from zget.config import (
    ZGET_HOME,
    DB_PATH,
    VIDEOS_DIR,
    detect_platform,
    ensure_directories,
)

__version__ = "0.2.0"
__all__ = [
    # Core download functions
    "download",
    "extract_info",
    "list_formats",
    "compute_file_hash",
    "get_recent_videos_from_channel",
    # Authentication
    "get_cookies_from_browser",
    # Configuration
    "ZGET_HOME",
    "DB_PATH",
    "VIDEOS_DIR",
    "detect_platform",
    "ensure_directories",
]
