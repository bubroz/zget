"""
Library path resolution and migration.

When ZGET_HOME moves (e.g. ~/Downloads/zget → an external volume), absolute
paths stored in the DB go stale even though the media still exists under the
new home. This module:

- Resolves a stored path against the current home + known legacy homes
- Plans and applies safe DB rewrites (local_path + thumbnail_path)
- Classifies records for doctor (healthy / relocatable / off_home / orphan)

No network. Pure filesystem + SQLite updates via VideoStore.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from ..config import ZGET_HOME
from ..db.models import Video
from ..db.store import VideoStore

# Historical default home used by zget before custom zget_home configs.
DEFAULT_LEGACY_HOME = Path.home() / "Downloads" / "zget"


class PathStatus(str, Enum):
    """Classification of a video's stored media path."""

    HEALTHY = "healthy"  # stored path exists
    RELOCATABLE = "relocatable"  # missing at stored path, found under current home
    OFF_HOME = "off_home"  # exists outside ZGET_HOME (pipeline -o); not an orphan
    OFFLINE_VOLUME = "offline_volume"  # path is under /Volumes/X and X is not mounted
    ORPHAN = "orphan"  # no file found (and volume root is present if applicable)
    EMPTY = "empty"  # no local_path set


@dataclass
class PathAssessment:
    video: Video
    status: PathStatus
    stored_path: Path | None
    resolved_path: Path | None = None
    stored_thumbnail: Path | None = None
    resolved_thumbnail: Path | None = None
    note: str = ""


@dataclass
class RewritePlan:
    """One row to update after a successful relocate."""

    video_id: int
    old_local_path: str | None
    new_local_path: str | None
    old_thumbnail_path: str | None
    new_thumbnail_path: str | None


@dataclass
class LibraryPathReport:
    assessments: list[PathAssessment] = field(default_factory=list)

    @property
    def healthy(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.HEALTHY]

    @property
    def relocatable(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.RELOCATABLE]

    @property
    def off_home(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.OFF_HOME]

    @property
    def orphans(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.ORPHAN]

    @property
    def offline_volume(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.OFFLINE_VOLUME]

    @property
    def empty(self) -> list[PathAssessment]:
        return [a for a in self.assessments if a.status == PathStatus.EMPTY]


def default_legacy_homes() -> list[Path]:
    """Known previous library roots to try when resolving stale absolute paths."""
    homes = [DEFAULT_LEGACY_HOME.resolve()]
    current = ZGET_HOME.expanduser().resolve()
    # Dedup if already on default
    return [h for h in homes if h != current]


def try_rebase_under_home(stored: Path, legacy_home: Path, current_home: Path) -> Path | None:
    """
    If stored is under legacy_home, return the equivalent path under current_home.

    Example:
      stored:  /Users/me/Downloads/zget/videos/youtube/a.mp4
      legacy:  /Users/me/Downloads/zget
      current: /Volumes/Media/zget
      → /Volumes/Media/zget/videos/youtube/a.mp4
    """
    try:
        rel = stored.resolve() if stored.exists() else stored
        # Use pure string/path prefix when file is missing (resolve may fail on missing)
        stored_abs = Path(stored).expanduser()
        if not stored_abs.is_absolute():
            stored_abs = Path.cwd() / stored_abs
        legacy = legacy_home.expanduser().resolve() if legacy_home.exists() else legacy_home.expanduser()
        try:
            relative = stored_abs.relative_to(legacy)
        except ValueError:
            # Also try string prefix for non-normalized paths
            stored_s = str(stored_abs)
            legacy_s = str(legacy)
            if not stored_s.startswith(legacy_s.rstrip("/") + "/") and stored_s != legacy_s:
                return None
            relative = Path(stored_s[len(legacy_s) :].lstrip("/"))
        candidate = current_home.expanduser() / relative
        return candidate
    except Exception:
        return None


def resolve_under_homes(
    stored: str | Path | None,
    *,
    current_home: Path | None = None,
    legacy_homes: list[Path] | None = None,
) -> tuple[Path | None, Path | None]:
    """
    Resolve a stored absolute path.

    Returns:
        (resolved_existing_path, suggested_path_if_relocatable)
        - If stored exists: (stored, None)  → healthy
        - If rebased under current home exists: (candidate, candidate) → relocatable
        - Else: (None, None) or (None, candidate) if candidate guessed but missing
    """
    if not stored:
        return None, None

    current = (current_home or ZGET_HOME).expanduser()
    path = Path(stored).expanduser()

    if path.exists():
        return path, None

    legacies = legacy_homes if legacy_homes is not None else default_legacy_homes()
    for legacy in legacies:
        candidate = try_rebase_under_home(path, legacy, current)
        if candidate is not None and candidate.exists():
            return candidate, candidate

    # Last resort: same relative layout under current home even without legacy prefix match
    # (e.g. path was already relative-ish). Skip if we can't derive a relative segment.
    return None, None


def is_under_home(path: Path, home: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(home.expanduser().resolve())
        return True
    except Exception:
        try:
            return str(path.expanduser()).startswith(str(home.expanduser()).rstrip("/") + "/")
        except Exception:
            return False


def volume_mount_root(path: Path) -> Path | None:
    """
    If path is under /Volumes/<name>/..., return /Volumes/<name>.
    Otherwise None (not a volume path).
    """
    parts = path.expanduser().parts
    # ('/', 'Volumes', 'waypoint', ...)
    if len(parts) >= 3 and parts[1] == "Volumes":
        return Path("/") / "Volumes" / parts[2]
    return None


def assess_video(
    video: Video,
    *,
    current_home: Path | None = None,
    legacy_homes: list[Path] | None = None,
) -> PathAssessment:
    """Classify one video record's path health."""
    home = (current_home or ZGET_HOME).expanduser()
    legs = legacy_homes if legacy_homes is not None else default_legacy_homes()

    if not video.local_path:
        return PathAssessment(
            video=video,
            status=PathStatus.EMPTY,
            stored_path=None,
            note="no local_path",
        )

    stored = Path(video.local_path).expanduser()
    existing, reloc = resolve_under_homes(
        video.local_path, current_home=home, legacy_homes=legs
    )

    thumb_stored = Path(video.thumbnail_path).expanduser() if video.thumbnail_path else None
    thumb_existing, thumb_reloc = resolve_under_homes(
        video.thumbnail_path, current_home=home, legacy_homes=legs
    ) if video.thumbnail_path else (None, None)

    if existing is not None and reloc is None:
        # Stored path works
        if is_under_home(existing, home):
            status = PathStatus.HEALTHY
            note = "ok"
        else:
            status = PathStatus.OFF_HOME
            note = "file exists outside ZGET_HOME (intentional pipeline output)"
        return PathAssessment(
            video=video,
            status=status,
            stored_path=stored,
            resolved_path=existing,
            stored_thumbnail=thumb_stored,
            resolved_thumbnail=thumb_existing or thumb_reloc,
            note=note,
        )

    if existing is not None and reloc is not None:
        return PathAssessment(
            video=video,
            status=PathStatus.RELOCATABLE,
            stored_path=stored,
            resolved_path=reloc,
            stored_thumbnail=thumb_stored,
            resolved_thumbnail=thumb_reloc if thumb_reloc else thumb_existing,
            note="stale home prefix; file found under current ZGET_HOME",
        )

    # Unmounted external volume → not a true orphan (media may still exist offline)
    vol = volume_mount_root(stored)
    if vol is not None and not vol.exists():
        return PathAssessment(
            video=video,
            status=PathStatus.OFFLINE_VOLUME,
            stored_path=stored,
            resolved_path=None,
            stored_thumbnail=thumb_stored,
            resolved_thumbnail=None,
            note=f"volume not mounted: {vol}",
        )

    return PathAssessment(
        video=video,
        status=PathStatus.ORPHAN,
        stored_path=stored,
        resolved_path=None,
        stored_thumbnail=thumb_stored,
        resolved_thumbnail=None,
        note="file missing",
    )


def assess_library(
    videos: list[Video],
    *,
    current_home: Path | None = None,
    legacy_homes: list[Path] | None = None,
) -> LibraryPathReport:
    report = LibraryPathReport()
    for v in videos:
        report.assessments.append(
            assess_video(v, current_home=current_home, legacy_homes=legacy_homes)
        )
    return report


def plan_rewrites(
    report: LibraryPathReport,
    *,
    current_home: Path | None = None,
    legacy_homes: list[Path] | None = None,
) -> list[RewritePlan]:
    """
    Build rewrite rows when local_path and/or thumbnail_path can be rebased
    onto the current ZGET_HOME (media or thumb file exists at the new path).
    """
    home = current_home or ZGET_HOME
    legs = legacy_homes if legacy_homes is not None else default_legacy_homes()
    plans: list[RewritePlan] = []

    for a in report.assessments:
        v = a.video
        if v.id is None:
            continue

        new_local = v.local_path
        new_thumb = v.thumbnail_path
        changed = False

        if v.local_path:
            _existing, reloc = resolve_under_homes(
                v.local_path, current_home=home, legacy_homes=legs
            )
            if reloc is not None:
                new_local = str(reloc)
                changed = True

        if v.thumbnail_path:
            _existing, reloc = resolve_under_homes(
                v.thumbnail_path, current_home=home, legacy_homes=legs
            )
            if reloc is not None:
                new_thumb = str(reloc)
                changed = True

        if changed:
            plans.append(
                RewritePlan(
                    video_id=v.id,
                    old_local_path=v.local_path,
                    new_local_path=new_local,
                    old_thumbnail_path=v.thumbnail_path,
                    new_thumbnail_path=new_thumb,
                )
            )
    return plans


def backup_database(db_path: Path, backup_dir: Path | None = None) -> Path:
    """Copy library.db to a timestamped backup next to it (or backup_dir)."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = Path(backup_dir) if backup_dir else db_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"library.db.bak.{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def apply_rewrites(store: VideoStore, plans: list[RewritePlan]) -> int:
    """Apply path rewrites. Returns number of rows updated."""
    updated = 0
    for plan in plans:
        store.update_media_paths(
            plan.video_id,
            local_path=plan.new_local_path,
            thumbnail_path=plan.new_thumbnail_path,
        )
        updated += 1
    return updated


def rewrite_stale_paths(
    store: VideoStore,
    *,
    current_home: Path | None = None,
    legacy_homes: list[Path] | None = None,
    dry_run: bool = True,
    backup: bool = True,
    db_path: Path | None = None,
) -> tuple[LibraryPathReport, list[RewritePlan], Path | None]:
    """
    Assess library, plan relocatable rewrites, optionally backup + apply.

    Returns (report, plans, backup_path_or_None).
    """
    videos = store.list_all_videos()
    report = assess_library(videos, current_home=current_home, legacy_homes=legacy_homes)
    plans = plan_rewrites(
        report, current_home=current_home, legacy_homes=legacy_homes
    )
    backup_path: Path | None = None

    if dry_run or not plans:
        return report, plans, None

    if backup:
        path = db_path or getattr(store, "db_path", None)
        if path is None:
            raise ValueError("db_path required for backup")
        backup_path = backup_database(Path(path))

    apply_rewrites(store, plans)
    return report, plans, backup_path
