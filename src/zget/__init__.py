"""
zget - Agentic media capture and local archival library.

CLI and MCP front-end over yt-dlp: download, dedupe, metadata, path handoff.
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
    "download",
    "extract_info",
    "list_formats",
    "compute_file_hash",
    "get_recent_videos_from_channel",
    "get_cookies_from_browser",
    "ZGET_HOME",
    "DB_PATH",
    "VIDEOS_DIR",
    "detect_platform",
    "ensure_directories",
]
