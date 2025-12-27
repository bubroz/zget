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
    DEFAULT_COOKIE_BROWSER,
    FILENAME_TEMPLATE_SAFE,
    detect_platform,
    get_cookie_browser,
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
        "outtmpl": str(output_dir / FILENAME_TEMPLATE_SAFE),
        "quiet": quiet,
        "no_warnings": quiet,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 8,
        "restrictfilenames": False,  # Allow unicode in filenames
        "windowsfilenames": True,  # But sanitize for safety
        "ffmpeg_location": "/opt/homebrew/bin/",  # Homebrew ffmpeg on Apple Silicon
        # Enable EJS remote components for YouTube JS challenge solver
        # This is required to get video formats on YouTube
        "enable_ejs_remote_components": "github",
        # IMPORTANT: Only download single video, not entire playlist
        "noplaylist": True,
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
            # Use 'bv*+ba' format which means "best video + best audio"
            opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
            opts["merge_output_format"] = "mp4"
    else:
        # Constrain to max height
        opts["format"] = (
            f"bv*[height<={max_quality}][ext=mp4]+ba[ext=m4a]"
            f"/bv*[height<={max_quality}]+ba"
            f"/b[height<={max_quality}]"
            "/b"
        )
        opts["merge_output_format"] = "mp4"

    # Cookie authentication
    if cookies_from:
        opts["cookiesfrombrowser"] = (cookies_from,)
    elif cookies_file:
        opts["cookiefile"] = str(cookies_file)
    else:
        # Use platform-specific default browser for cookies
        default_browser = get_cookie_browser(platform)
        if default_browser:
            opts["cookiesfrombrowser"] = (default_browser,)

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

        # Get the final filename (may differ from prepared filename due to merging)
        if downloaded_filepath is None:
            downloaded_filepath = ydl.prepare_filename(info)

        # Handle merged output format
        if opts.get("merge_output_format"):
            base = Path(downloaded_filepath)
            merged_path = base.with_suffix(f".{opts['merge_output_format']}")
            if merged_path.exists():
                downloaded_filepath = str(merged_path)

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
            opts["cookiesfrombrowser"] = (default_browser,)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

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
