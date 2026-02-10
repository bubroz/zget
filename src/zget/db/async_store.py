"""
zget async database store.

Async SQLite operations using aiosqlite for non-blocking FastAPI integration.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from .models import Video


class AsyncVideoStore:
    """Async SQLite-based video library with full-text search."""

    def __init__(self, db_path: Path):
        """Initialize the async store with the given database path."""
        self.db_path = db_path

    @asynccontextmanager
    async def _connect(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Async context manager for database connections."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    # ========================================================================
    # VIDEO OPERATIONS
    # ========================================================================

    async def get_video(self, video_id: int) -> Video | None:
        """Get a video by its database ID."""
        async with self._connect() as conn:
            cursor = await conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = await cursor.fetchone()
            return self._row_to_video(row) if row else None

    async def get_recent(self, limit: int = 100) -> list[Video]:
        """Get the most recently downloaded videos."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM videos
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_video(row) for row in rows]

    async def search(self, query: str, limit: int = 50) -> list[Video]:
        """
        Full-text search across title, description, uploader, tags, notes.

        Returns videos sorted by relevance. Supports prefix matching.
        """
        async with self._connect() as conn:
            # Escape special FTS5 characters and add prefix matching
            safe_query = query.replace('"', '""')
            fts_query = f'"{safe_query}"*'
            cursor = await conn.execute(
                """
                SELECT v.* FROM videos v
                JOIN videos_fts fts ON v.id = fts.rowid
                WHERE videos_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_video(row) for row in rows]

    async def get_by_uploader(self, uploader: str, limit: int = 100) -> list[Video]:
        """Get videos from a specific uploader."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM videos
                WHERE uploader = ?
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (uploader, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_video(row) for row in rows]

    async def get_by_platform(self, platform: str, limit: int = 100) -> list[Video]:
        """Get videos from a specific platform."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM videos
                WHERE platform = ?
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (platform, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_video(row) for row in rows]

    async def delete_video(self, video_id: int) -> bool:
        """Delete a video by its database ID. Returns True if deleted."""
        async with self._connect() as conn:
            cursor = await conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            return cursor.rowcount > 0

    async def update_video(self, video: Video) -> None:
        """Update a video in the database."""
        async with self._connect() as conn:
            await conn.execute(
                """
                UPDATE videos SET
                    title = ?, description = ?, notes = ?, rating = ?,
                    collection = ?, thumbnail_path = ?, local_path = ?
                WHERE id = ?
                """,
                (
                    video.title,
                    video.description,
                    video.notes,
                    video.rating,
                    video.collection,
                    video.thumbnail_path,
                    video.local_path,
                    video.id,
                ),
            )

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _row_to_video(self, row: aiosqlite.Row) -> Video:
        """Convert a database row to a Video model."""
        return Video(
            id=row["id"],
            url=row["url"],
            platform=row["platform"],
            video_id=row["video_id"],
            title=row["title"],
            description=row["description"],
            uploader=row["uploader"],
            uploader_id=row["uploader_id"],
            upload_date=datetime.fromisoformat(row["upload_date"]) if row["upload_date"] else None,
            duration_seconds=row["duration_seconds"],
            view_count=row["view_count"],
            like_count=row["like_count"],
            comment_count=row["comment_count"],
            resolution=row["resolution"],
            fps=row["fps"],
            codec=row["codec"],
            file_size_bytes=row["file_size_bytes"],
            file_hash_sha256=row["file_hash_sha256"],
            local_path=row["local_path"],
            thumbnail_path=row["thumbnail_path"],
            downloaded_at=datetime.fromisoformat(row["downloaded_at"])
            if row["downloaded_at"]
            else None,
            tags=json.loads(row["tags"]) if row["tags"] else [],
            rating=row["rating"],
            notes=row["notes"],
            collection=row["collection"],
            raw_metadata=json.loads(row["raw_metadata"]) if row["raw_metadata"] else None,
        )


# ============================================================================
# FASTAPI DEPENDENCY INJECTION
# ============================================================================

# Singleton instance for the async store
_async_store: AsyncVideoStore | None = None


def get_async_store(db_path: Path | None = None) -> AsyncVideoStore:
    """
    Get or create the async video store singleton.

    Usage in FastAPI:
        @app.get("/api/library")
        async def get_library(store: AsyncVideoStore = Depends(get_async_store)):
            return await store.get_recent()
    """
    global _async_store
    if _async_store is None:
        if db_path is None:
            from ..config import DB_PATH

            db_path = DB_PATH
        _async_store = AsyncVideoStore(db_path)
    return _async_store


async def get_db_dependency() -> AsyncVideoStore:
    """FastAPI dependency for database injection."""
    return get_async_store()
