"""Platform-specific adapters (beyond plain yt-dlp extractors)."""

from .cspan import (
    is_cspan_program_url,
    prepare_cspan_url,
    resolve_cspan_program,
)

__all__ = [
    "is_cspan_program_url",
    "prepare_cspan_url",
    "resolve_cspan_program",
]
