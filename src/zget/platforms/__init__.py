"""Platform-specific adapters (beyond plain yt-dlp extractors)."""

from .cspan import (
    is_cspan_event_url,
    is_cspan_hls_url,
    is_cspan_program_url,
    prepare_cspan_downloads,
    prepare_cspan_url,
    resolve_cspan_event,
    resolve_cspan_program,
)

__all__ = [
    "is_cspan_event_url",
    "is_cspan_hls_url",
    "is_cspan_program_url",
    "prepare_cspan_downloads",
    "prepare_cspan_url",
    "resolve_cspan_event",
    "resolve_cspan_program",
]
