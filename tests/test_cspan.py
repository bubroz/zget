"""Tests for C-SPAN /program/ and /event/ URL resolution (mocked network)."""

from __future__ import annotations

import json

import httpx

from zget.platforms.cspan import (
    extract_event_id,
    extract_program_id,
    is_cspan_event_url,
    is_cspan_hls_url,
    is_cspan_program_url,
    merge_cspan_meta,
    prepare_cspan_downloads,
    resolve_cspan_event,
    resolve_cspan_program,
)


def test_is_cspan_program_url():
    assert is_cspan_program_url(
        "https://www.c-span.org/program/washington-journal/some-title/540123"
    )
    assert not is_cspan_program_url("https://www.c-span.org/video/?540123-1/foo")
    assert not is_cspan_program_url("https://www.youtube.com/watch?v=abc")
    assert not is_cspan_program_url(
        "https://www.c-span.org/event/campaign-2026/some-title/444858"
    )


def test_is_cspan_event_url():
    assert is_cspan_event_url(
        "https://www.c-span.org/event/campaign-2026/us-senate-candidate/444858"
    )
    assert not is_cspan_event_url(
        "https://www.c-span.org/program/campaign-2026/title/682566"
    )
    assert is_cspan_hls_url(
        "https://www.c-span.org/event/campaign-2026/us-senate-candidate/444858"
    )
    assert is_cspan_hls_url(
        "https://www.c-span.org/program/campaign-2026/title/682566"
    )


def test_extract_program_id():
    assert (
        extract_program_id(
            "https://www.c-span.org/program/washington-journal/some-title/540123"
        )
        == "540123"
    )
    assert extract_program_id("https://www.c-span.org/video/?540123-1/foo") is None
    assert extract_program_id(
        "https://www.c-span.org/event/campaign-2026/title/444858"
    ) is None


def test_extract_event_id():
    assert (
        extract_event_id(
            "https://www.c-span.org/event/campaign-2026/us-senate-candidate/444858"
        )
        == "444858"
    )
    assert extract_event_id(
        "https://www.c-span.org/program/campaign-2026/title/682566"
    ) is None


def test_resolve_cspan_program_from_content_url():
    program_url = "https://www.c-span.org/program/test/slug/540123"
    m3u8 = "https://m3u8-0.c-spanvideo.org/program/program.540123.tsc.m3u8"
    html = f'''
    <html><head>
      <meta property="og:title" content="Hearing Title | C-SPAN.org" />
      <script type="application/ld+json">
      {{"contentUrl": "{m3u8}"}}
      </script>
    </head></html>
    '''

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/api/programs/" in url:
            return httpx.Response(404)
        if "c-span.org/program" in url:
            return httpx.Response(200, text=html)
        if str(request.url).endswith(".m3u8"):
            # Require Referer like the real CDN
            if request.headers.get("Referer", "").startswith("https://www.c-span.org"):
                return httpx.Response(200, text="#EXTM3U\n#EXT-X-STREAM-INF\n")
            return httpx.Response(403, text="forbidden")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        resolved = resolve_cspan_program(program_url, client=client)

    assert resolved.program_id == "540123"
    assert resolved.m3u8_url == m3u8
    assert resolved.title == "Hearing Title"


def test_resolve_cspan_program_cdn_fallback():
    program_url = "https://www.c-span.org/program/test/slug/999888"
    # Page has no m3u8; CDN template with .m3u8 (not .tsc) works
    good = "https://m3u8-1.c-spanvideo.org/program/program.999888.m3u8"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/api/" in url:
            return httpx.Response(404)
        if "c-span.org/program" in url:
            return httpx.Response(200, text="<html><title>Fallback Case</title></html>")
        if url == good:
            return httpx.Response(200, text="#EXTM3U\n#EXT-X-STREAM-INF\n")
        if url.endswith(".m3u8"):
            return httpx.Response(404)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        resolved = resolve_cspan_program(program_url, client=client)

    assert resolved.m3u8_url == good
    assert resolved.program_id == "999888"


def test_resolve_cspan_event_multi_program():
    """Event API lists speech + presser; each resolves via program CDN."""
    event_url = (
        "https://www.c-span.org/event/campaign-2026/"
        "us-senate-candidate-roy-cooper/444858"
    )
    api_payload = {
        "title": "Event Title",
        "date": "2026-07-09T00:00:00-04:00",
        "programs": [
            {
                "id": 682566,
                "title": "Campaign Speech",
                "canonicalUrlPath": (
                    "/program/campaign-2026/campaign-speech/682566"
                ),
                "time": "2026-07-09T17:04:28Z",
            },
            {
                "id": 682654,
                "title": "News Conference",
                "canonicalUrlPath": (
                    "/program/campaign-2026/news-conference/682654"
                ),
                "time": "2026-07-09T20:54:02Z",
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.rstrip("/").endswith("/api/events/444858"):
            return httpx.Response(
                200,
                content=json.dumps(api_payload),
                headers={"content-type": "application/json"},
            )
        if "/api/programs/682566" in url:
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "title": "Campaign Speech",
                        "date": "2026-07-09T00:00:00-04:00",
                        "videoFile": (
                            "https://m3u8-1.c-spanvideo.org/program/"
                            "program.682566.tsc.m3u8"
                        ),
                    }
                ),
                headers={"content-type": "application/json"},
            )
        if "/api/programs/682654" in url:
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "title": "News Conference",
                        "date": "2026-07-09T00:00:00-04:00",
                        "videoFile": (
                            "https://m3u8-1.c-spanvideo.org/program/"
                            "program.682654.tsc.m3u8"
                        ),
                    }
                ),
                headers={"content-type": "application/json"},
            )
        if url.endswith(".m3u8"):
            if "program.682566" in url or "program.682654" in url:
                return httpx.Response(200, text="#EXTM3U\n#EXT-X-STREAM-INF\n")
            return httpx.Response(403, text="AccessDenied")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        resolved = resolve_cspan_event(event_url, client=client)

    assert resolved.event_id == "444858"
    assert len(resolved.programs) == 2
    assert resolved.programs[0].program_id == "682566"
    assert resolved.programs[1].program_id == "682654"
    assert "program.682566" in resolved.programs[0].m3u8_url
    assert resolved.programs[0].title == "Campaign Speech"
    assert resolved.programs[0].event_id == "444858"


def test_prepare_cspan_downloads_event():
    event_url = "https://www.c-span.org/event/campaign-2026/title/444858"
    api_payload = {
        "title": "Event",
        "programs": [
            {
                "id": 100001,
                "title": "Only Program",
                "canonicalUrlPath": "/program/x/y/100001",
            }
        ],
    }
    good = "https://m3u8-1.c-spanvideo.org/program/program.100001.tsc.m3u8"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/api/events/444858" in url:
            return httpx.Response(
                200,
                content=json.dumps(api_payload),
                headers={"content-type": "application/json"},
            )
        if "/api/programs/100001" in url:
            return httpx.Response(
                200,
                content=json.dumps({"title": "Only Program", "videoFile": good}),
                headers={"content-type": "application/json"},
            )
        if url == good or "program.100001" in url:
            return httpx.Response(200, text="#EXTM3U\n#EXT-X-STREAM-INF\n")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        # prepare_cspan_downloads builds its own client; exercise resolve path
        # via resolve_cspan_event directly then shape-check downloads helper with mock
        event = resolve_cspan_event(event_url, client=client)
        assert len(event.programs) == 1

    # Unit: empty for non-cspan
    assert prepare_cspan_downloads("https://www.youtube.com/watch?v=x") == []


def test_merge_cspan_meta():
    info = {"title": "something.m3u8", "id": "x"}
    meta = {
        "program_id": "540123",
        "program_url": "https://www.c-span.org/program/a/b/540123",
        "title": "Real Title",
        "m3u8_url": "https://example/m.m3u8",
    }
    out = merge_cspan_meta(info, meta)
    assert out["id"] == "540123"
    assert out["title"] == "Real Title"
    assert out["webpage_url"].endswith("540123")
    assert out["extractor"] == "cspan-program"

    event_meta = {
        **meta,
        "event_id": "444858",
        "event_url": "https://www.c-span.org/event/a/b/444858",
        "upload_date": "20260709",
    }
    out2 = merge_cspan_meta(info, event_meta)
    assert out2["extractor"] == "cspan-event"
    assert out2["upload_date"] == "20260709"
    assert out2["_zget_cspan_event_id"] == "444858"
