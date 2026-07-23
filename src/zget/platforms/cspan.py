"""
C-SPAN adapters.

Classic ``video/?…`` URLs work via yt-dlp. Public UVP pages often do not:

- ``/program/.../{id}`` — VOD units; public HLS at ``program/program.{id}.tsc.m3u8``
- ``/event/.../{id}`` — container pages; may list multiple programs (speech + Q&A).
  Event-level ``event/event.{id}.m3u8`` is often AccessDenied; real streams are
  the child **program** ids from ``GET /api/events/{id}/``.

Working approach (public HLS, no MyC-SPAN login for free streams):

1. Detect ``/program/`` or ``/event/`` URL
2. For events: call C-SPAN JSON API → child program ids (+ titles/dates)
3. For each program: prefer API/page ``contentUrl`` / m3u8, else CDN templates
4. Download HLS with C-SPAN Referer/Origin (fragments 403 without them)

``www.c-span.org`` is behind AWS WAF. When the API returns challenge/202, retry
with browser cookies (especially ``aws-waf-token``) if available.

Downstream download still uses yt-dlp on the resolved m3u8 so formats,
progress, and merge stay consistent with the rest of zget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
CSPAN_API = "https://www.c-span.org/api"

# https://www.c-span.org/program/some-slug/title-here/1234567
_PROGRAM_ID_RE = re.compile(
    r"(?:https?://)?(?:www\.)?c-span\.org/program/(?:[^/\s]+/){1,4}(\d{4,})",
    re.IGNORECASE,
)
# https://www.c-span.org/event/campaign-2026/title-here/444858
_EVENT_ID_RE = re.compile(
    r"(?:https?://)?(?:www\.)?c-span\.org/event/(?:[^/\s]+/){1,4}(\d{4,})",
    re.IGNORECASE,
)
_PROGRAM_PATH_RE = re.compile(r"c-span\.org/program/", re.IGNORECASE)
_EVENT_PATH_RE = re.compile(r"c-span\.org/event/", re.IGNORECASE)
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
_PROGRAM_DOT_RE = re.compile(r"program\.(\d{5,})", re.IGNORECASE)


@dataclass
class CspanProgramResolve:
    """Result of resolving a C-SPAN program (or one program under an event)."""

    page_url: str
    program_id: str
    m3u8_url: str
    title: str | None = None
    webpage_html_ok: bool = False
    event_id: str | None = None
    event_url: str | None = None
    upload_date: str | None = None  # YYYYMMDD when known
    kind: str = "program"  # program | event-program


@dataclass
class CspanEventResolve:
    """An event expanded to one or more downloadable programs."""

    event_url: str
    event_id: str
    title: str | None
    programs: list[CspanProgramResolve] = field(default_factory=list)


def is_cspan_program_url(url: str) -> bool:
    """True if URL looks like a C-SPAN /program/... page (not classic video/?)."""
    if not url:
        return False
    return bool(_PROGRAM_PATH_RE.search(url))


def is_cspan_event_url(url: str) -> bool:
    """True if URL looks like a C-SPAN /event/... page."""
    if not url:
        return False
    return bool(_EVENT_PATH_RE.search(url))


def is_cspan_hls_url(url: str) -> bool:
    """True for UVP pages that need zget HLS resolve (/program/ or /event/)."""
    return is_cspan_program_url(url) or is_cspan_event_url(url)


def extract_program_id(url: str) -> str | None:
    """Pull numeric program id from a C-SPAN program URL."""
    m = _PROGRAM_ID_RE.search(url.strip())
    if m:
        return m.group(1)
    if is_cspan_program_url(url):
        m = re.search(r"/(\d{5,})/?$", url.strip())
        return m.group(1) if m else None
    return None


def extract_event_id(url: str) -> str | None:
    """Pull numeric event id from a C-SPAN event URL."""
    m = _EVENT_ID_RE.search(url.strip())
    if m:
        return m.group(1)
    if is_cspan_event_url(url):
        m = re.search(r"/(\d{5,})/?$", url.strip())
        return m.group(1) if m else None
    return None


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


def _api_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": CSPAN_REFERER,
        "Accept-Language": "en-US,en;q=0.9",
    }


def _cdn_fallback_urls(program_id: str) -> list[str]:
    """Known public HLS templates for a program id (event streams are not reliable)."""
    hosts = ("m3u8-1", "m3u8-0", "m3u8-l")
    paths = (
        f"program/program.{program_id}.tsc.m3u8",
        f"program/program.{program_id}.m3u8",
    )
    return [f"https://{host}.c-spanvideo.org/{path}" for host in hosts for path in paths]


def _clean_cspan_title(title: str) -> str:
    """Strip common C-SPAN site suffixes from page titles."""
    title = title.strip()
    for sep in (" | C-SPAN.org", " | C-SPAN", " - C-SPAN", " | CSPAN", " | Video"):
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


def _iso_to_yyyymmdd(value: str | None) -> str | None:
    if not value:
        return None
    # 2026-07-09T00:00:00-04:00 or 2026-07-09
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    return None


def _m3u8_reachable(client: httpx.Client, m3u8: str) -> bool:
    try:
        resp = client.get(m3u8, headers=cspan_http_headers(), timeout=20.0)
        return resp.status_code == 200 and len(resp.content) > 0 and b"#EXT" in resp.content[:64]
    except Exception:
        return False


def _is_waf_blocked(resp: httpx.Response) -> bool:
    if resp.status_code == 202:
        return True
    if resp.headers.get("x-amzn-waf-action", "").lower() == "challenge":
        return True
    text = (resp.text or "")[:500].lower()
    return "challenge.js" in text or "gokuprops" in text or "awswaf" in text


def _cookies_from_browser(browser: str | None) -> dict[str, str]:
    """Best-effort extract of C-SPAN / WAF cookies from a local browser profile."""
    if not browser:
        return {}
    try:
        from yt_dlp.cookies import extract_cookies_from_browser

        jar = extract_cookies_from_browser(browser)
    except Exception:
        return {}

    out: dict[str, str] = {}
    for cookie in jar:
        domain = (cookie.domain or "").lstrip(".").lower()
        name = cookie.name or ""
        if name == "aws-waf-token" or domain.endswith("c-span.org") or "awswaf" in domain:
            out[name] = cookie.value
    return out


def _merge_cookie_maps(*maps: dict[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for m in maps:
        if m:
            merged.update(m)
    return merged


def _http_client(
    *,
    cookies: dict[str, str] | None = None,
    client: httpx.Client | None = None,
) -> tuple[httpx.Client, bool]:
    if client is not None:
        if cookies:
            client.cookies.update(cookies)
        return client, False
    return httpx.Client(follow_redirects=True, timeout=45.0, cookies=cookies or {}), True


def _first_reachable_m3u8(client: httpx.Client, candidates: list[str]) -> str | None:
    seen: set[str] = set()
    ordered: list[str] = []
    # Prefer program/ HLS over event/ (event often AccessDenied on free tier)
    prioritized = sorted(
        candidates,
        key=lambda u: (0 if "/program/" in u else 1, 0 if ".tsc.m3u8" in u else 1, u),
    )
    for c in prioritized:
        c = c.strip().rstrip("\\").rstrip("'\"")
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    for m3u8 in ordered:
        if _m3u8_reachable(client, m3u8):
            return m3u8
    return None


def resolve_program_m3u8(
    program_id: str,
    *,
    client: httpx.Client | None = None,
    page_url: str | None = None,
    extra_candidates: list[str] | None = None,
) -> str:
    """
    Resolve a reachable m3u8 for a numeric program id.

    Tries page HTML (if page_url), extra candidates, then CDN templates.
    """
    own_client = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=45.0)
    try:
        candidates: list[str] = list(extra_candidates or [])
        if page_url:
            try:
                resp = client.get(page_url, headers=_page_headers())
                if resp.status_code == 200 and resp.text and not _is_waf_blocked(resp):
                    html = resp.text
                    content = _CONTENT_URL_RE.search(html)
                    if content:
                        candidates.append(unquote(content.group(1)))
                    candidates.extend(_M3U8_RE.findall(html))
            except Exception:
                pass
        candidates.extend(_cdn_fallback_urls(program_id))
        found = _first_reachable_m3u8(client, candidates)
        if found:
            return found
        raise ValueError(
            f"No reachable HLS stream for C-SPAN program {program_id}"
            + (f" ({page_url})" if page_url else "")
        )
    finally:
        if own_client:
            client.close()


def resolve_cspan_program(
    program_url: str,
    *,
    client: httpx.Client | None = None,
    cookies: dict[str, str] | None = None,
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

    client, own = _http_client(cookies=cookies, client=client)
    try:
        candidates: list[str] = []
        title: str | None = None
        html_ok = False
        upload_date: str | None = None

        # Prefer JSON API (richer title/date) when WAF allows
        try:
            api = client.get(f"{CSPAN_API}/programs/{program_id}/", headers=_api_headers())
            if api.status_code == 200 and not _is_waf_blocked(api):
                data = api.json()
                title = data.get("title") or title
                upload_date = _iso_to_yyyymmdd(data.get("date"))
                vf = data.get("videoFile") or data.get("videofile")
                if isinstance(vf, str) and ".m3u8" in vf:
                    candidates.append(vf)
        except Exception:
            pass

        try:
            resp = client.get(program_url, headers=_page_headers())
            if resp.status_code == 200 and resp.text and not _is_waf_blocked(resp):
                html_ok = True
                html = resp.text
                title = title or _parse_title(html)
                content = _CONTENT_URL_RE.search(html)
                if content:
                    candidates.append(unquote(content.group(1)))
                candidates.extend(_M3U8_RE.findall(html))
        except Exception:
            pass

        m3u8 = resolve_program_m3u8(
            program_id,
            client=client,
            page_url=None,  # already scraped
            extra_candidates=candidates,
        )
        return CspanProgramResolve(
            page_url=program_url,
            program_id=program_id,
            m3u8_url=m3u8,
            title=title,
            webpage_html_ok=html_ok,
            upload_date=upload_date,
            kind="program",
        )
    finally:
        if own:
            client.close()


def _fetch_event_api(
    client: httpx.Client,
    event_id: str,
) -> dict[str, Any] | None:
    resp = client.get(f"{CSPAN_API}/events/{event_id}/", headers=_api_headers())
    if resp.status_code == 200 and not _is_waf_blocked(resp):
        try:
            return resp.json()
        except Exception:
            return None
    if _is_waf_blocked(resp):
        return None  # signal WAF; caller may retry with cookies
    return None


def resolve_cspan_event(
    event_url: str,
    *,
    client: httpx.Client | None = None,
    cookies: dict[str, str] | None = None,
    cookies_from_browser: str | None = None,
) -> CspanEventResolve:
    """
    Resolve a C-SPAN /event/ URL to one or more program streams.

    Event-level m3u8 URLs are often AccessDenied; child programs are the VOD.
    Multi-segment events (speech + presser) return multiple programs.

    Raises:
        ValueError: if event id missing, WAF-blocked without cookies, or no streams
    """
    event_url = event_url.strip()
    event_id = extract_event_id(event_url)
    if not event_id:
        raise ValueError(f"Could not parse C-SPAN event id from URL: {event_url}")

    cookie_map = _merge_cookie_maps(cookies, _cookies_from_browser(cookies_from_browser))
    client, own = _http_client(cookies=cookie_map or None, client=client)
    try:
        data = _fetch_event_api(client, event_id)

        # Retry once with browser cookies if first attempt was cookieless and failed
        if data is None and not cookie_map and cookies_from_browser is None:
            for browser in ("chrome", "chromium", "firefox", "safari", "edge"):
                browser_cookies = _cookies_from_browser(browser)
                if not browser_cookies:
                    continue
                client.cookies.update(browser_cookies)
                data = _fetch_event_api(client, event_id)
                if data is not None:
                    break

        if data is None:
            # Last resort: HTML scrape for program.NNNNN / program m3u8
            programs = _programs_from_event_html(client, event_url, event_id)
            if programs:
                return CspanEventResolve(
                    event_url=event_url,
                    event_id=event_id,
                    title=programs[0].title,
                    programs=programs,
                )
            raise ValueError(
                f"C-SPAN event {event_id} blocked or unreadable (AWS WAF / no program list). "
                f"Open https://www.c-span.org/ in a browser once, then retry with "
                f"--cookies-from chrome (needs aws-waf-token). "
                f"Or pass a /program/... URL if you already know the program id."
            )

        event_title = data.get("title")
        raw_programs = data.get("programs") or []
        if not raw_programs:
            raise ValueError(
                f"C-SPAN event {event_id} has no programs yet "
                f"(title={event_title!r}). Video may not be published as VOD."
            )

        resolved: list[CspanProgramResolve] = []
        for prog in raw_programs:
            pid = str(prog.get("id") or "").strip()
            if not pid.isdigit():
                continue
            path = prog.get("canonicalUrlPath") or f"/program/event/{pid}"
            if not path.startswith("http"):
                page = f"https://www.c-span.org{path}"
            else:
                page = path
            title = prog.get("title") or event_title
            upload_date = _iso_to_yyyymmdd(prog.get("time") or data.get("date"))
            # Optional per-program API for exact videoFile
            extra: list[str] = []
            try:
                pr = client.get(f"{CSPAN_API}/programs/{pid}/", headers=_api_headers())
                if pr.status_code == 200 and not _is_waf_blocked(pr):
                    pdata = pr.json()
                    title = pdata.get("title") or title
                    upload_date = _iso_to_yyyymmdd(pdata.get("date")) or upload_date
                    vf = pdata.get("videoFile") or pdata.get("videofile")
                    if isinstance(vf, str) and ".m3u8" in vf:
                        extra.append(vf)
            except Exception:
                pass

            try:
                m3u8 = resolve_program_m3u8(pid, client=client, extra_candidates=extra)
            except ValueError:
                continue

            resolved.append(
                CspanProgramResolve(
                    page_url=page,
                    program_id=pid,
                    m3u8_url=m3u8,
                    title=title,
                    webpage_html_ok=True,
                    event_id=event_id,
                    event_url=event_url,
                    upload_date=upload_date,
                    kind="event-program",
                )
            )

        if not resolved:
            raise ValueError(
                f"No reachable HLS streams for C-SPAN event {event_id} "
                f"({len(raw_programs)} program(s) listed)"
            )

        return CspanEventResolve(
            event_url=event_url,
            event_id=event_id,
            title=event_title,
            programs=resolved,
        )
    finally:
        if own:
            client.close()


def _programs_from_event_html(
    client: httpx.Client,
    event_url: str,
    event_id: str,
) -> list[CspanProgramResolve]:
    """Fallback: scrape program ids / m3u8 from event HTML (works only when WAF allows)."""
    try:
        resp = client.get(event_url, headers=_page_headers())
    except Exception:
        return []
    if resp.status_code != 200 or _is_waf_blocked(resp) or not resp.text:
        return []

    html = resp.text
    title = _parse_title(html)
    candidates = []
    content = _CONTENT_URL_RE.search(html)
    if content:
        candidates.append(unquote(content.group(1)))
    candidates.extend(_M3U8_RE.findall(html))

    program_ids: list[str] = []
    for m in _PROGRAM_DOT_RE.findall(html):
        if m not in program_ids:
            program_ids.append(m)
    for m in re.findall(r"/program/[^\"'\s]+/(\d{5,})", html):
        if m not in program_ids:
            program_ids.append(m)

    # Prefer program streams from page; ignore event/* m3u8 if programs found
    out: list[CspanProgramResolve] = []
    if program_ids:
        for pid in program_ids:
            try:
                m3u8 = resolve_program_m3u8(
                    pid,
                    client=client,
                    extra_candidates=[c for c in candidates if pid in c],
                )
            except ValueError:
                continue
            out.append(
                CspanProgramResolve(
                    page_url=event_url,
                    program_id=pid,
                    m3u8_url=m3u8,
                    title=title,
                    webpage_html_ok=True,
                    event_id=event_id,
                    event_url=event_url,
                    kind="event-program",
                )
            )
        return out

    # Only event m3u8 present — try it (usually fails AccessDenied)
    m3u8 = _first_reachable_m3u8(client, candidates)
    if m3u8 and "/program/" in m3u8:
        pid_m = _PROGRAM_DOT_RE.search(m3u8)
        pid = pid_m.group(1) if pid_m else event_id
        return [
            CspanProgramResolve(
                page_url=event_url,
                program_id=pid,
                m3u8_url=m3u8,
                title=title,
                webpage_html_ok=True,
                event_id=event_id,
                event_url=event_url,
                kind="event-program",
            )
        ]
    return []


def _resolve_to_meta(resolved: CspanProgramResolve) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "program_id": resolved.program_id,
        "program_url": resolved.page_url,
        "title": resolved.title,
        "m3u8_url": resolved.m3u8_url,
        "upload_date": resolved.upload_date,
        "_zget_cspan_program": True,
    }
    if resolved.event_id:
        meta["event_id"] = resolved.event_id
        meta["event_url"] = resolved.event_url
        meta["_zget_cspan_event"] = True
    return meta


def prepare_cspan_url(
    url: str,
    *,
    cookies_from_browser: str | None = None,
    cookies: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """
    If ``url`` is a C-SPAN /program/ or /event/ page, resolve to m3u8 and return
    ``(download_url, meta)``. Otherwise return ``(url, None)``.

    For multi-program **events**, returns the **first** program only. Use
    :func:`prepare_cspan_downloads` to get every program under an event.

    ``meta`` keys: program_id, program_url, title, m3u8_url, optional event_*
    """
    jobs = prepare_cspan_downloads(
        url, cookies_from_browser=cookies_from_browser, cookies=cookies
    )
    if not jobs:
        return url, None
    return jobs[0]


def prepare_cspan_downloads(
    url: str,
    *,
    cookies_from_browser: str | None = None,
    cookies: dict[str, str] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """
    Expand a C-SPAN UVP URL into one or more ``(m3u8_url, meta)`` download jobs.

    - ``/program/`` → single job
    - ``/event/`` → one job per child program (speech, presser, …)
    - other URLs → empty list
    """
    if is_cspan_program_url(url):
        resolved = resolve_cspan_program(
            url, cookies=cookies or _cookies_from_browser(cookies_from_browser)
        )
        return [(resolved.m3u8_url, _resolve_to_meta(resolved))]

    if is_cspan_event_url(url):
        event = resolve_cspan_event(
            url,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
        )
        return [(p.m3u8_url, _resolve_to_meta(p)) for p in event.programs]

    return []


def merge_cspan_meta(info: dict[str, Any], meta: dict[str, Any] | None) -> dict[str, Any]:
    """Attach original program/event page identity onto a yt-dlp info dict."""
    if not meta:
        return info
    info = dict(info)
    page = meta.get("program_url") or meta.get("event_url")
    info["webpage_url"] = page or info.get("webpage_url")
    info["original_url"] = meta.get("event_url") or page or info.get("original_url")
    info["id"] = meta.get("program_id") or info.get("id")
    info["extractor"] = "cspan-event" if meta.get("event_id") else "cspan-program"
    info["extractor_key"] = "CspanEvent" if meta.get("event_id") else "CspanProgram"
    if meta.get("upload_date") and not info.get("upload_date"):
        info["upload_date"] = meta["upload_date"]
    if meta.get("event_id"):
        info["playlist_id"] = meta["event_id"]
        info["playlist_title"] = meta.get("title")
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
    if meta.get("event_id"):
        info["_zget_cspan_event"] = True
        info["_zget_cspan_event_id"] = meta.get("event_id")
    return info
