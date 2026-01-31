"""
zget configuration module.

Central configuration for all paths and settings.
"""

from pathlib import Path
import os
import json
import platform


# ============================================================================
# BROWSER DETECTION
# ============================================================================


def detect_installed_browser() -> str | None:
    """
    Detect the first available browser for cookie extraction.

    Returns the first browser found, or None if no supported browser is installed.
    Priority order: Chrome, Brave, Firefox, Edge, Chromium, Opera, Vivaldi
    """
    if platform.system() == "Darwin":  # macOS
        browser_paths = {
            "chrome": Path.home() / "Library/Application Support/Google/Chrome",
            "brave": Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser",
            "firefox": Path.home() / "Library/Application Support/Firefox",
            "edge": Path.home() / "Library/Application Support/Microsoft Edge",
            "chromium": Path.home() / "Library/Application Support/Chromium",
            "opera": Path.home() / "Library/Application Support/com.operasoftware.Opera",
            "vivaldi": Path.home() / "Library/Application Support/Vivaldi",
        }
    elif platform.system() == "Windows":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
        app_data = Path(os.environ.get("APPDATA", ""))
        browser_paths = {
            "chrome": local_app_data / "Google/Chrome/User Data",
            "brave": local_app_data / "BraveSoftware/Brave-Browser/User Data",
            "firefox": app_data / "Mozilla/Firefox",
            "edge": local_app_data / "Microsoft/Edge/User Data",
            "chromium": local_app_data / "Chromium/User Data",
            "opera": app_data / "Opera Software/Opera Stable",
            "vivaldi": local_app_data / "Vivaldi/User Data",
        }
    else:  # Linux
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        browser_paths = {
            "chrome": config_home / "google-chrome",
            "brave": config_home / "BraveSoftware/Brave-Browser",
            "firefox": Path.home() / ".mozilla/firefox",
            "edge": config_home / "microsoft-edge",
            "chromium": config_home / "chromium",
            "opera": config_home / "opera",
            "vivaldi": config_home / "vivaldi",
        }

    # Return first installed browser
    for browser, path in browser_paths.items():
        if path.exists():
            return browser

    return None


# ============================================================================
# PATHS
# ============================================================================

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
# PLEX / MEDIA SERVER INTEGRATION
# ============================================================================

# Custom output directory (overrides VIDEOS_DIR for downloads)
# Set to a path like "/Volumes/Media/Social Videos" for Plex
# Can be set via ZGET_OUTPUT_DIR env var or config.json "output_dir" key
_custom_output_raw = os.getenv("ZGET_OUTPUT_DIR", PERSISTENT_CONFIG.get("output_dir", None))
CUSTOM_OUTPUT_DIR: Path | None = Path(_custom_output_raw) if _custom_output_raw else None

# Use flat structure (no platform subdirectories)
# Default: False (organize by platform)
# When True, all videos go in one folder regardless of platform
FLAT_OUTPUT_STRUCTURE = os.getenv("ZGET_FLAT_OUTPUT", "").lower() in (
    "1",
    "true",
    "yes",
) or PERSISTENT_CONFIG.get("flat_output", False)

# Custom filename template (yt-dlp format)
# Default uses existing FILENAME_TEMPLATE_SAFE
# Plex-friendly example: "%(upload_date>%Y-%m-%d)s %(extractor)s - %(uploader).50s - %(title).100s.%(ext)s"
CUSTOM_FILENAME_TEMPLATE: str | None = os.getenv(
    "ZGET_FILENAME_TEMPLATE", PERSISTENT_CONFIG.get("filename_template", None)
)

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
# Auto-detects first available browser, or can be set via config/env
_detected_browser = detect_installed_browser()
DEFAULT_COOKIE_BROWSER = os.getenv(
    "ZGET_COOKIE_BROWSER", PERSISTENT_CONFIG.get("cookie_browser", _detected_browser)
)

# Per-platform browser preferences (can be overridden)
PLATFORM_COOKIE_BROWSERS: dict[str, str] = {}

# ============================================================================
# BROWSER SETTINGS (for opening URLs)
# ============================================================================

# Browser application to use for opening URLs
# Options: "default", "brave", "chrome", "safari", "firefox"
# Falls back to "default" if no browser detected
BROWSER_APP = os.getenv(
    "ZGET_BROWSER_APP", PERSISTENT_CONFIG.get("browser_app", _detected_browser or "default")
)

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
    "c-span": [
        "c-span.org",
    ],
}

PLATFORM_DISPLAY = {
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "twitter": "X",
    "reddit": "Reddit",
    "twitch": "Twitch",
    "c-span": "C-SPAN",
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
    """Get the output directory for a platform's videos.

    If CUSTOM_OUTPUT_DIR is set, uses that as the base directory.
    If FLAT_OUTPUT_STRUCTURE is True (or custom dir is set), skips platform subdirectories.
    """
    if CUSTOM_OUTPUT_DIR:
        base_dir = CUSTOM_OUTPUT_DIR
        # When using custom output dir, default to flat structure
        use_flat = True
    else:
        base_dir = VIDEOS_DIR
        use_flat = FLAT_OUTPUT_STRUCTURE

    if use_flat:
        # Flat structure: all videos in one folder
        output_dir = base_dir
    else:
        # Organized by platform (default)
        output_dir = base_dir / platform

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_filename_template() -> str:
    """Get the active filename template.

    Returns custom template if set, otherwise the default safe template.
    """
    return CUSTOM_FILENAME_TEMPLATE or FILENAME_TEMPLATE_SAFE


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
