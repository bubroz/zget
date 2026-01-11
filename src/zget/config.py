"""
zget configuration module.

Central configuration for all paths and settings.
"""

from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================

import os
import json

# Standard config location
CONFIG_DIR = Path.home() / ".config" / "zget"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_persistent_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


PERSISTENT_CONFIG = load_persistent_config()

# All zget data lives here (in ~/Downloads, visible folder by default)
ZGET_HOME = Path(
    os.getenv(
        "ZGET_HOME", PERSISTENT_CONFIG.get("zget_home", str(Path.home() / "Downloads" / "zget"))
    )
)

# Database
DB_PATH = ZGET_HOME / "library.db"

# Media storage (organized by platform)
VIDEOS_DIR = ZGET_HOME / "videos"
THUMBNAILS_DIR = ZGET_HOME / "thumbnails"

# Exports and logs
EXPORTS_DIR = ZGET_HOME / "exports"
LOGS_DIR = ZGET_HOME / "logs"

# ============================================================================
# DOWNLOAD SETTINGS
# ============================================================================

# Maximum concurrent downloads
PARALLEL_DOWNLOADS = 32

# Default video quality (can be overridden per-download)
DEFAULT_QUALITY = "best"

# Filename template: {date}_{uploader}_{title}.{ext}
# Using simpler template that yt-dlp handles reliably
FILENAME_TEMPLATE = "%(upload_date)s_%(uploader)s_%(title)s.%(ext)s"

# Same template - yt-dlp handles missing fields gracefully
FILENAME_TEMPLATE_SAFE = "%(upload_date)s_%(uploader)s_%(title)s.%(ext)s"

# ============================================================================
# MONITORING SETTINGS
# ============================================================================

# Default check interval in minutes
DEFAULT_CHECK_INTERVAL_MINUTES = 120  # 2 hours

# Platform-specific intervals (some platforms are more lenient)
PLATFORM_CHECK_INTERVALS = {
    "youtube": 60,  # 1 hour - YouTube is lenient
    "tiktok": 120,  # 2 hours - TikTok is stricter
    "instagram": 120,  # 2 hours - Instagram is strict
    "twitter": 120,  # 2 hours
}

# Jitter percentage for randomizing check times (±10%)
CHECK_INTERVAL_JITTER = 0.10

# ============================================================================
# AUTHENTICATION
# ============================================================================

# Default browser for cookie extraction (for logged-in sessions)
DEFAULT_COOKIE_BROWSER = "brave"

# Per-platform browser preferences (can be overridden)
PLATFORM_COOKIE_BROWSERS: dict[str, str] = {}

# ============================================================================
# BROWSER SETTINGS (for opening URLs)
# ============================================================================

# Browser application to use for opening URLs
# Options: "default", "brave", "chrome", "safari", "firefox"
BROWSER_APP = "brave"

# Browser profile directory name (for Brave/Chrome)
# Use None for default profile, or specify like "Profile 1", "Profile 4", etc.
# Find profiles at: ~/Library/Application Support/BraveSoftware/Brave-Browser/
BROWSER_PROFILE = "Default"

# ============================================================================
# DUPLICATE DETECTION
# ============================================================================

# Check for duplicates by URL before downloading
CHECK_DUPLICATE_URL = True

# Check for duplicates by file hash after downloading
CHECK_DUPLICATE_HASH = True

# ============================================================================
# EXPORT SETTINGS
# ============================================================================

# Automatically export JSON after each download
AUTO_EXPORT_JSON = True

# Include full yt-dlp raw metadata in database
STORE_RAW_METADATA = True

# ============================================================================
# TUI SETTINGS
# ============================================================================

# Enable clipboard monitoring for auto-detecting URLs
CLIPBOARD_MONITORING = True

# Notification sound on events
NOTIFICATION_SOUND = True

# ============================================================================
# PLATFORM DETECTION
# ============================================================================

PLATFORM_PATTERNS = {
    "youtube": [
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
    ],
    "tiktok": [
        "tiktok.com",
        "vm.tiktok.com",
    ],
    "instagram": [
        "instagram.com",
        "instagr.am",
    ],
    "twitter": [
        "twitter.com",
        "x.com",
        "t.co",
    ],
    "reddit": [
        "reddit.com",
        "redd.it",
    ],
    "twitch": [
        "twitch.tv",
        "clips.twitch.tv",
    ],
}

PLATFORM_DISPLAY = {
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "twitter": "X",
    "reddit": "Reddit",
    "twitch": "Twitch",
}


def detect_platform(url: str) -> str:
    """Detect the platform from a URL."""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            # Check for proper domain boundary: pattern must be followed by / or end of domain
            # This prevents 't.co' from matching in 'combatfootage'
            idx = url_lower.find(pattern)
            if idx != -1:
                end_idx = idx + len(pattern)
                # Check that pattern is at domain boundary (followed by /, :, or end)
                if end_idx >= len(url_lower) or url_lower[end_idx] in ("/", ":", "?", "#"):
                    return platform
    return "other"


def get_video_output_dir(platform: str) -> Path:
    """Get the output directory for a platform's videos."""
    output_dir = VIDEOS_DIR / platform
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_check_interval(platform: str) -> int:
    """Get the check interval in minutes for a platform."""
    return PLATFORM_CHECK_INTERVALS.get(platform, DEFAULT_CHECK_INTERVAL_MINUTES)


def get_cookie_browser(platform: str) -> str:
    """Get the browser to use for cookie extraction for a platform."""
    return PLATFORM_COOKIE_BROWSERS.get(platform, DEFAULT_COOKIE_BROWSER)


def ensure_directories() -> None:
    """Create all necessary directories if they don't exist."""
    for directory in [ZGET_HOME, VIDEOS_DIR, THUMBNAILS_DIR, EXPORTS_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
