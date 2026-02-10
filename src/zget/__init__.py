"""
zget - Personal Media Command Center.

A TUI-driven video acquisition and library management tool.
Wraps yt-dlp with a beautiful terminal interface, searchable database,
and account monitoring capabilities.
"""

from zget.config import (
    DB_PATH,
    VIDEOS_DIR,
    ZGET_HOME,
    detect_platform,
    ensure_directories,
)
from zget.cookies import get_cookies_from_browser
from zget.core import (
    compute_file_hash,
    download,
    extract_info,
    get_recent_videos_from_channel,
    list_formats,
)
from zget.utils import get_version

__version__ = get_version()
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
