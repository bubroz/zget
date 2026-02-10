"""
Shared utilities for zget.

Common helpers used across multiple modules.
"""

import mimetypes
import re
import unicodedata


def get_version() -> str:
    """Get the package version from installed metadata."""
    try:
        from importlib.metadata import version

        return version("zget")
    except Exception:
        return "0.4.0"


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string to be a safe, URL-friendly filename (slug style)."""
    # Convert to NFKD (separate characters from accents)
    name = unicodedata.normalize("NFKD", name)
    # Remove non-ascii characters (emojis, etc)
    name = name.encode("ascii", "ignore").decode("ascii")
    # Replace anything not alphanumeric or hyphen with space
    name = re.sub(r"[^\w-]", " ", name)
    # Replace multiple spaces/underscores/dots with single underscore, lowercase
    name = re.sub(r"[\s_.-]+", "_", name).strip("_").lower()
    # Limit length
    return name[:max_length]


def guess_media_type(path: str) -> str:
    """Guess the MIME type of a media file, defaulting to video/mp4."""
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "video/mp4"
