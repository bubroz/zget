"""
zget database store.

SQLite operations with FTS5 full-text search.
"""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .models import DownloadTask, Video, WatchedAccount

# ============================================================================
# SCHEMA
# ============================================================================

SCHEMA_VERSION = 1

SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- ============================================================================
-- VIDEOS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source information
    url TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL,
    video_id TEXT NOT NULL,
    
    -- Content metadata
    title TEXT NOT NULL,
    description TEXT,
    uploader TEXT NOT NULL,
    uploader_id TEXT,
    upload_date TEXT,
    duration_seconds INTEGER,
    
    -- Engagement metrics
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    
    -- Technical metadata
    resolution TEXT,
    fps REAL,
    codec TEXT,
    file_size_bytes INTEGER,
    file_hash_sha256 TEXT,
    
    -- Local storage
    local_path TEXT,
    thumbnail_path TEXT,
    downloaded_at TEXT,
    
    -- User metadata (tags stored as JSON array)
    tags TEXT DEFAULT '[]',
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    notes TEXT,
    collection TEXT,
    
    -- Raw yt-dlp data (JSON blob)
    raw_metadata TEXT,
    
    -- Constraints
    UNIQUE(platform, video_id)
);

-- Full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
    title,
    description,
    uploader,
    tags,
    notes,
    content='videos',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
    INSERT INTO videos_fts(rowid, title, description, uploader, tags, notes)
    VALUES (new.id, new.title, new.description, new.uploader, new.tags, new.notes);
END;

CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, title, description, uploader, tags, notes)
    VALUES ('delete', old.id, old.title, old.description, old.uploader, old.tags, old.notes);
END;

CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, title, description, uploader, tags, notes)
    VALUES ('delete', old.id, old.title, old.description, old.uploader, old.tags, old.notes);
    INSERT INTO videos_fts(rowid, title, description, uploader, tags, notes)
    VALUES (new.id, new.title, new.description, new.uploader, new.tags, new.notes);
END;

-- ============================================================================
-- WATCHED ACCOUNTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS watched_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Account identification
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_url TEXT NOT NULL,
    display_name TEXT,
    
    -- Monitoring configuration
    check_interval_minutes INTEGER DEFAULT 120,
    enabled INTEGER DEFAULT 1,
    auto_download INTEGER DEFAULT 0,
    
    -- State tracking
    last_checked_at TEXT,
    last_new_content_at TEXT,
    last_known_video_id TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Authentication
    requires_auth INTEGER DEFAULT 0,
    cookies_browser TEXT,
    
    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(platform, account_id)
);

-- ============================================================================
-- MONITOR RUNS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS monitor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watched_account_id INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    videos_found INTEGER DEFAULT 0,
    new_videos INTEGER DEFAULT 0,
    error_message TEXT,
    
    FOREIGN KEY (watched_account_id) REFERENCES watched_accounts(id) ON DELETE CASCADE
);

-- ============================================================================
-- DOWNLOAD QUEUE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS download_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    
    -- Pre-fetched info
    title TEXT,
    uploader TEXT,
    duration_seconds INTEGER,
    thumbnail_url TEXT,
    
    -- Download options
    format_id TEXT,
    output_dir TEXT,
    cookies_browser TEXT,
    
    -- Progress
    progress_percent REAL DEFAULT 0,
    downloaded_bytes INTEGER DEFAULT 0,
    total_bytes INTEGER,
    speed_bytes_per_sec REAL,
    eta_seconds INTEGER,
    
    -- Result
    video_id INTEGER,
    error_message TEXT,
    
    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE SET NULL
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);
CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos(uploader);
CREATE INDEX IF NOT EXISTS idx_videos_downloaded ON videos(downloaded_at);
CREATE INDEX IF NOT EXISTS idx_videos_hash ON videos(file_hash_sha256);
CREATE INDEX IF NOT EXISTS idx_videos_collection ON videos(collection);

CREATE INDEX IF NOT EXISTS idx_watched_platform ON watched_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_watched_enabled ON watched_accounts(enabled);

CREATE INDEX IF NOT EXISTS idx_queue_status ON download_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_created ON download_queue(created_at);
"""


# ============================================================================
# VIDEO STORE
# ============================================================================


class VideoStore:
    """SQLite-based video library with full-text search."""

    def __init__(self, db_path: Path):
        """Initialize the store with the given database path."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Set schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_metadata(self, key: str, default: str | None = None) -> str | None:
        """Get a metadata value by key."""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value."""
        with self._connect() as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    # ========================================================================
    # VIDEO OPERATIONS
    # ========================================================================

    def insert_video(self, video: Video) -> int:
        """Insert a video into the library. Returns the new ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO videos (
                    url, platform, video_id, title, description,
                    uploader, uploader_id, upload_date, duration_seconds,
                    view_count, like_count, comment_count,
                    resolution, fps, codec, file_size_bytes, file_hash_sha256,
                    local_path, thumbnail_path, downloaded_at,
                    tags, rating, notes, collection, raw_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video.url,
                    video.platform,
                    video.video_id,
                    video.title,
                    video.description,
                    video.uploader,
                    video.uploader_id,
                    video.upload_date.isoformat() if video.upload_date else None,
                    video.duration_seconds,
                    video.view_count,
                    video.like_count,
                    video.comment_count,
                    video.resolution,
                    video.fps,
                    video.codec,
                    video.file_size_bytes,
                    video.file_hash_sha256,
                    video.local_path,
                    video.thumbnail_path,
                    video.downloaded_at.isoformat() if video.downloaded_at else None,
                    json.dumps(video.tags),
                    video.rating,
                    video.notes,
                    video.collection,
                    json.dumps(video.raw_metadata) if video.raw_metadata else None,
                ),
            )
            return cursor.lastrowid  # type: ignore

    def get_video(self, video_id: int) -> Video | None:
        """Get a video by its database ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
            return self._row_to_video(row) if row else None

    def get_video_by_url(self, url: str) -> Video | None:
        """Get a video by its URL."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE url = ?", (url,)).fetchone()
            return self._row_to_video(row) if row else None

    def get_video_by_video_id(self, video_id: str) -> Video | None:
        """Get a video by its platform-specific video ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
            return self._row_to_video(row) if row else None

    def get_uploaders(self) -> list[dict]:
        """Get distinct uploaders with their video counts."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT uploader, platform, COUNT(*) as count
                FROM videos
                GROUP BY uploader, platform
                ORDER BY count DESC
                """
            ).fetchall()
            return [{"uploader": row[0], "platform": row[1], "count": row[2]} for row in rows]

    def exists_by_url(self, url: str) -> bool:
        """Check if a URL already exists in the library."""
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM videos WHERE url = ?", (url,)).fetchone()
            return row is not None

    def exists_by_hash(self, file_hash: str) -> bool:
        """Check if a file with this hash already exists (duplicate content)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM videos WHERE file_hash_sha256 = ?", (file_hash,)
            ).fetchone()
            return row is not None

    def search(self, query: str, limit: int = 50) -> list[Video]:
        """
        Full-text search across title, description, uploader, tags, notes.

        Returns videos sorted by relevance. Supports prefix matching.
        """
        with self._connect() as conn:
            # Escape special FTS5 characters and add prefix matching
            safe_query = query.replace('"', '""')
            # Add * for prefix matching (so "departm" matches "department")
            fts_query = f'"{safe_query}"*'
            rows = conn.execute(
                """
                SELECT v.* FROM videos v
                JOIN videos_fts fts ON v.id = fts.rowid
                WHERE videos_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
            return [self._row_to_video(row) for row in rows]

    def get_recent(self, limit: int = 100) -> list[Video]:
        """Get the most recently downloaded videos."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM videos
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_video(row) for row in rows]

    def get_by_platform(self, platform: str, limit: int = 100) -> list[Video]:
        """Get videos from a specific platform."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM videos
                WHERE platform = ?
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (platform, limit),
            ).fetchall()
            return [self._row_to_video(row) for row in rows]

    def get_by_uploader(self, uploader: str, limit: int = 100) -> list[Video]:
        """Get videos from a specific uploader."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM videos
                WHERE uploader = ? OR uploader_id = ?
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (uploader, uploader, limit),
            ).fetchall()
            return [self._row_to_video(row) for row in rows]

    def get_by_collection(self, collection: str, limit: int = 100) -> list[Video]:
        """Get videos in a specific collection."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM videos
                WHERE collection = ?
                ORDER BY downloaded_at DESC
                LIMIT ?
                """,
                (collection, limit),
            ).fetchall()
            return [self._row_to_video(row) for row in rows]

    def update_video(self, video: Video) -> None:
        """Update an existing video."""
        if video.id is None:
            raise ValueError("Cannot update video without an ID")

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos SET
                    tags = ?,
                    rating = ?,
                    notes = ?,
                    collection = ?
                WHERE id = ?
                """,
                (
                    json.dumps(video.tags),
                    video.rating,
                    video.notes,
                    video.collection,
                    video.id,
                ),
            )

    def delete_video(self, video_id: int) -> bool:
        """Delete a video from the library. Returns True if deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            return cursor.rowcount > 0

    def count_videos(self) -> int:
        """Get total count of videos in the library."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM videos").fetchone()
            return row[0] if row else 0

    def get_stats(self) -> dict:
        """Get library statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            total_size = conn.execute(
                "SELECT COALESCE(SUM(file_size_bytes), 0) FROM videos"
            ).fetchone()[0]
            platforms = conn.execute(
                """
                SELECT platform, COUNT(*) as count 
                FROM videos 
                GROUP BY platform 
                ORDER BY count DESC
                """
            ).fetchall()

            return {
                "total_videos": total,
                "total_size_bytes": total_size,
                "platforms": {row["platform"]: row["count"] for row in platforms},
            }

    def get_download_rate_stats(self) -> dict:
        """Get download rate statistics for today and this week."""
        with self._connect() as conn:
            # Today's downloads
            today = datetime.now().strftime("%Y-%m-%d")
            today_row = conn.execute(
                """
                SELECT COUNT(*) as count, COALESCE(SUM(file_size_bytes), 0) as size
                FROM videos WHERE DATE(downloaded_at) = ?
                """,
                (today,),
            ).fetchone()

            # This week's downloads (last 7 days)
            week_row = conn.execute(
                """
                SELECT COUNT(*) as count, COALESCE(SUM(file_size_bytes), 0) as size
                FROM videos WHERE downloaded_at >= datetime('now', '-7 days')
                """
            ).fetchone()

            return {
                "today_count": today_row["count"] if today_row else 0,
                "today_size": today_row["size"] if today_row else 0,
                "week_count": week_row["count"] if week_row else 0,
                "week_size": week_row["size"] if week_row else 0,
            }

    def _row_to_video(self, row: sqlite3.Row) -> Video:
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

    # ========================================================================
    # WATCHED ACCOUNTS OPERATIONS
    # ========================================================================

    def add_watched_account(self, account: WatchedAccount) -> int:
        """Add an account to watch. Returns the new ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO watched_accounts (
                    platform, account_id, account_url, display_name,
                    check_interval_minutes, enabled, auto_download,
                    requires_auth, cookies_browser
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.platform,
                    account.account_id,
                    account.account_url,
                    account.display_name,
                    account.check_interval_minutes,
                    1 if account.enabled else 0,
                    1 if account.auto_download else 0,
                    1 if account.requires_auth else 0,
                    account.cookies_browser,
                ),
            )
            return cursor.lastrowid  # type: ignore

    def get_watched_accounts(self, enabled_only: bool = False) -> list[WatchedAccount]:
        """Get all watched accounts."""
        with self._connect() as conn:
            if enabled_only:
                rows = conn.execute("SELECT * FROM watched_accounts WHERE enabled = 1").fetchall()
            else:
                rows = conn.execute("SELECT * FROM watched_accounts").fetchall()
            return [self._row_to_watched_account(row) for row in rows]

    def update_watched_account(self, account: WatchedAccount) -> None:
        """Update a watched account."""
        if account.id is None:
            raise ValueError("Cannot update account without an ID")

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE watched_accounts SET
                    display_name = ?,
                    check_interval_minutes = ?,
                    enabled = ?,
                    auto_download = ?,
                    last_checked_at = ?,
                    last_new_content_at = ?,
                    last_known_video_id = ?,
                    consecutive_failures = ?,
                    requires_auth = ?,
                    cookies_browser = ?
                WHERE id = ?
                """,
                (
                    account.display_name,
                    account.check_interval_minutes,
                    1 if account.enabled else 0,
                    1 if account.auto_download else 0,
                    account.last_checked_at.isoformat() if account.last_checked_at else None,
                    account.last_new_content_at.isoformat()
                    if account.last_new_content_at
                    else None,
                    account.last_known_video_id,
                    account.consecutive_failures,
                    1 if account.requires_auth else 0,
                    account.cookies_browser,
                    account.id,
                ),
            )

    def delete_watched_account(self, account_id: int) -> bool:
        """Delete a watched account."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM watched_accounts WHERE id = ?", (account_id,))
            return cursor.rowcount > 0

    def _row_to_watched_account(self, row: sqlite3.Row) -> WatchedAccount:
        """Convert a database row to a WatchedAccount model."""
        return WatchedAccount(
            id=row["id"],
            platform=row["platform"],
            account_id=row["account_id"],
            account_url=row["account_url"],
            display_name=row["display_name"],
            check_interval_minutes=row["check_interval_minutes"],
            enabled=bool(row["enabled"]),
            auto_download=bool(row["auto_download"]),
            last_checked_at=datetime.fromisoformat(row["last_checked_at"])
            if row["last_checked_at"]
            else None,
            last_new_content_at=datetime.fromisoformat(row["last_new_content_at"])
            if row["last_new_content_at"]
            else None,
            last_known_video_id=row["last_known_video_id"],
            consecutive_failures=row["consecutive_failures"],
            requires_auth=bool(row["requires_auth"]),
            cookies_browser=row["cookies_browser"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    # ========================================================================
    # DOWNLOAD QUEUE OPERATIONS
    # ========================================================================

    def add_to_queue(self, task: DownloadTask) -> int:
        """Add a download task to the queue. Returns the new ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO download_queue (
                    url, platform, status, title, uploader, duration_seconds,
                    thumbnail_url, format_id, output_dir, cookies_browser
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.url,
                    task.platform,
                    task.status,
                    task.title,
                    task.uploader,
                    task.duration_seconds,
                    task.thumbnail_url,
                    task.format_id,
                    task.output_dir,
                    task.cookies_browser,
                ),
            )
            return cursor.lastrowid  # type: ignore

    def get_pending_tasks(self, limit: int = 32) -> list[DownloadTask]:
        """Get pending download tasks."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM download_queue
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_download_task(row) for row in rows]

    def get_active_tasks(self) -> list[DownloadTask]:
        """Get currently downloading tasks."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM download_queue
                WHERE status = 'downloading'
                ORDER BY started_at ASC
                """
            ).fetchall()
            return [self._row_to_download_task(row) for row in rows]

    def update_task_progress(
        self,
        task_id: int,
        progress_percent: float,
        downloaded_bytes: int,
        total_bytes: int | None,
        speed: float | None,
        eta: int | None,
    ) -> None:
        """Update download progress for a task."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE download_queue SET
                    progress_percent = ?,
                    downloaded_bytes = ?,
                    total_bytes = ?,
                    speed_bytes_per_sec = ?,
                    eta_seconds = ?
                WHERE id = ?
                """,
                (progress_percent, downloaded_bytes, total_bytes, speed, eta, task_id),
            )

    def complete_task(self, task_id: int, video_id: int) -> None:
        """Mark a task as complete with the resulting video ID."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE download_queue SET
                    status = 'complete',
                    progress_percent = 100,
                    video_id = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (video_id, datetime.now().isoformat(), task_id),
            )

    def fail_task(self, task_id: int, error_message: str) -> None:
        """Mark a task as failed."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE download_queue SET
                    status = 'failed',
                    error_message = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (error_message, datetime.now().isoformat(), task_id),
            )

    def _row_to_download_task(self, row: sqlite3.Row) -> DownloadTask:
        """Convert a database row to a DownloadTask model."""
        return DownloadTask(
            id=row["id"],
            url=row["url"],
            platform=row["platform"],
            status=row["status"],
            title=row["title"],
            uploader=row["uploader"],
            duration_seconds=row["duration_seconds"],
            thumbnail_url=row["thumbnail_url"],
            format_id=row["format_id"],
            output_dir=row["output_dir"],
            cookies_browser=row["cookies_browser"],
            progress_percent=row["progress_percent"] or 0,
            downloaded_bytes=row["downloaded_bytes"] or 0,
            total_bytes=row["total_bytes"],
            speed_bytes_per_sec=row["speed_bytes_per_sec"],
            eta_seconds=row["eta_seconds"],
            video_id=row["video_id"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
        )
