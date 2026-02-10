"""
zget database models.

Pydantic models for type safety and validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Video(BaseModel):
    """A downloaded video with all its metadata."""

    # Database ID
    id: int | None = None

    # Source information
    url: str
    platform: str
    video_id: str

    # Content metadata
    title: str
    description: str | None = None
    uploader: str
    uploader_id: str | None = None
    uploader_url: str | None = None
    upload_date: datetime | None = None
    duration_seconds: float | None = None

    # Engagement metrics
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None

    # Technical metadata
    resolution: str | None = None  # e.g., "1920x1080"
    fps: float | None = None
    codec: str | None = None  # e.g., "h264", "vp9"
    format_id: str | None = None
    file_size_bytes: int | None = None
    file_hash_sha256: str | None = None

    # Local storage
    local_path: str | None = None
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None
    downloaded_at: datetime | None = None

    # User-added metadata
    tags: list[str] = Field(default_factory=list)
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    collection: str | None = None

    # Raw yt-dlp info_dict (stored as JSON in DB)
    raw_metadata: dict | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class WatchedAccount(BaseModel):
    """An account being monitored for new content."""

    # Database ID
    id: int | None = None

    # Account identification
    platform: str
    account_id: str  # e.g., "@mkbhd", "UC...", "user/..."
    account_url: str  # Full URL to the account/channel
    display_name: str | None = None

    # Monitoring configuration
    check_interval_minutes: int = 120  # Default: 2 hours
    enabled: bool = True
    auto_download: bool = False  # Default: notify only

    # State tracking
    last_checked_at: datetime | None = None
    last_new_content_at: datetime | None = None
    last_known_video_id: str | None = None  # Most recent video we've seen
    consecutive_failures: int = 0

    # Authentication
    requires_auth: bool = False
    cookies_browser: str | None = None  # e.g., "chrome", "firefox"

    # Timestamps
    created_at: datetime | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class MonitorRun(BaseModel):
    """A single run of the account monitor."""

    id: int | None = None
    watched_account_id: int
    started_at: datetime
    completed_at: datetime | None = None
    status: str  # "success", "failed", "auth_required"
    videos_found: int = 0
    new_videos: int = 0
    error_message: str | None = None


class DownloadTask(BaseModel):
    """A video download task in the queue."""

    id: int | None = None
    url: str
    platform: str
    status: str = "pending"  # pending, downloading, complete, failed, cancelled

    # Optional pre-fetched info
    title: str | None = None
    uploader: str | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None

    # Download options
    format_id: str | None = None  # Selected format, or None for best
    output_dir: str | None = None  # Override output directory
    cookies_browser: str | None = None

    # Progress tracking
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed_bytes_per_sec: float | None = None
    eta_seconds: int | None = None

    # Result
    video_id: int | None = None  # ID in videos table after successful download
    error_message: str | None = None

    # Timestamps
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class ExportedVideo(BaseModel):
    """Curated video data for JSON export (excludes raw_metadata)."""

    url: str
    platform: str
    video_id: str
    title: str
    description: str | None = None
    uploader: str
    uploader_id: str | None = None
    upload_date: str | None = None  # ISO format string
    duration_seconds: float | None = None
    view_count: int | None = None
    like_count: int | None = None
    resolution: str | None = None
    fps: float | None = None
    codec: str | None = None
    file_size_bytes: int | None = None
    file_hash_sha256: str | None = None
    local_path: str | None = None
    downloaded_at: str | None = None  # ISO format string
    tags: list[str] = Field(default_factory=list)
    rating: int | None = None
    collection: str | None = None

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
