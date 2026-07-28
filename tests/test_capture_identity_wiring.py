"""Capture identity, wired: the three 2026-07-27 defects must not recur.

These exercise the paths that actually produced the bad captures, not just the
pure helpers: the C-SPAN meta chokepoint that names the file, the raw-asset
guard that refuses an uncitable capture, and the sidecar that has to record a
citable URL and say where the title came from.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zget.core import _cspan_outtmpl, _identity_outtmpl, download
from zget.metadata.librarian_json import generate_librarian_json_from_info
from zget.platforms.cspan import CspanProgramResolve, _resolve_to_meta

CSPAN_URL = (
    "https://www.c-span.org/program/campaign-2026/"
    "roy-cooper-primary-night-victory-remarks/674647"
)
SINCLAIR_ASSET = (
    "https://harvest-media-clips.sinclairstoryline.com/WGME/"
    "2026-07-22T21:59:59.173Z/a2d3cc90-5018-4425-a8ca-90aa221bcb1d/index.m3u8"
)
SINCLAIR_PAGE = (
    "https://wgme.com/news/local/"
    "hes-a-bernie-bro-senator-susan-collins-addresses-likely-democratic-challenger-troy-jackson"
)


def _blocked_program() -> CspanProgramResolve:
    """What the resolver returns when the WAF blocks the API and the page."""
    return CspanProgramResolve(
        page_url=CSPAN_URL,
        program_id="674647",
        m3u8_url="https://m3u8-0.c-spanvideo.org/program/program.674647.tsc.m3u8",
        title=None,
        webpage_html_ok=False,
        upload_date="20260304",
    )


def test_cspan_meta_recovers_a_title_when_the_waf_blocks_everything():
    meta = _resolve_to_meta(_blocked_program())
    assert meta["title"] == "Roy Cooper Primary Night Victory Remarks"
    assert meta["title_source"] == "url-slug"


def test_cspan_filename_is_no_longer_the_hls_stem(tmp_path: Path):
    meta = _resolve_to_meta(_blocked_program())
    tmpl = _cspan_outtmpl(tmp_path, meta)
    assert "program.674647.tsc" not in tmpl
    assert "20260304_C-SPAN_Roy Cooper Primary Night Victory Remarks" in tmpl


def test_cspan_meta_keeps_a_served_title_and_says_so():
    resolved = _blocked_program()
    resolved.title = "Roy Cooper Primary Night Victory Remarks"
    meta = _resolve_to_meta(resolved)
    assert meta["title_source"] == "publisher"


def test_raw_asset_capture_is_refused_before_any_bytes_are_spent():
    with pytest.raises(ValueError) as exc:
        download(SINCLAIR_ASSET, output_dir="/tmp/zget-test-should-not-be-written")
    message = str(exc.value)
    assert "index" in message
    assert "--title" in message and "--source-url" in message


def test_raw_asset_capture_accepts_a_page_url_it_can_deslug(monkeypatch, tmp_path: Path):
    seen: dict = {}

    def fake_download_one(url, **kwargs):
        seen.update(kwargs)
        seen["url"] = url
        return {"title": kwargs.get("title")}

    monkeypatch.setattr("zget.core._download_one", fake_download_one)
    download(SINCLAIR_ASSET, output_dir=tmp_path, source_url=SINCLAIR_PAGE)

    # No --title given, but the article URL carries the headline slug.
    assert seen["title"].startswith("Hes a Bernie Bro")
    assert seen["source_url"] == SINCLAIR_PAGE


def test_identity_filename_uses_the_publisher_not_NA(tmp_path: Path):
    tmpl = _identity_outtmpl(tmp_path, title="Delegates arrive to vote", channel="wabi.tv")
    assert "_wabi.tv_Delegates arrive to vote." in tmpl
    assert "NA_NA" not in tmpl


def test_sidecar_records_the_citable_page_and_the_asset_it_came_from(tmp_path: Path):
    media = tmp_path / "20260722_WGME_Bernie Bro.mp4"
    media.write_bytes(b"\x00")
    info = {
        "title": "'He's a Bernie Bro': Sen. Collins addresses Troy Jackson",
        "_zget_platform": "generic",
        "_zget_source_url": SINCLAIR_PAGE,
        "_zget_asset_url": SINCLAIR_ASSET,
        "_zget_title_source": "operator",
        "url": SINCLAIR_ASSET,
        "uploader": "wgme.com",
        "upload_date": "20260722",
    }
    side = generate_librarian_json_from_info(media, info, sha256="deadbeef")
    payload = json.loads(side.read_text())

    assert payload["url"] == SINCLAIR_PAGE  # what a reader can visit
    assert payload["asset_url"] == SINCLAIR_ASSET  # what was actually fetched
    assert payload["title_source"] == "operator"
    assert payload["title"].startswith("'He's a Bernie Bro'")
