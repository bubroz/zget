"""Tests for .librarian.json provenance sidecars."""

from __future__ import annotations

import json
from pathlib import Path

from zget.metadata.librarian_json import (
    build_librarian_payload,
    generate_librarian_json,
    generate_librarian_json_from_info,
    librarian_json_path,
    source_id_from_url,
)


def test_librarian_json_path():
    p = Path("/tmp/foo/bar video.mp4")
    assert librarian_json_path(p) == Path("/tmp/foo/bar video.librarian.json")


def test_source_id_youtube():
    assert (
        source_id_from_url("https://www.youtube.com/watch?v=abc123XYZ_-")
        == "abc123XYZ_-"
    )


def test_source_id_cspan():
    assert (
        source_id_from_url(
            "https://www.c-span.org/event/campaign-2026/title/444858"
        )
        == "cspan_444858"
    )
    assert (
        source_id_from_url(
            "https://www.c-span.org/program/campaign-2026/title/682566"
        )
        == "cspan_682566"
    )


def test_generate_librarian_json_roundtrip(tmp_path: Path):
    media = tmp_path / "20260709_C-SPAN_Test.mp4"
    media.write_bytes(b"fake-video-bytes")

    side = generate_librarian_json(
        media,
        url="https://www.c-span.org/program/campaign-2026/title/682566",
        title="Test Title",
        platform="c-span",
        duration_sec=1223.4,
        published_date="20260709",
        sha256="abc",
        source_id="cspan_682566",
        uploader="C-SPAN",
        extra={"program_id": "682566", "event_id": "444858"},
    )
    assert side.name == "20260709_C-SPAN_Test.librarian.json"
    data = json.loads(side.read_text())
    assert data["title"] == "Test Title"
    assert data["platform"] == "c-span"
    assert data["duration_sec"] == "1223"
    assert data["published_date"] == "2026-07-09"
    assert data["sha256"] == "abc"
    assert data["source_id"] == "cspan_682566"
    assert data["program_id"] == "682566"
    assert data["event_id"] == "444858"
    assert data["file_size"] == str(media.stat().st_size)
    assert "local_path" in data


def test_from_info_cspan(tmp_path: Path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"x" * 100)
    info = {
        "title": "Campaign Event",
        "id": "682566",
        "original_url": (
            "https://www.c-span.org/event/campaign-2026/title/444858"
        ),
        "webpage_url": (
            "https://www.c-span.org/program/campaign-2026/title/682566"
        ),
        "upload_date": "20260709",
        "duration": 100,
        "uploader": "C-SPAN",
        "_zget_platform": "c-span",
        "_zget_cspan_program": True,
        "_zget_cspan_event_id": "444858",
        "_zget_cspan_m3u8": "https://m3u8-1.c-spanvideo.org/program/program.682566.tsc.m3u8",
        "_zget_downloaded_at": "2026-07-22T12:00:00",
    }
    side = generate_librarian_json_from_info(media, info, sha256="deadbeef")
    data = json.loads(side.read_text())
    assert data["platform"] == "c-span"
    assert data["sha256"] == "deadbeef"
    assert data["event_id"] == "444858"
    assert data["program_id"] == "682566"
    assert data["url"].endswith("444858") or "c-span.org" in data["url"]


def test_build_payload_omits_empty_corpus_unless_provided():
    payload = build_librarian_payload(
        Path("/tmp/a.mp4"),
        url="https://example.com/v",
        title="T",
        platform="youtube",
    )
    assert "person_id" not in payload
    payload2 = build_librarian_payload(
        Path("/tmp/a.mp4"),
        url="https://example.com/v",
        title="T",
        platform="youtube",
        extra={"person_id": "example_person"},
    )
    assert payload2["person_id"] == "example_person"
