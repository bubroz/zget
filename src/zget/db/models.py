"""
zget database models.

Pydantic models for type safety and validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Video(BaseModel):
    """A downloaded video with all its metadata."""

    # Database ID
    id: Optional[int] = None

    # Source information
    url: str
    platform: str
    video_id: str

    # Content metadata
    title: str
    description: Optional[str] = None
    uploader: str
    uploader_id: Optional[str] = None
    upload_date: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    # Engagement metrics
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    # Technical metadata
    resolution: Optional[str] = None  # e.g., "1920x1080"
    fps: Optional[float] = None
    codec: Optional[str] = None  # e.g., "h264", "vp9"
    file_size_bytes: Optional[int] = None
    file_hash_sha256: Optional[str] = None

    # Local storage
    local_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    # User-added metadata
    tags: list[str] = Field(default_factory=list)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None
    collection: Optional[str] = None

    # Raw yt-dlp info_dict (stored as JSON in DB)
    raw_metadata: Optional[dict] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class WatchedAccount(BaseModel):
    """An account being monitored for new content."""

    # Database ID
    id: Optional[int] = None

    # Account identification
    platform: str
    account_id: str  # e.g., "@mkbhd", "UC...", "user/..."
    account_url: str  # Full URL to the account/channel
    display_name: Optional[str] = None

    # Monitoring configuration
    check_interval_minutes: int = 120  # Default: 2 hours
    enabled: bool = True
    auto_download: bool = False  # Default: notify only

    # State tracking
    last_checked_at: Optional[datetime] = None
    last_new_content_at: Optional[datetime] = None
    last_known_video_id: Optional[str] = None  # Most recent video we've seen
    consecutive_failures: int = 0

    # Authentication
    requires_auth: bool = False
    cookies_browser: Optional[str] = None  # e.g., "chrome", "firefox"

    # Timestamps
    created_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class MonitorRun(BaseModel):
    """A single run of the account monitor."""

    id: Optional[int] = None
    watched_account_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "success", "failed", "auth_required"
    videos_found: int = 0
    new_videos: int = 0
    error_message: Optional[str] = None


class DownloadTask(BaseModel):
    """A video download task in the queue."""

    id: Optional[int] = None
    url: str
    platform: str
    status: str = "pending"  # pending, downloading, complete, failed, cancelled

    # Optional pre-fetched info
    title: Optional[str] = None
    uploader: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None

    # Download options
    format_id: Optional[str] = None  # Selected format, or None for best
    output_dir: Optional[str] = None  # Override output directory
    cookies_browser: Optional[str] = None

    # Progress tracking
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bytes_per_sec: Optional[float] = None
    eta_seconds: Optional[int] = None

    # Result
    video_id: Optional[int] = None  # ID in videos table after successful download
    error_message: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class ExportedVideo(BaseModel):
    """Curated video data for JSON export (excludes raw_metadata)."""

    url: str
    platform: str
    video_id: str
    title: str
    description: Optional[str] = None
    uploader: str
    uploader_id: Optional[str] = None
    upload_date: Optional[str] = None  # ISO format string
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_hash_sha256: Optional[str] = None
    local_path: Optional[str] = None
    downloaded_at: Optional[str] = None  # ISO format string
    tags: list[str] = Field(default_factory=list)
    rating: Optional[int] = None
    collection: Optional[str] = None

    @classmethod
    def from_video(cls, video: Video) -> "ExportedVideo":
        """Create an export model from a full Video."""
        return cls(
            url=video.url,
            platform=video.platform,
            video_id=video.video_id,
            title=video.title,
            description=video.description,
            uploader=video.uploader,
            uploader_id=video.uploader_id,
            upload_date=video.upload_date.isoformat() if video.upload_date else None,
            duration_seconds=video.duration_seconds,
            view_count=video.view_count,
            like_count=video.like_count,
            resolution=video.resolution,
            fps=video.fps,
            codec=video.codec,
            file_size_bytes=video.file_size_bytes,
            file_hash_sha256=video.file_hash_sha256,
            local_path=video.local_path,
            downloaded_at=video.downloaded_at.isoformat() if video.downloaded_at else None,
            tags=video.tags,
            rating=video.rating,
            collection=video.collection,
        )
