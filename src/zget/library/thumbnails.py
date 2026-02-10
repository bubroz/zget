"""
Thumbnail caching.

Download and cache thumbnails for offline browsing.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ..types import YtdlpInfo


async def cache_thumbnail(
    info: YtdlpInfo,
    thumbnails_dir: Path,
) -> Path | None:
    """
    Download and cache a video's thumbnail.

    Args:
        info: yt-dlp info dict containing thumbnail URL
        thumbnails_dir: Directory to cache thumbnails

    Returns:
        Path to cached thumbnail, or None if unavailable
    """
    thumbnail_url = info.get("thumbnail")

    if not thumbnail_url:
        # Try to get from thumbnails list
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            # Prefer medium-sized thumbnail
            for thumb in thumbnails:
                if thumb.get("width", 0) >= 320:
                    thumbnail_url = thumb.get("url")
                    break
            if not thumbnail_url:
                thumbnail_url = thumbnails[-1].get("url")

    if not thumbnail_url:
        return None

    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from URL hash
    video_id = info.get("id", "unknown")
    platform = info.get("_zget_platform", "unknown")

    # Determine extension from URL
    ext = "jpg"
    if ".png" in thumbnail_url.lower():
        ext = "png"
    elif ".webp" in thumbnail_url.lower():
        ext = "webp"

    filename = f"{platform}_{video_id}.{ext}"
    cache_path = thumbnails_dir / filename

    # Check if already cached
    if cache_path.exists():
        return cache_path

    # Download thumbnail
    try:
        # Build Referer from original URL if available (for CDN protections like C-SPAN)
        referer = None
        original_url = info.get("original_url") or info.get("webpage_url")
        if original_url:
            from urllib.parse import urlparse

            parsed = urlparse(original_url)
            referer = f"{parsed.scheme}://{parsed.netloc}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(thumbnail_url, follow_redirects=True)
            response.raise_for_status()

            with open(cache_path, "wb") as f:
                f.write(response.content)

            return cache_path
    except Exception:
        # Thumbnail download is non-critical, just return None
        return None


def cache_thumbnail_sync(
    info: YtdlpInfo,
    thumbnails_dir: Path,
) -> Path | None:
    """Synchronous version of cache_thumbnail."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an event loop -- run in a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, cache_thumbnail(info, thumbnails_dir)).result()
    return asyncio.run(cache_thumbnail(info, thumbnails_dir))


def get_thumbnail_path(
    video_id: str,
    platform: str,
    thumbnails_dir: Path,
) -> Path | None:
    """
    Get path to cached thumbnail if it exists.

    Args:
        video_id: Video ID
        platform: Platform name
        thumbnails_dir: Directory where thumbnails are cached

    Returns:
        Path to thumbnail if cached, None otherwise
    """
    # Check for common extensions
    for ext in ["jpg", "png", "webp"]:
        path = thumbnails_dir / f"{platform}_{video_id}.{ext}"
        if path.exists():
            return path

    return None


def delete_thumbnail(
    video_id: str,
    platform: str,
    thumbnails_dir: Path,
) -> bool:
    """
    Delete a cached thumbnail.

    Args:
        video_id: Video ID
        platform: Platform name
        thumbnails_dir: Directory where thumbnails are cached

    Returns:
        True if deleted, False if not found
    """
    path = get_thumbnail_path(video_id, platform, thumbnails_dir)
    if path and path.exists():
        path.unlink()
        return True
    return False


def get_cache_stats(thumbnails_dir: Path) -> dict:
    """
    Get statistics about the thumbnail cache.

    Args:
        thumbnails_dir: Directory where thumbnails are cached

    Returns:
        Dict with count, total_size_bytes
    """
    if not thumbnails_dir.exists():
        return {"count": 0, "total_size_bytes": 0}

    count = 0
    total_size = 0

    for path in thumbnails_dir.iterdir():
        if path.is_file() and path.suffix.lower() in (".jpg", ".png", ".webp"):
            count += 1
            total_size += path.stat().st_size

    return {
        "count": count,
        "total_size_bytes": total_size,
    }
