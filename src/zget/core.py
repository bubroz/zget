"""
Core download functionality wrapping yt-dlp.

Enhanced version with format selection, file hashing, and full metadata extraction.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from .config import (
    BROWSER_PROFILE,
    DEFAULT_COOKIE_BROWSER,
    detect_platform,
    get_cookie_browser,
    get_filename_template,
    get_video_output_dir,
)


def download(
    url: str,
    output_dir: str | Path | None = None,
    format_id: str | None = None,
    audio_only: bool = False,
    max_quality: str = "best",
    cookies_from: str | None = None,
    cookies_file: str | Path | None = None,
    progress_callback: Callable[[dict], None] | None = None,
    quiet: bool = False,
) -> dict:
    """
    Download video/audio from URL.

    Args:
        url: Video URL (YouTube, Instagram, TikTok, Twitter, etc.)
        output_dir: Output directory (default: auto-detect from platform)
        format_id: Specific format ID to download (from list_formats)
        audio_only: Extract audio only (M4A/MP3)
        max_quality: Maximum video height (e.g., "1080", "720") or "best"
        cookies_from: Browser to extract cookies from ("chrome", "firefox", "safari")
        cookies_file: Path to cookies.txt file
        progress_callback: Callback for progress updates
        quiet: Suppress yt-dlp output

    Returns:
        dict with full yt-dlp info_dict including downloaded file info
    """
    # Auto-detect platform and output directory
    platform = detect_platform(url)

    if output_dir is None:
        output_dir = get_video_output_dir(platform)
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build yt-dlp options
    opts = {
        "outtmpl": str(output_dir / get_filename_template()),
        "quiet": quiet,
        "no_warnings": quiet,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 8,
        "restrictfilenames": False,  # Allow unicode in filenames
        "windowsfilenames": True,  # But sanitize for safety
        "ffmpeg_location": "/opt/homebrew/bin/",  # Homebrew ffmpeg on Apple Silicon
        # IMPORTANT: Only download single video, not entire playlist
        "noplaylist": True,
        # Anti-Bot Headers (Bypass 403 specific blocks)
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    # Format selection
    if format_id:
        # User explicitly selected a format
        opts["format"] = format_id
    elif audio_only:
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ]
    elif max_quality == "best":
        # Platform-specific format selection
        if platform == "twitter":
            # Twitter: prefer HTTP formats over HLS to avoid token expiration issues
            # HLS tokens expire during download causing failures at 20-30%
            opts["format"] = "http-10368/http-2176/http-832/http-256/bv*+ba/b"
            opts["merge_output_format"] = "mp4"
        else:
            # Best available video+audio, merged to mp4
            # Force/Prefer H.264 (avc1) for maximum iOS/PWA compatibility
            # This avoids the 'VP9 in MP4' issue that causes black screens on Safari
            opts["format"] = "bv*[ext=mp4][vcodec^=avc]+ba[ext=m4a]/bv*[ext=mp4]+ba[ext=m4a]/b"
            opts["merge_output_format"] = "mp4"
    else:
        # Constrain to max height, still prioritizing compatible codecs
        opts["format"] = (
            f"bv*[height<={max_quality}][ext=mp4][vcodec^=avc]+ba[ext=m4a]"
            f"/bv*[height<={max_quality}][ext=mp4]+ba[ext=m4a]"
            f"/bv*[height<={max_quality}]+ba"
            f"/b[height<={max_quality}]"
            "/b"
        )
        opts["merge_output_format"] = "mp4"

    # Cookie authentication (only if a browser is configured/detected)
    if cookies_from:
        opts["cookiesfrombrowser"] = (cookies_from,)
    elif cookies_file:
        opts["cookiefile"] = str(cookies_file)
    else:
        # Use platform-specific default browser for cookies (if available)
        default_browser = get_cookie_browser(platform)
        if default_browser:
            if BROWSER_PROFILE:
                opts["cookiesfrombrowser"] = (default_browser, BROWSER_PROFILE)
            else:
                opts["cookiesfrombrowser"] = (default_browser,)
        # If no browser detected, skip cookies entirely (downloads still work for public content)

    # Progress callback
    downloaded_filepath = None

    if progress_callback:

        def progress_hook(d):
            nonlocal downloaded_filepath
            if d["status"] == "finished":
                downloaded_filepath = d.get("filename")
            if d["status"] in ("downloading", "finished"):
                progress_callback(
                    {
                        "status": d["status"],
                        "filename": d.get("filename"),
                        "downloaded_bytes": d.get("downloaded_bytes", 0),
                        "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate", 0),
                        "speed": d.get("speed", 0),
                        "eta": d.get("eta", 0),
                        "fragment_index": d.get("fragment_index"),
                        "fragment_count": d.get("fragment_count"),
                    }
                )

        opts["progress_hooks"] = [progress_hook]
    else:

        def progress_hook(d):
            nonlocal downloaded_filepath
            if d["status"] == "finished":
                downloaded_filepath = d.get("filename")

        opts["progress_hooks"] = [progress_hook]

    # Download
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        # Get the final filename
        # requested_downloads is the most reliable source for the final merged file path
        requested = info.get("requested_downloads")
        if requested and len(requested) > 0:
            downloaded_filepath = requested[0].get("filepath")

        # Fallback to prepare_filename if hook didn't catch it or requested_downloads is missing
        if downloaded_filepath is None:
            downloaded_filepath = ydl.prepare_filename(info)

        # Handle merged output format (backup check)
        if opts.get("merge_output_format"):
            # Check if ydl.prepare_filename(info) already has the right extension
            path = Path(downloaded_filepath)
            expected_ext = f".{opts['merge_output_format']}"
            if path.suffix != expected_ext:
                merged_path = path.with_suffix(expected_ext)
                if merged_path.exists():
                    downloaded_filepath = str(merged_path)

    # Sanitize metadata for database (remove non-JSON-serializable objects)
    info = _sanitize_info(info)

    # Add our metadata
    info["_zget_filepath"] = downloaded_filepath
    info["_zget_platform"] = platform
    info["_zget_downloaded_at"] = datetime.now().isoformat()

    return info


def extract_info(
    url: str,
    cookies_from: str | None = None,
    cookies_file: str | Path | None = None,
) -> dict:
    """
    Extract video metadata without downloading.

    Args:
        url: Video URL
        cookies_from: Browser to extract cookies from
        cookies_file: Path to cookies.txt file

    Returns:
        dict with full yt-dlp info_dict
    """
    platform = detect_platform(url)

    opts = {
        "quiet": True,
        "no_warnings": True,
    }

    if cookies_from:
        opts["cookiesfrombrowser"] = (cookies_from,)
    elif cookies_file:
        opts["cookiefile"] = str(cookies_file)
    else:
        default_browser = get_cookie_browser(platform)
        if default_browser:
            if BROWSER_PROFILE:
                opts["cookiesfrombrowser"] = (default_browser, BROWSER_PROFILE)
            else:
                opts["cookiesfrombrowser"] = (default_browser,)
        # If no browser detected, skip cookies entirely

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Sanitize metadata
    info = _sanitize_info(info)

    info["_zget_platform"] = platform
    return info


def list_formats(
    url: str,
    cookies_from: str | None = None,
    cookies_file: str | Path | None = None,
) -> list[dict]:
    """
    List available formats for a video.

    Useful for letting users choose quality before downloading.

    Args:
        url: Video URL
        cookies_from: Browser to extract cookies from
        cookies_file: Path to cookies.txt file

    Returns:
        List of format dicts with id, extension, resolution, codec info
    """
    info = extract_info(url, cookies_from, cookies_file)

    formats = []
    for f in info.get("formats", []):
        # Skip formats without video or audio
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")

        format_dict = {
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution") or _build_resolution(f),
            "width": f.get("width"),
            "height": f.get("height"),
            "fps": f.get("fps"),
            "vcodec": vcodec if vcodec != "none" else None,
            "acodec": acodec if acodec != "none" else None,
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "tbr": f.get("tbr"),  # Total bitrate
            "vbr": f.get("vbr"),  # Video bitrate
            "abr": f.get("abr"),  # Audio bitrate
            "format_note": f.get("format_note"),
            "has_video": vcodec not in ("none", None),
            "has_audio": acodec not in ("none", None),
        }
        formats.append(format_dict)

    # Sort by quality (height, then bitrate)
    formats.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)

    return formats


def _build_resolution(f: dict) -> str:
    """Build resolution string from format dict."""
    width = f.get("width")
    height = f.get("height")
    if width and height:
        return f"{width}x{height}"
    elif height:
        return f"{height}p"
    else:
        return "audio only" if f.get("acodec") not in ("none", None) else "unknown"


def compute_file_hash(file_path: Path | str, algorithm: str = "sha256") -> str:
    """
    Compute hash of a file for duplicate detection.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ("sha256", "md5", etc.)

    Returns:
        Hex digest of the hash
    """
    file_path = Path(file_path)

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        hasher = hashlib.new(algorithm)

    # Read in chunks to handle large files efficiently
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def parse_upload_date(date_str: str | None) -> Optional[datetime]:
    """
    Parse yt-dlp upload_date format (YYYYMMDD) to datetime.

    Args:
        date_str: Date string in YYYYMMDD format

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename for use on the filesystem.

    Args:
        filename: Original filename
        max_length: Maximum length

    Returns:
        Sanitized filename
    """
    # Remove problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)

    # Replace multiple spaces/underscores with single
    filename = re.sub(r"[\s_]+", "_", filename)

    # Trim to max length (preserving extension if present)
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_len = max_length - len(ext) - 1 if ext else max_length
        filename = name[:max_name_len] + ("." + ext if ext else "")

    return filename.strip("._")


def get_recent_videos_from_channel(
    channel_url: str,
    limit: int = 10,
    cookies_from: str | None = None,
) -> list[dict]:
    """
    Get recent videos from a channel/playlist.

    Used for monitoring accounts for new content.

    Args:
        channel_url: URL to channel, playlist, or user page
        limit: Maximum number of videos to fetch
        cookies_from: Browser to extract cookies from

    Returns:
        List of video info dicts (without full download)
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,  # Don't extract each video fully
        "playlistend": limit,
    }

    if cookies_from:
        opts["cookiesfrombrowser"] = (cookies_from,)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get("entries", [])

    videos = []
    for entry in entries:
        if entry is None:
            continue
        videos.append(
            {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "url": entry.get("url") or entry.get("webpage_url"),
                "uploader": entry.get("uploader") or info.get("uploader"),
                "upload_date": entry.get("upload_date"),
                "duration": entry.get("duration"),
                "view_count": entry.get("view_count"),
            }
        )

    return videos


def _sanitize_info(info: dict) -> dict:
    """
    Recursively sanitize yt-dlp info_dict for JSON serialization.

    Removes non-serializable objects like post-processors or logger objects.
    """
    serializable_types = (str, int, float, bool, type(None))

    if isinstance(info, dict):
        return {
            str(k): _sanitize_info(v)
            for k, v in info.items()
            if not str(k).startswith("_")
            or k in ("_zget_filepath", "_zget_platform", "_zget_downloaded_at")
        }
    elif isinstance(info, list):
        return [_sanitize_info(i) for i in info]
    elif isinstance(info, serializable_types):
        return info
    else:
        # Convert everything else to string representation
        return str(info)
