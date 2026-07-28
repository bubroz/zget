"""Tests for capture identity.

The cases are three real capture failures, each caught by hand long after the
download because nothing checks a title or a URL at capture time.
"""

from __future__ import annotations

import pytest

from zget.metadata.identity import (
    is_raw_asset_url,
    is_stream_artifact_title,
    publisher_from_url,
    resolve_title,
    title_from_url,
)

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
WABI_PAGE = "https://www.wabi.tv/2026/07/13/dr-nirav-shah-holds-town-hall-bangor"


@pytest.mark.parametrize(
    "title",
    [
        "program.674647.tsc",  # the C-SPAN defect
        "index",  # the Sinclair defect
        "index.m3u8",
        "master",
        "playlist",
        "",
        "   ",
        None,
        "674647",
    ],
)
def test_artifact_titles_are_recognised(title):
    assert is_stream_artifact_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "Roy Cooper Primary Night Victory Remarks",
        "Political Brew | ICE cooperation, Collins' voting record",
        "I'm Running for U.S. Senate",
        "Video Diary: One Day in Bangor",  # contains an artifact word, is not one
    ],
)
def test_real_titles_survive(title):
    assert not is_stream_artifact_title(title)


def test_cspan_slug_recovers_the_program_title():
    assert title_from_url(CSPAN_URL) == "Roy Cooper Primary Night Victory Remarks"


def test_station_article_slug_recovers_the_headline():
    assert title_from_url(WABI_PAGE) == "Dr Nirav Shah Holds Town Hall Bangor"


def test_slug_skips_dates_ids_and_furniture():
    # Nothing but a date, a UUID and site furniture: no title to recover.
    assert title_from_url(SINCLAIR_ASSET) is None


def test_slug_rejects_short_category_segments():
    assert title_from_url("https://wgme.com/news/local/") is None


def test_raw_asset_urls_are_flagged():
    assert is_raw_asset_url(SINCLAIR_ASSET)
    assert is_raw_asset_url("https://m3u8-0.c-spanvideo.org/program/program.674647.tsc.m3u8")
    assert not is_raw_asset_url(CSPAN_URL)
    assert not is_raw_asset_url("https://www.youtube.com/watch?v=abc123")


def test_publisher_falls_back_to_the_verifiable_domain():
    assert publisher_from_url(WABI_PAGE) == "wabi.tv"
    assert publisher_from_url(SINCLAIR_ASSET) == "sinclairstoryline.com"
    assert publisher_from_url("not a url") is None


def test_resolve_prefers_the_publisher_then_the_slug():
    assert resolve_title("Roy Cooper Wins", page_url=CSPAN_URL) == (
        "Roy Cooper Wins",
        "publisher",
    )
    # The exact C-SPAN failure: WAF blocked the title, the slug carries it.
    assert resolve_title("program.674647.tsc", page_url=CSPAN_URL) == (
        "Roy Cooper Primary Night Victory Remarks",
        "url-slug",
    )


def test_resolve_lets_the_operator_win():
    title, source = resolve_title(
        "index",
        operator="'He's a Bernie Bro': Sen. Collins addresses likely Democratic challenger",
        page_url=SINCLAIR_PAGE,
    )
    assert source == "operator"
    assert title.startswith("'He's a Bernie Bro'")


def test_resolve_reports_unresolved_rather_than_inventing():
    assert resolve_title("index", page_url=SINCLAIR_ASSET) == (None, "unresolved")
