"""Regional collections for zget.

Provides geographic filtering for the site registry, enabling users to
discover video sites by region (Japan, Russia, LATAM, etc.) with health status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Paths - go up 3 levels: regions.py -> zget/ -> src/ -> project_root/
DATA_DIR = Path(__file__).parent.parent.parent / "data"
REGIONS_PATH = DATA_DIR / "regions.json"
REGISTRY_PATH = DATA_DIR / "enriched_registry.json"
HEALTH_LOG_PATH = DATA_DIR / "health_log.json"


@dataclass
class Region:
    """A regional collection of sites."""

    id: str
    name: str
    emoji: str
    countries: list[str]
    notes: Optional[str]


@dataclass
class SiteInfo:
    """A site with its metadata and health status."""

    name: str
    country: str
    category: str
    description: Optional[str]
    status: str  # "working", "failed", "geo-blocked", "untested"
    test_url: Optional[str]
    is_adult: bool


@dataclass
class RegionSummary:
    """Summary statistics for a region."""

    region: Region
    site_count: int
    working: int
    failed: int
    untested: int


def load_regions() -> dict[str, Region]:
    """Load all regional collections from regions.json."""
    if not REGIONS_PATH.exists():
        return {}

    with open(REGIONS_PATH) as f:
        data = json.load(f)

    return {
        region_id: Region(
            id=region_id,
            name=info["name"],
            emoji=info["emoji"],
            countries=info["countries"],
            notes=info.get("notes"),
        )
        for region_id, info in data.items()
    }


def load_registry() -> dict:
    """Load the enriched registry."""
    if not REGISTRY_PATH.exists():
        return {}

    with open(REGISTRY_PATH) as f:
        return json.load(f)


def load_health_log() -> dict:
    """Load smokescreen health results from health_log.json."""
    if not HEALTH_LOG_PATH.exists():
        return {}

    with open(HEALTH_LOG_PATH) as f:
        return json.load(f)


def get_sites_for_region(region_id: str) -> list[SiteInfo]:
    """Get all sites belonging to a region with their health status."""
    regions = load_regions()
    if region_id not in regions:
        return []

    region = regions[region_id]
    registry = load_registry()
    health_log = load_health_log()

    sites = []
    for site_name, site_data in registry.items():
        site_country = site_data.get("country", "Unknown")

        if site_country in region.countries:
            # Determine status from health_log (smokescreen results)
            if site_name in health_log:
                health_status = health_log[site_name].get("status", "unknown")
                # Map health_log statuses to display statuses
                if health_status == "ok":
                    status = "working"
                elif health_status == "geo_blocked":
                    status = "geo-blocked"
                elif health_status in ("broken", "timeout"):
                    status = "failed"
                else:
                    status = "untested"
            else:
                status = "untested"

            sites.append(
                SiteInfo(
                    name=site_name,
                    country=site_country,
                    category=site_data.get("category", "Unknown"),
                    description=site_data.get("description"),
                    status=status,
                    test_url=site_data.get("test_url"),
                    is_adult=site_data.get("is_adult", False),
                )
            )

    # Sort: working first, then by name
    status_order = {"working": 0, "failed": 1, "geo-blocked": 1, "untested": 2}
    sites.sort(key=lambda s: (status_order.get(s.status, 2), s.name.lower()))

    return sites


def get_region_summary(region_id: str) -> Optional[RegionSummary]:
    """Get summary statistics for a region."""
    regions = load_regions()
    if region_id not in regions:
        return None

    region = regions[region_id]
    sites = get_sites_for_region(region_id)

    working = sum(1 for s in sites if s.status == "working")
    failed = sum(1 for s in sites if s.status in ("failed", "geo-blocked"))
    untested = sum(1 for s in sites if s.status == "untested")

    return RegionSummary(
        region=region,
        site_count=len(sites),
        working=working,
        failed=failed,
        untested=untested,
    )


def list_all_regions() -> list[RegionSummary]:
    """Get summary statistics for all regions, sorted by site count."""
    regions = load_regions()
    summaries = []

    for region_id in regions:
        summary = get_region_summary(region_id)
        if summary:
            summaries.append(summary)

    # Sort by site count descending
    summaries.sort(key=lambda s: s.site_count, reverse=True)
    return summaries
