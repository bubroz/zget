"""Tests for C-SPAN /program/ URL resolution (mocked network)."""

from __future__ import annotations

import httpx

from zget.platforms.cspan import (
    extract_program_id,
    is_cspan_program_url,
    merge_cspan_meta,
    resolve_cspan_program,
)


def test_is_cspan_program_url():
    assert is_cspan_program_url(
        "https://www.c-span.org/program/washington-journal/some-title/540123"
    )
    assert not is_cspan_program_url("https://www.c-span.org/video/?540123-1/foo")
    assert not is_cspan_program_url("https://www.youtube.com/watch?v=abc")


def test_extract_program_id():
    assert (
        extract_program_id(
            "https://www.c-span.org/program/washington-journal/some-title/540123"
        )
        == "540123"
    )
    assert extract_program_id("https://www.c-span.org/video/?540123-1/foo") is None


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
        if "c-span.org/program" in str(request.url):
            return httpx.Response(200, text=html)
        if str(request.url).endswith(".m3u8"):
            # Require Referer like the real CDN
            if request.headers.get("Referer", "").startswith("https://www.c-span.org"):
                return httpx.Response(200, text="#EXTM3U\n")
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
        if "c-span.org/program" in url:
            return httpx.Response(200, text="<html><title>Fallback Case</title></html>")
        if url == good:
            return httpx.Response(200, text="#EXTM3U\n")
        if url.endswith(".m3u8"):
            return httpx.Response(404)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        resolved = resolve_cspan_program(program_url, client=client)

    assert resolved.m3u8_url == good
    assert resolved.program_id == "999888"


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
