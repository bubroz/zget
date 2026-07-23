"""
Provenance sidecar: ``{stem}.librarian.json`` next to each media file.

zget fills capture fields it knows (url, title, platform, hashes, dates).
Optional corpus-style fields (person_id, race_id, queue, …) are omitted
unless callers pass them via ``extra`` (downstream tools can merge).

Always written after a successful download so event multi-program, CLI, MCP
ingest, and raw ``core.download`` share one path.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


def librarian_json_path(media_path: Path | str) -> Path:
    """``video.mp4`` → ``video.librarian.json`` (stem sidecar, not double-suffix)."""
    path = Path(media_path)
    return path.with_name(path.stem + ".librarian.json")


def source_id_from_url(url: str, fallback_id: str | None = None) -> str:
    """Stable source id for YouTube / C-SPAN / generic URLs."""
    if not url:
        return fallback_id or ""
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower().replace("www.", "")
        if "youtu" in host:
            qs = parse_qs(p.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0]
            if "youtu.be" in host:
                return p.path.strip("/")
        if "c-span.org" in host:
            m = re.search(r"/(\d{5,})/?$", p.path.rstrip("/"))
            if m:
                return f"cspan_{m.group(1)}"
            return "cspan_" + re.sub(r"[^a-zA-Z0-9]+", "_", p.path)[-40:]
    except Exception:
        pass
    if fallback_id:
        return str(fallback_id)
    return ""


def _yyyymmdd_to_iso(date_str: str | None) -> str:
    if not date_str:
        return ""
    s = str(date_str).strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def build_librarian_payload(
    media_path: Path | str,
    *,
    url: str,
    title: str,
    platform: str,
    duration_sec: float | int | None = None,
    published_date: str | None = None,
    file_size: int | None = None,
    sha256: str | None = None,
    downloaded_at: str | None = None,
    source_id: str | None = None,
    uploader: str | None = None,
    media_type: str = "video",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the JSON object written to ``.librarian.json``.

    Empty strings for unknown optional fields keep keys stable for merges.
    """
    path = Path(media_path)
    if file_size is None and path.exists():
        file_size = path.stat().st_size
    if downloaded_at is None:
        downloaded_at = datetime.now(timezone.utc).isoformat()

    sid = source_id if source_id is not None else source_id_from_url(url)

    payload: dict[str, Any] = {
        "url": url or "",
        "published_date": _yyyymmdd_to_iso(published_date),
        "title": title or path.stem,
        "platform": platform or "",
        "media_type": media_type,
        "duration_sec": (
            str(int(duration_sec)) if duration_sec is not None and duration_sec != "" else ""
        ),
        "local_path": str(path.resolve()) if path.exists() else str(path),
        "file_size": str(file_size) if file_size is not None else "",
        "sha256": sha256 or "",
        "downloaded_at": downloaded_at,
        "source_id": sid,
    }
    if uploader:
        payload["uploader"] = uploader

    # Optional corpus keys (empty when zget does not know them)
    for key in (
        "person_id",
        "person_name",
        "race_id",
        "party_role",
        "event_type",
        "canonical",
        "confidence",
        "notes",
        "queue",
    ):
        if extra and key in extra and extra[key] is not None:
            payload[key] = extra[key]

    if extra:
        for k, v in extra.items():
            if k not in payload and v is not None:
                payload[k] = v

    return payload


def generate_librarian_json(
    media_path: Path | str,
    *,
    url: str,
    title: str,
    platform: str,
    duration_sec: float | int | None = None,
    published_date: str | None = None,
    file_size: int | None = None,
    sha256: str | None = None,
    downloaded_at: str | None = None,
    source_id: str | None = None,
    uploader: str | None = None,
    media_type: str = "video",
    extra: dict[str, Any] | None = None,
) -> Path:
    """
    Write ``{stem}.librarian.json`` next to the media file.

    Returns:
        Path to the sidecar written.
    """
    path = Path(media_path)
    side = librarian_json_path(path)
    payload = build_librarian_payload(
        path,
        url=url,
        title=title,
        platform=platform,
        duration_sec=duration_sec,
        published_date=published_date,
        file_size=file_size,
        sha256=sha256,
        downloaded_at=downloaded_at,
        source_id=source_id,
        uploader=uploader,
        media_type=media_type,
        extra=extra,
    )
    side.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return side


def generate_librarian_json_from_info(
    media_path: Path | str,
    info: dict[str, Any],
    *,
    sha256: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """
    Write sidecar from a yt-dlp / zget info dict (post-download).

    Uses original_url / webpage_url for provenance URL; prefers program page
    for C-SPAN when present.
    """
    path = Path(media_path)
    url = (
        info.get("original_url")
        or info.get("webpage_url")
        or info.get("url")
        or ""
    )
    platform = str(info.get("_zget_platform") or info.get("extractor") or "")
    # Normalize common extractors
    if platform.lower() in ("cspan-program", "cspan-event", "cspan", "generic"):
        if "c-span" in url.lower() or info.get("_zget_cspan_program"):
            platform = "c-span"
    if platform in ("Youtube", "youtube"):
        platform = "youtube"

    upload_date = info.get("upload_date")
    media_type = "audio" if info.get("acodec") and not info.get("vcodec") else "video"
    # audio-only formats often still set vcodec to "none"
    vcodec = str(info.get("vcodec") or "")
    if vcodec in ("none", "None") or info.get("_filename", "").endswith(
        (".mp3", ".m4a", ".opus", ".flac", ".wav")
    ):
        if path.suffix.lower() in {".mp3", ".m4a", ".opus", ".flac", ".wav", ".ogg"}:
            media_type = "audio"

    cspan_extra: dict[str, Any] = {}
    if info.get("_zget_cspan_event_id") or info.get("playlist_id"):
        cspan_extra["event_id"] = info.get("_zget_cspan_event_id") or info.get(
            "playlist_id"
        )
    if info.get("id") and (
        info.get("_zget_cspan_program") or platform == "c-span"
    ):
        cspan_extra["program_id"] = str(info.get("id"))
    if info.get("_zget_cspan_m3u8"):
        cspan_extra["m3u8_url"] = info.get("_zget_cspan_m3u8")

    merged_extra = {**cspan_extra, **(extra or {})}

    return generate_librarian_json(
        path,
        url=str(url),
        title=str(info.get("title") or path.stem),
        platform=platform,
        duration_sec=info.get("duration"),
        published_date=str(upload_date) if upload_date else None,
        file_size=path.stat().st_size if path.exists() else info.get("filesize"),
        sha256=sha256,
        downloaded_at=info.get("_zget_downloaded_at"),
        source_id=source_id_from_url(str(url), fallback_id=str(info.get("id") or "")),
        uploader=info.get("uploader"),
        media_type=media_type,
        extra=merged_extra or None,
    )
