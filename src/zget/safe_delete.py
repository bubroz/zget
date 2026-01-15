"""
Safe delete utilities for zget.

Provides cross-platform trash support using send2trash, with graceful
fallback to hard delete when trash is unavailable.
"""

from pathlib import Path
from typing import Callable

# Try to import send2trash, fall back to None if unavailable
try:
    from send2trash import send2trash as _send2trash

    TRASH_AVAILABLE = True
except ImportError:
    _send2trash = None
    TRASH_AVAILABLE = False


def safe_delete(
    path: Path,
    use_trash: bool = True,
    on_error: Callable[[Path, Exception], None] | None = None,
) -> bool:
    """
    Safely delete a file by moving to system trash.

    Args:
        path: Path to file or directory to delete
        use_trash: If True, move to trash. If False, permanently delete.
        on_error: Optional callback for errors, receives (path, exception)

    Returns:
        True if deletion succeeded, False otherwise
    """
    if not path.exists():
        return True  # Already gone, consider success

    try:
        if use_trash and TRASH_AVAILABLE and _send2trash is not None:
            _send2trash(str(path))
        else:
            # Fallback to hard delete
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil

                shutil.rmtree(path)
        return True
    except Exception as e:
        if on_error:
            on_error(path, e)
        return False


def safe_delete_many(
    paths: list[Path],
    use_trash: bool = True,
) -> tuple[int, list[str]]:
    """
    Delete multiple files with error collection.

    Args:
        paths: List of paths to delete
        use_trash: If True, move to trash. If False, permanently delete.

    Returns:
        Tuple of (success_count, list of error messages)
    """
    deleted = 0
    errors: list[str] = []

    def collect_error(path: Path, e: Exception) -> None:
        errors.append(f"{path}: {e}")

    for path in paths:
        if safe_delete(path, use_trash=use_trash, on_error=collect_error):
            deleted += 1

    return deleted, errors


def get_trash_status() -> dict:
    """
    Get information about trash availability.

    Returns:
        Dict with trash status info
    """
    import sys

    return {
        "available": TRASH_AVAILABLE,
        "platform": sys.platform,
        "library": "send2trash" if TRASH_AVAILABLE else None,
    }
