"""Capture identity: a real title and a citable URL for every capture.

A capture whose title is the streaming server's filename is unusable later: it
does not say what the media is, and the URL stored beside it points at a CDN
path instead of a page anyone can open. Three real capture failures motivated
this module, each noticed long after the download rather than at capture time:

- a C-SPAN program behind the WAF kept ``program.674647.tsc`` (the HLS stem)
  as its title, because neither the API nor the page could be read;
- twelve Sinclair station clips captured from CDN asset URLs kept ``index``
  (the HLS playlist filename) as their title, and recorded the CDN asset as
  their source URL, which no reader can visit and which rots;
- station captures with no uploader produced ``NA`` where the publisher goes.

Every function here is pure and derives from the URL the operator already
supplied. Nothing is invented: a de-slugged title is the publisher's own slug,
and it is always labelled as derived (``title_source``) so a reader can tell it
apart from a title the publisher actually served.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Filenames streaming servers use, which yt-dlp lifts as the title when a page
# is not involved. None of these identifies a source.
_ARTIFACT_STEMS = frozenset(
    {
        "index",
        "master",
        "playlist",
        "chunklist",
        "manifest",
        "stream",
        "video",
        "audio",
        "media",
        "output",
        "untitled",
        "unknown",
        "na",
    }
)

# ``program.674647.tsc`` and friends: a stream id wearing a title's clothes.
_STREAM_ID_RE = re.compile(r"^(?:program|clip|event)[._-]?\d{3,}(?:\.\w+)?$", re.IGNORECASE)
_ASSET_SUFFIXES = (".m3u8", ".mpd", ".ts", ".tsc", ".mp4", ".m4a", ".mp3")

# Path segments that carry no title: dates, ids, and site furniture.
_NOISE_SEGMENTS = frozenset(
    {
        "video",
        "videos",
        "watch",
        "news",
        "live",
        "live-dvr",
        "program",
        "event",
        "media",
        "clips",
        "embed",
        "player",
    }
)
def _is_timestamp_segment(segment: str) -> bool:
    """True for ``2026``, ``07``, ``2026-07-22T21:59:59.173Z`` and the like.

    Digits and date punctuation only, allowing the ISO ``T`` and ``Z`` markers.
    A slug that carries any other letter (``9-11-remembrance``) is a title.
    """
    remainder = re.sub(r"[\d\-:.]", "", segment)
    return bool(segment) and set(remainder.upper()) <= {"T", "Z"}



_UUID_SEGMENT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

# Words a slug lower-cases that a title should not.
_SLUG_UPPER = {"us", "uk", "nc", "me", "dc", "eu", "un", "fbi", "cia", "ice", "gop", "tv"}
_SLUG_LOWER = {"a", "an", "and", "as", "at", "for", "in", "of", "on", "or", "the", "to", "with"}


def is_stream_artifact_title(title: str | None) -> bool:
    """True when a title is a streaming filename rather than a source name.

    Args:
        title: Candidate title, typically what yt-dlp reported.

    Returns:
        True when the title identifies nothing (empty, a playlist filename, a
        stream id, or a bare media filename).
    """
    stem = (title or "").strip()
    if not stem:
        return True
    low = stem.lower()
    if low.endswith(_ASSET_SUFFIXES):
        low = low.rsplit(".", 1)[0]
    if low in _ARTIFACT_STEMS:
        return True
    if _STREAM_ID_RE.match(stem):
        return True
    return bool(re.fullmatch(r"[\d\W_]+", stem))


def is_raw_asset_url(url: str) -> bool:
    """True when a URL points straight at media, with no page to cite.

    Args:
        url: The URL being captured.

    Returns:
        True for ``.m3u8`` / ``.mpd`` / bare media paths, which carry a
        stream filename instead of a title and cannot be cited by a reader.
    """
    path = (urlparse(url or "").path or "").lower()
    return path.endswith((".m3u8", ".mpd", ".ts", ".tsc"))


def _deslug(segment: str) -> str:
    words = [w for w in re.split(r"[-_]+", segment) if w]
    out: list[str] = []
    for i, word in enumerate(words):
        low = word.lower()
        if low in _SLUG_UPPER:
            out.append(low.upper())
        elif low in _SLUG_LOWER and i > 0:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def title_from_url(url: str, min_words: int = 3) -> str | None:
    """Recover a title from the publisher's own URL slug.

    The longest hyphenated path segment is the title slug on every publisher
    layout we capture from: C-SPAN ``/program/<category>/<title>/<id>``, station
    articles ``/2026/07/13/<title>``, and Sinclair ``/news/local/<title>``.

    Args:
        url: Page URL the capture came from.
        min_words: Reject slugs shorter than this, which are categories.

    Returns:
        The de-slugged title, or None when the URL carries no title slug.
        Capitalisation is the slug's, not the publisher's, so callers must
        record the result as derived.
    """
    try:
        segments = [s for s in (urlparse(url or "").path or "").split("/") if s]
    except ValueError:
        return None
    best = ""
    for raw in segments:
        seg = raw.rsplit(".", 1)[0] if raw.lower().endswith(_ASSET_SUFFIXES) else raw
        low = seg.lower()
        if low in _NOISE_SEGMENTS or _is_timestamp_segment(seg) or _UUID_SEGMENT_RE.match(seg):
            continue
        if len([w for w in re.split(r"[-_]+", seg) if w]) < min_words:
            continue
        if len(seg) > len(best):
            best = seg
    return _deslug(best) if best else None


def publisher_from_url(url: str) -> str | None:
    """The publisher's domain, for captures that report no uploader.

    Args:
        url: Page or asset URL.

    Returns:
        The registrable domain (``wabi.tv``), which is verifiable, or None.
        Deliberately not a station's display name: that would be a guess.
    """
    host = (urlparse(url or "").hostname or "").lower()
    if not host:
        return None
    host = host.removeprefix("www.")
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 else host or None


def resolve_title(
    reported: str | None,
    *,
    operator: str | None = None,
    page_url: str | None = None,
) -> tuple[str | None, str]:
    """Pick the best available title and say where it came from.

    Args:
        reported: Title the extractor reported, if any.
        operator: Title the operator passed explicitly, which always wins.
        page_url: Page URL to de-slug when the reported title is an artifact.

    Returns:
        ``(title, title_source)`` where title_source is ``operator``,
        ``publisher``, ``url-slug``, or ``unresolved`` (title None).
    """
    if operator and operator.strip():
        return operator.strip(), "operator"
    if not is_stream_artifact_title(reported):
        return (reported or "").strip(), "publisher"
    slug = title_from_url(page_url or "")
    if slug:
        return slug, "url-slug"
    return None, "unresolved"
