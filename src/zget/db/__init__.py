"""
zget database package.

SQLite database with FTS5 full-text search for video library management.
"""

from .async_store import AsyncVideoStore, get_db_dependency
from .models import (
    DownloadTask,
    ExportedVideo,
    MonitorRun,
    Video,
    WatchedAccount,
)
from .store import VideoStore

__all__ = [
    "AsyncVideoStore",
    "DownloadTask",
    "ExportedVideo",
    "MonitorRun",
    "Video",
    "VideoStore",
    "WatchedAccount",
    "get_db_dependency",
]
