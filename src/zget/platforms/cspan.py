"""
C-SPAN adapters.

Classic ``video/?…`` and many C-SPAN URLs work via yt-dlp. Public
``/program/.../{id}`` pages often do not: yt-dlp reports unsupported URL.

Working approach (public HLS, no MyC-SPAN login for free streams):

1. Fetch the program HTML page
2. Prefer JSON-LD ``contentUrl`` / in-page ``*.m3u8`` links
3. Fall back to known CDN templates for the program id
4. Download the HLS stream with C-SPAN Referer/Origin headers (required;
   fragment requests 403 without them)

Downstream download still uses yt-dlp on the resolved m3u8 so formats,
progress, and merge stay consistent with the rest of zget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import unquote

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

CSPAN_REFERER = "https://www.c-span.org/"
CSPAN_ORIGIN = "https://www.c-span.org"

# https://www.c-span.org/program/some-slug/title-here/1234567
_PROGRAM_ID_RE = re.compile(
    r"(?:https?://)?(?:www\.)?c-span\.org/program/(?:[^/\s]+/){1,4}(\d{4,})",
    re.IGNORECASE,
)
_PROGRAM_PATH_RE = re.compile(r"c-span\.org/program/", re.IGNORECASE)
_M3U8_RE = re.compile(r"https://[^\s\"'<>]+\.m3u8[^\s\"'<>]*", re.IGNORECASE)
_CONTENT_URL_RE = re.compile(
    r'"contentUrl"\s*:\s*"(https://[^"]+\.m3u8[^"]*)"',
    re.IGNORECASE,
)
_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TITLE_TAG_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)


@dataclass
class CspanProgramResolve:
    """Result of resolving a C-SPAN /program/ page to a downloadable stream."""

    program_url: str
    program_id: str
    m3u8_url: str
    title: str | None = None
    webpage_html_ok: bool = False


def is_cspan_program_url(url: str) -> bool:
    """True if URL looks like a C-SPAN /program/... page (not classic video/?)."""
    if not url:
        return False
    if not _PROGRAM_PATH_RE.search(url):
        return False
    # Exclude non-program media paths if any
    return True


def extract_program_id(url: str) -> str | None:
    """Pull numeric program id from a C-SPAN program URL."""
    m = _PROGRAM_ID_RE.search(url.strip())
    if m:
        return m.group(1)
    # trailing /NNNNN
    m = re.search(r"/(\d{5,})/?$", url.strip())
    return m.group(1) if m else None


def cspan_http_headers() -> dict[str, str]:
    """Headers required for C-SPAN CDN HLS (Referer is mandatory)."""
    return {
        "User-Agent": USER_AGENT,
        "Referer": CSPAN_REFERER,
        "Origin": CSPAN_ORIGIN,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _page_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _cdn_fallback_urls(program_id: str) -> list[str]:
    return [
        f"https://m3u8-0.c-spanvideo.org/program/program.{program_id}.tsc.m3u8",
        f"https://m3u8-1.c-spanvideo.org/program/program.{program_id}.m3u8",
        f"https://m3u8-0.c-spanvideo.org/program/program.{program_id}.m3u8",
        f"https://m3u8-1.c-spanvideo.org/program/program.{program_id}.tsc.m3u8",
    ]


def _clean_cspan_title(title: str) -> str:
    """Strip common C-SPAN site suffixes from page titles."""
    title = title.strip()
    for sep in (" | C-SPAN.org", " | C-SPAN", " - C-SPAN", " | CSPAN"):
        idx = title.lower().find(sep.lower())
        if idx > 0:
            return title[:idx].strip()
    return title


def _parse_title(html: str) -> str | None:
    m = _OG_TITLE_RE.search(html)
    if m:
        title = _clean_cspan_title(unescape(m.group(1)))
        return title or None
    m = _TITLE_TAG_RE.search(html)
    if m:
        title = _clean_cspan_title(unescape(m.group(1)))
        return title or None
    return None


def _m3u8_reachable(client: httpx.Client, m3u8: str) -> bool:
    try:
        resp = client.get(m3u8, headers=cspan_http_headers(), timeout=20.0)
        return resp.status_code == 200 and len(resp.content) > 0
    except Exception:
        return False


def resolve_cspan_program(
    program_url: str,
    *,
    client: httpx.Client | None = None,
) -> CspanProgramResolve:
    """
    Resolve a C-SPAN /program/ URL to a working m3u8.

    Raises:
        ValueError: if program id missing or no reachable stream
    """
    program_url = program_url.strip()
    program_id = extract_program_id(program_url)
    if not program_id:
        raise ValueError(f"Could not parse C-SPAN program id from URL: {program_url}")

    own_client = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=45.0)
    try:
        candidates: list[str] = []
        title: str | None = None
        html_ok = False

        try:
            resp = client.get(program_url, headers=_page_headers())
            if resp.status_code == 200 and resp.text:
                html_ok = True
                html = resp.text
                title = _parse_title(html)
                content = _CONTENT_URL_RE.search(html)
                if content:
                    candidates.append(unquote(content.group(1)))
                candidates.extend(_M3U8_RE.findall(html))
        except Exception:
            pass

        candidates.extend(_cdn_fallback_urls(program_id))

        seen: set[str] = set()
        ordered: list[str] = []
        for c in candidates:
            c = c.strip().rstrip("\\").rstrip("'\"")
            if c and c not in seen:
                seen.add(c)
                ordered.append(c)

        for m3u8 in ordered:
            if _m3u8_reachable(client, m3u8):
                return CspanProgramResolve(
                    program_url=program_url,
                    program_id=program_id,
                    m3u8_url=m3u8,
                    title=title,
                    webpage_html_ok=html_ok,
                )

        raise ValueError(
            f"No reachable HLS stream for C-SPAN program {program_id} ({program_url})"
        )
    finally:
        if own_client:
            client.close()


def prepare_cspan_url(url: str) -> tuple[str, dict[str, Any] | None]:
    """
    If ``url`` is a C-SPAN /program/ page, resolve to m3u8 and return
    ``(download_url, meta)``. Otherwise return ``(url, None)``.

    ``meta`` keys: program_id, program_url, title, m3u8_url
    """
    if not is_cspan_program_url(url):
        return url, None
    resolved = resolve_cspan_program(url)
    meta = {
        "program_id": resolved.program_id,
        "program_url": resolved.program_url,
        "title": resolved.title,
        "m3u8_url": resolved.m3u8_url,
        "_zget_cspan_program": True,
    }
    return resolved.m3u8_url, meta


def merge_cspan_meta(info: dict[str, Any], meta: dict[str, Any] | None) -> dict[str, Any]:
    """Attach original program page identity onto a yt-dlp info dict."""
    if not meta:
        return info
    info = dict(info)
    info["webpage_url"] = meta.get("program_url") or info.get("webpage_url")
    info["original_url"] = meta.get("program_url") or info.get("original_url")
    info["id"] = meta.get("program_id") or info.get("id")
    info["extractor"] = "cspan-program"
    info["extractor_key"] = "CspanProgram"
    existing_title = str(info.get("title") or "")
    looks_like_stream_id = (
        not existing_title
        or existing_title in ("", "unknown", str(meta.get("m3u8_url") or ""))
        or existing_title.endswith(".m3u8")
        or existing_title.startswith("program.")
        or existing_title.endswith(".tsc")
    )
    if meta.get("title") and looks_like_stream_id:
        info["title"] = meta["title"]
    info["_zget_cspan_program"] = True
    info["_zget_cspan_m3u8"] = meta.get("m3u8_url")
    return info
