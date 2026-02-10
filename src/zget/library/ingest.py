"""
Video ingest pipeline.

Handles the complete flow: download → metadata extraction → deduplication → DB storage.
"""

import asyncio
import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..config import (
    EXPORTS_DIR,
    THUMBNAILS_DIR,
    detect_platform,
    get_cookie_browser,
    get_video_output_dir,
)
from ..core import compute_file_hash, download, parse_upload_date
from ..db import Video, VideoStore
from ..metadata.nfo import generate_nfo
from ..types import ProgressDict, YtdlpInfo
from .export import export_video_json
from .thumbnails import cache_thumbnail


class DuplicateError(Exception):
    """Raised when a duplicate video is detected."""

    def __init__(self, message: str, existing_video: Video | None = None):
        super().__init__(message)
        self.existing_video: Video | None = existing_video


async def ingest_video(
    url: str,
    store: VideoStore,
    output_dir: Path | str | None = None,
    format_id: str | None = None,
    cookies_from: str | None = None,
    on_progress: Callable[[ProgressDict], None] | None = None,
    skip_duplicate_check: bool = False,
    tags: list[str] | None = None,
    collection: str | None = None,
) -> Video:
    """
    Complete ingest pipeline: download → extract metadata → hash → save to DB.

    Args:
        url: Video URL to download
        store: VideoStore instance for database operations
        output_dir: Override output directory (default: auto from platform)
        format_id: Specific format to download (from list_formats)
        cookies_from: Browser for cookie extraction
        on_progress: Callback for download progress
        skip_duplicate_check: Skip URL duplicate check (for re-downloads)
        tags: Optional tags to apply to the video
        collection: Optional collection name

    Returns:
        Video model with all metadata

    Raises:
        DuplicateError: If video URL or content hash already exists
    """
    # 1. Check for URL duplicates
    if not skip_duplicate_check:
        existing = store.get_video_by_url(url)
        if existing:
            raise DuplicateError(f"URL already in library: {url}", existing_video=existing)

    # 2. Determine platform and output directory
    platform = detect_platform(url)

    if output_dir is None:
        output_dir = get_video_output_dir(platform)
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Get cookie browser if not specified
    if cookies_from is None:
        cookies_from = get_cookie_browser(platform)

    # 4. DOWNLOAD TO TEMP - "Atomic Move" strategy for Plex
    # We download to a temporary directory first, then move to the final
    # destination. This prevents media servers from scanning incomplete files.
    temp_dir = Path(tempfile.mkdtemp(prefix="zget_"))
    try:
        # download with metadata (run in thread pool to avoid blocking)
        info = await asyncio.to_thread(
            download,
            url,
            temp_dir,
            format_id,
            False,  # audio_only
            "best",  # max_quality
            cookies_from,
            None,  # cookies_file
            on_progress,
            True,  # quiet
        )

        # 5. Get the downloaded file path - try multiple sources
        file_path = None

        # Method 1: Our custom field
        if info.get("_zget_filepath"):
            file_path = Path(info["_zget_filepath"])
            if file_path.exists():
                pass  # Found it
            else:
                file_path = None

        # Method 2: requested_downloads contains the actual merged output
        if file_path is None and info.get("requested_downloads"):
            for rd in info["requested_downloads"]:
                if rd.get("filepath"):
                    possible = Path(rd["filepath"])
                    if possible.exists():
                        file_path = possible
                        break
                if rd.get("filename"):
                    possible = Path(rd["filename"])
                    if possible.exists():
                        file_path = possible
                        break

        # Method 3: Search output_dir for files matching the title
        if file_path is None:
            title = info.get("title", "")
            upload_date = info.get("upload_date", "")
            uploader = info.get("uploader", "unknown")

            # Search for mp4 files that might match
            for ext in ["mp4", "webm", "mkv"]:
                for mp4 in temp_dir.glob(f"*.{ext}"):
                    # Check if filename contains key parts
                    name = mp4.name
                    if (upload_date in name and uploader in name) or title[:20] in name:
                        file_path = mp4
                        break
                if file_path:
                    break

        # Method 4: Just get the most recently modified file
        if file_path is None:
            mp4_files = list(temp_dir.glob("*.mp4"))
            if mp4_files:
                # Get most recent
                file_path = max(mp4_files, key=lambda p: p.stat().st_mtime)

        if file_path is None or not file_path.exists():
            raise FileNotFoundError(f"Downloaded file not found in {temp_dir}")

        # Now move it to the final destination (ATOMIC MOVE)
        final_path = output_dir / file_path.name
        # Use shutil.move to handle cross-device move if necessary
        shutil.move(str(file_path), str(final_path))
        file_path = final_path

        # 6. Compute file hash for deduplication (also in thread)
        file_hash = await asyncio.to_thread(compute_file_hash, file_path)

        # 7. Check for content duplicates
        if store.exists_by_hash(file_hash):
            # Delete the duplicate file we just downloaded
            file_path.unlink(missing_ok=True)
            raise DuplicateError(f"File content already in library (hash: {file_hash[:12]}...)")

        # 8. Cache thumbnail
        thumbnail_path = await cache_thumbnail(info, THUMBNAILS_DIR)

        # 9. Build Video model
        # Convert duration to int (X/Twitter returns float)
        duration = info.get("duration")
        duration_seconds = int(duration) if duration is not None else None

        # Determine uploader with fallbacks
        uploader = info.get("uploader")
        if not uploader or uploader.lower() in ("unknown", "null", "none"):
            if platform == "c-span":
                uploader = "C-SPAN"
            else:
                uploader = "unknown"

        video = Video(
            url=url,
            platform=platform,
            video_id=info.get("id", ""),
            title=info.get("title", "Untitled"),
            description=info.get("description"),
            uploader=uploader,
            uploader_id=info.get("uploader_id"),
            upload_date=parse_upload_date(info.get("upload_date")),
            duration_seconds=duration_seconds,
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            comment_count=info.get("comment_count"),
            resolution=f"{info.get('width', '?')}x{info.get('height', '?')}",
            fps=info.get("fps"),
            codec=info.get("vcodec"),
            file_size_bytes=file_path.stat().st_size,
            file_hash_sha256=file_hash,
            local_path=str(file_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            downloaded_at=datetime.now(),
            tags=tags or [],
            collection=collection,
            raw_metadata=_sanitize_metadata(info),
        )

        # 10. Save to database
        video.id = store.insert_video(video)

        # 11. Export JSON
        export_video_json(video, EXPORTS_DIR)

        # 12. PLEX INTEGRATION: Generate NFO and Local Thumbnail
        # We save these directly next to the video file for media server discovery
        try:
            nfo_path = file_path.with_suffix(".nfo")
            generate_nfo(video, nfo_path)

            # Copy thumbnail to video directory as well for Plex/Jellyfin
            if thumbnail_path and thumbnail_path.exists():
                local_thumb = file_path.with_suffix(thumbnail_path.suffix)
                if not local_thumb.exists():
                    shutil.copy2(thumbnail_path, local_thumb)
        except Exception as e:
            # Don't fail the whole ingest if NFO generation fails
            print(f"Warning: Failed to generate sidecar metadata: {e}")

        return video
    finally:
        # Always clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def ingest_video_sync(
    url: str,
    store: VideoStore,
    output_dir: Path | str | None = None,
    format_id: str | None = None,
    cookies_from: str | None = None,
    on_progress: Callable[[ProgressDict], None] | None = None,
    skip_duplicate_check: bool = False,
    tags: list[str] | None = None,
    collection: str | None = None,
) -> Video:
    """
    Synchronous version of ingest_video.

    Uses asyncio.run internally for non-async contexts.
    Falls back to thread-pool execution if already inside a running event loop.
    """
    import asyncio

    coro = ingest_video(
        url=url,
        store=store,
        output_dir=output_dir,
        format_id=format_id,
        cookies_from=cookies_from,
        on_progress=on_progress,
        skip_duplicate_check=skip_duplicate_check,
        tags=tags,
        collection=collection,
    )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _sanitize_metadata(info: YtdlpInfo) -> YtdlpInfo:
    """
    Sanitize yt-dlp info dict for JSON storage.

    Removes non-serializable objects and very large fields.
    """
    # Fields to exclude (large or non-serializable)
    exclude_keys = {
        "formats",  # Large list of all formats
        "thumbnails",  # Large list of all thumbnails
        "subtitles",  # Can be very large
        "automatic_captions",  # Can be very large
        "requested_downloads",  # Internal yt-dlp data
        "requested_formats",  # Internal yt-dlp data
        "http_headers",  # Internal
        "_filename",  # Internal
    }

    sanitized = {}
    for key, value in info.items():
        if key in exclude_keys:
            continue
        if key.startswith("_"):
            # Skip internal keys except our zget ones
            if not key.startswith("_zget"):
                continue

        # Try to ensure serializable
        try:
            import json

            json.dumps(value)
            sanitized[key] = value
        except (TypeError, ValueError):
            # Skip non-serializable values
            continue

    return sanitized
