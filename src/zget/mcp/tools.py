"""
MCP Tool implementations for zget.

Each tool is an async method that interfaces with zget's core functionality.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from ..config import DB_PATH
from ..db import VideoStore


class ZgetTools:
    """
    MCP tool implementations for zget.

    Provides async wrappers around zget's core functionality for agent access.
    """

    def __init__(self):
        self._store: Optional[VideoStore] = None

    @property
    def store(self) -> VideoStore:
        """Lazy-load the video store."""
        if self._store is None:
            self._store = VideoStore(DB_PATH)
        return self._store

    async def search(self, query: str, limit: int = 20) -> dict:
        """
        Search the video library using full-text search.

        Args:
            query: Search text (supports prefix matching)
            limit: Maximum results

        Returns:
            Dict with 'videos' list containing matches
        """
        videos = self.store.search(query, limit=limit)
        return {
            "count": len(videos),
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "uploader": v.uploader,
                    "platform": v.platform,
                    "duration_seconds": v.duration_seconds,
                    "local_path": v.local_path,
                    "downloaded_at": v.downloaded_at.isoformat() if v.downloaded_at else None,
                }
                for v in videos
            ],
        }

    async def get_video(self, video_id: int) -> dict:
        """
        Get full metadata for a video by ID.

        Args:
            video_id: Database ID

        Returns:
            Full video metadata dict
        """
        video = self.store.get_video(video_id)
        if not video:
            return {"error": f"Video {video_id} not found"}

        return {
            "id": video.id,
            "url": video.url,
            "platform": video.platform,
            "video_id": video.video_id,
            "title": video.title,
            "description": video.description,
            "uploader": video.uploader,
            "uploader_url": video.uploader_url,
            "duration_seconds": video.duration_seconds,
            "upload_date": video.upload_date.isoformat() if video.upload_date else None,
            "downloaded_at": video.downloaded_at.isoformat() if video.downloaded_at else None,
            "local_path": video.local_path,
            "file_size_bytes": video.file_size_bytes,
            "file_hash_sha256": video.file_hash_sha256,
            "resolution": video.resolution,
            "format_id": video.format_id,
            "thumbnail_url": video.thumbnail_url,
            "tags": video.tags,
            "collection": video.collection,
            "notes": video.notes,
        }

    async def get_local_path(self, video_id: int) -> dict:
        """
        Get the local file path for a video.

        This is the key handoff point for Librarian integration -
        it gets the actual file path for SAM3 analysis.

        Args:
            video_id: Database ID

        Returns:
            Dict with 'path' and existence check
        """
        video = self.store.get_video(video_id)
        if not video:
            return {"error": f"Video {video_id} not found"}

        path = Path(video.local_path) if video.local_path else None
        return {
            "video_id": video_id,
            "path": video.local_path,
            "exists": path.exists() if path else False,
            "size_bytes": path.stat().st_size if path and path.exists() else None,
            "title": video.title,
        }

    async def download(
        self,
        url: str,
        collection: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """
        Download a video to the library.

        Args:
            url: Video URL
            collection: Optional collection name
            tags: Optional tags list

        Returns:
            New video metadata including local path
        """
        from ..library.ingest import ingest_video

        try:
            video = await ingest_video(
                url=url,
                store=self.store,
                tags=tags,
                collection=collection,
            )
            return {
                "success": True,
                "video_id": video.id,
                "title": video.title,
                "uploader": video.uploader,
                "local_path": video.local_path,
                "duration_seconds": video.duration_seconds,
                "platform": video.platform,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_info(self, url: str) -> dict:
        """
        Extract metadata without downloading.

        Args:
            url: Video URL

        Returns:
            Video metadata (title, uploader, duration, etc.)
        """
        from ..core import extract_info as core_extract_info

        try:
            info = await asyncio.to_thread(core_extract_info, url)
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "uploader_url": info.get("uploader_url"),
                "duration": info.get("duration"),
                "description": info.get("description", "")[:500],  # Truncate
                "thumbnail": info.get("thumbnail"),
                "view_count": info.get("view_count"),
                "upload_date": info.get("upload_date"),
                "extractor": info.get("extractor"),
                "format_count": len(info.get("formats", [])),
            }
        except Exception as e:
            return {"error": str(e)}

    async def list_formats(self, url: str) -> dict:
        """
        List available download formats for a URL.

        Args:
            url: Video URL

        Returns:
            List of available formats with resolution/quality info
        """
        from ..core import list_formats as core_list_formats

        try:
            formats = await asyncio.to_thread(core_list_formats, url)
            return {
                "count": len(formats),
                "formats": formats[:20],  # Limit to top 20
            }
        except Exception as e:
            return {"error": str(e)}

    async def check_url(self, url: str) -> dict:
        """
        Check if a URL is already in the library.

        Args:
            url: Video URL to check

        Returns:
            Dict indicating if URL exists and video info if found
        """
        video = self.store.get_video_by_url(url)
        if video:
            return {
                "exists": True,
                "video_id": video.id,
                "title": video.title,
                "local_path": video.local_path,
                "downloaded_at": video.downloaded_at.isoformat() if video.downloaded_at else None,
            }
        return {"exists": False}

    async def get_recent(self, limit: int = 20) -> dict:
        """
        Get recently downloaded videos.

        Args:
            limit: Maximum results

        Returns:
            List of recent videos
        """
        videos = self.store.get_recent(limit=limit)
        return {
            "count": len(videos),
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "uploader": v.uploader,
                    "platform": v.platform,
                    "local_path": v.local_path,
                    "downloaded_at": v.downloaded_at.isoformat() if v.downloaded_at else None,
                }
                for v in videos
            ],
        }

    async def get_by_uploader(self, uploader: str, limit: int = 50) -> dict:
        """
        Get videos from a specific uploader/channel.

        Args:
            uploader: Uploader name to filter
            limit: Maximum results

        Returns:
            List of videos from that uploader
        """
        videos = self.store.get_by_uploader(uploader, limit=limit)
        return {
            "count": len(videos),
            "uploader": uploader,
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "platform": v.platform,
                    "local_path": v.local_path,
                    "duration_seconds": v.duration_seconds,
                    "downloaded_at": v.downloaded_at.isoformat() if v.downloaded_at else None,
                }
                for v in videos
            ],
        }
