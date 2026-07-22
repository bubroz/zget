"""Tests for library path resolution and rewrite planning."""

from __future__ import annotations

from pathlib import Path

from zget.db.models import Video
from zget.db.store import VideoStore
from zget.library.paths import (
    PathStatus,
    assess_library,
    assess_video,
    plan_rewrites,
    rewrite_stale_paths,
    try_rebase_under_home,
)


def _video(**kwargs) -> Video:
    defaults = dict(
        url="https://example.com/v1",
        platform="youtube",
        video_id="abc",
        title="Test",
        uploader="Tester",
    )
    defaults.update(kwargs)
    return Video(**defaults)


def test_try_rebase_under_home(tmp_path: Path):
    legacy = tmp_path / "old_home"
    current = tmp_path / "new_home"
    stored = legacy / "videos" / "youtube" / "clip.mp4"
    (current / "videos" / "youtube").mkdir(parents=True)
    # file only on new home
    (current / "videos" / "youtube" / "clip.mp4").write_bytes(b"data")

    got = try_rebase_under_home(stored, legacy, current)
    assert got == current / "videos" / "youtube" / "clip.mp4"
    assert got.exists()


def test_assess_relocatable(tmp_path: Path):
    legacy = tmp_path / "Downloads" / "zget"
    current = tmp_path / "media" / "zget"
    rel = Path("videos/youtube/a.mp4")
    (current / rel).parent.mkdir(parents=True)
    (current / rel).write_bytes(b"x")

    v = _video(id=1, local_path=str(legacy / rel))
    a = assess_video(v, current_home=current, legacy_homes=[legacy])
    assert a.status == PathStatus.RELOCATABLE
    assert a.resolved_path == current / rel


def test_assess_healthy_and_off_home(tmp_path: Path):
    home = tmp_path / "zget"
    outside = tmp_path / "other" / "file.mp4"
    inside = home / "videos" / "x.mp4"
    inside.parent.mkdir(parents=True)
    outside.parent.mkdir(parents=True)
    inside.write_bytes(b"1")
    outside.write_bytes(b"2")

    h = assess_video(
        _video(id=1, local_path=str(inside)),
        current_home=home,
        legacy_homes=[],
    )
    assert h.status == PathStatus.HEALTHY

    o = assess_video(
        _video(id=2, url="https://example.com/v2", video_id="b", local_path=str(outside)),
        current_home=home,
        legacy_homes=[],
    )
    assert o.status == PathStatus.OFF_HOME


def test_assess_orphan(tmp_path: Path):
    home = tmp_path / "zget"
    home.mkdir()
    v = _video(id=1, local_path=str(home / "missing.mp4"))
    a = assess_video(v, current_home=home, legacy_homes=[])
    assert a.status == PathStatus.ORPHAN


def test_rewrite_stale_paths_apply(tmp_path: Path):
    legacy = tmp_path / "old"
    current = tmp_path / "new"
    media_rel = Path("videos/youtube/vid.mp4")
    thumb_rel = Path("thumbnails/youtube_vid.jpg")
    (current / media_rel).parent.mkdir(parents=True)
    (current / thumb_rel).parent.mkdir(parents=True)
    (current / media_rel).write_bytes(b"media")
    (current / thumb_rel).write_bytes(b"thumb")

    db = current / "library.db"
    store = VideoStore(db)
    vid = _video(
        local_path=str(legacy / media_rel),
        thumbnail_path=str(legacy / thumb_rel),
    )
    vid_id = store.insert_video(vid)

    report, plans, backup = rewrite_stale_paths(
        store,
        current_home=current,
        legacy_homes=[legacy],
        dry_run=False,
        backup=True,
        db_path=db,
    )
    assert backup is not None and backup.exists()
    assert len(plans) == 1
    assert plans[0].new_local_path == str(current / media_rel)

    updated = store.get_video(vid_id)
    assert updated is not None
    assert updated.local_path == str(current / media_rel)
    assert updated.thumbnail_path == str(current / thumb_rel)

    # Second pass: nothing left to rewrite
    report2 = assess_library(
        store.list_all_videos(), current_home=current, legacy_homes=[legacy]
    )
    assert len(report2.relocatable) == 0
    assert len(report2.healthy) == 1
    assert len(plan_rewrites(report2, current_home=current, legacy_homes=[legacy])) == 0


def test_doctor_does_not_treat_off_home_as_orphan(tmp_path: Path):
    home = tmp_path / "zget"
    home.mkdir()
    outside = tmp_path / "pipeline" / "out.mp4"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"x")
    report = assess_library(
        [_video(id=1, local_path=str(outside))],
        current_home=home,
        legacy_homes=[],
    )
    assert len(report.orphans) == 0
    assert len(report.off_home) == 1


def test_offline_volume_not_orphan(monkeypatch, tmp_path: Path):
    """Paths under a missing /Volumes/name are offline, not orphans."""
    from zget.library import paths as paths_mod

    home = tmp_path / "zget"
    home.mkdir()
    # Fake a volume path that isn't mounted
    stored = Path("/Volumes/DoesNotExist_zget_test/media/clip.mp4")
    assert not Path("/Volumes/DoesNotExist_zget_test").exists()

    a = assess_video(
        _video(id=1, local_path=str(stored)),
        current_home=home,
        legacy_homes=[],
    )
    assert a.status == PathStatus.OFFLINE_VOLUME
    assert "not mounted" in a.note
