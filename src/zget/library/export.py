"""
Video export functionality.

Export video metadata to JSON for analytics pipelines.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..db import Video, VideoStore, ExportedVideo


async def export_video_json(
    video: Video,
    export_dir: Path,
    include_raw: bool = False,
) -> Path:
    """
    Export a single video's metadata to JSON.

    Args:
        video: Video to export
        export_dir: Directory to save JSON files
        include_raw: Include full raw_metadata (large)

    Returns:
        Path to the exported JSON file
    """
    export_dir.mkdir(parents=True, exist_ok=True)

    # Create curated export model
    exported = ExportedVideo.from_video(video)
    data = exported.model_dump()

    # Optionally include raw metadata
    if include_raw and video.raw_metadata:
        data["raw_metadata"] = video.raw_metadata

    # Generate filename: {platform}_{video_id}_{timestamp}.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_video_id = _safe_filename(video.video_id)
    filename = f"{video.platform}_{safe_video_id}_{timestamp}.json"

    export_path = export_dir / filename

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    return export_path


async def export_library_json(
    store: VideoStore,
    export_path: Path,
    include_raw: bool = False,
    platform: Optional[str] = None,
    collection: Optional[str] = None,
    limit: Optional[int] = None,
) -> int:
    """
    Export library to a single JSON file.

    Args:
        store: VideoStore instance
        export_path: Path for the output JSON file
        include_raw: Include raw_metadata for each video
        platform: Filter by platform
        collection: Filter by collection
        limit: Maximum number of videos to export

    Returns:
        Number of videos exported
    """
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Get videos based on filters
    if platform:
        videos = store.get_by_platform(platform, limit=limit or 10000)
    elif collection:
        videos = store.get_by_collection(collection, limit=limit or 10000)
    else:
        videos = store.get_recent(limit=limit or 10000)

    # Convert to export format
    export_data = []
    for video in videos:
        exported = ExportedVideo.from_video(video)
        data = exported.model_dump()

        if include_raw and video.raw_metadata:
            data["raw_metadata"] = video.raw_metadata

        export_data.append(data)

    # Write to file
    output = {
        "exported_at": datetime.now().isoformat(),
        "total_videos": len(export_data),
        "filters": {
            "platform": platform,
            "collection": collection,
            "limit": limit,
        },
        "videos": export_data,
    }

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    return len(export_data)


def export_video_json_sync(
    video: Video,
    export_dir: Path,
    include_raw: bool = False,
) -> Path:
    """Synchronous version of export_video_json."""
    import asyncio

    return asyncio.run(export_video_json(video, export_dir, include_raw))


def export_library_json_sync(
    store: VideoStore,
    export_path: Path,
    include_raw: bool = False,
    platform: Optional[str] = None,
    collection: Optional[str] = None,
    limit: Optional[int] = None,
) -> int:
    """Synchronous version of export_library_json - works in event loops."""
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Get videos based on filters
    if platform:
        videos = store.get_by_platform(platform, limit=limit or 10000)
    elif collection:
        videos = store.get_by_collection(collection, limit=limit or 10000)
    else:
        videos = store.get_recent(limit=limit or 10000)

    # Convert to export format
    export_data = []
    for video in videos:
        exported = ExportedVideo.from_video(video)
        data = exported.model_dump()

        if include_raw and video.raw_metadata:
            data["raw_metadata"] = video.raw_metadata

        export_data.append(data)

    # Write to file
    output = {
        "exported_at": datetime.now().isoformat(),
        "total_videos": len(export_data),
        "filters": {
            "platform": platform,
            "collection": collection,
            "limit": limit,
        },
        "videos": export_data,
    }

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    return len(export_data)


def _safe_filename(text: str, max_length: int = 50) -> str:
    """Create a safe filename from text."""
    import re

    # Remove problematic characters
    safe = re.sub(r'[<>:"/\\|?*\s]', "_", text)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Truncate
    return safe[:max_length].strip("_")
