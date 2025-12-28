import json
import re
import httpx
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

from .db.store import VideoStore
from .smokescreen import (
    verify_site,
    verify_sites_batch,
    save_health_log,
    load_health_log,
    HealthResult,
    HealthStatus,
)

SUPPORTED_SITES_URL = "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md"
METADATA_MANIFEST_URL = (
    "https://raw.githubusercontent.com/bubroz/zget/main/data/enriched_registry.json"
)

# Top sites to verify on startup (most commonly used)
TOP_SITES = [
    "youtube",
    "tiktok",
    "instagram",
    "twitter",
    "reddit",
    "vimeo",
    "soundcloud",
    "twitch",
    "facebook",
    "dailymotion",
    "bilibili",
    "nicovideo",
    "pornhub",
    "xvideos",
    "bandcamp",
    "spotify",
]


class SiteHealth:
    """Manages the status and health of supported download sites."""

    def __init__(self, store: VideoStore):
        self.store = store
        self._matrix: Dict[str, bool] = {}
        self._metadata: Dict[str, Dict] = {}
        self._health_log: Dict[str, Dict] = {}
        self._project_root = Path(__file__).resolve().parent.parent.parent
        self._health_log_path = self._project_root / "data/health_log.json"

    async def get_working_matrix(self) -> Dict[str, bool]:
        """Get the site status matrix, either from cache or fresh."""
        sync_needed = self._check_sync_needed()

        if sync_needed or not self._matrix:
            await self.sync()

        return self._matrix

    def _check_sync_needed(self) -> bool:
        """Check if we need to sync based on last_sync metadata."""
        last_sync_str = self.store.get_metadata("last_registry_sync")
        if not last_sync_str:
            return True

        try:
            last_sync = datetime.fromisoformat(last_sync_str)
            return datetime.now() - last_sync > timedelta(days=7)
        except (ValueError, TypeError):
            return True

    async def sync(self) -> None:
        """Fetch fresh site and metadata status."""
        async with httpx.AsyncClient() as client:
            # 1. Fetch yt-dlp supported sites
            try:
                resp = await client.get(SUPPORTED_SITES_URL, timeout=10.0)
                if resp.status_code == 200:
                    self._matrix = self._parse_markdown(resp.text)
                    self.store.set_metadata("cached_site_matrix", json.dumps(self._matrix))
            except Exception:
                cached_str = self.store.get_metadata("cached_site_matrix")
                if cached_str:
                    self._matrix = json.loads(cached_str)

            # 2. Load enriched metadata from local file first
            local_path = self._project_root / "data/enriched_registry.json"

            if local_path.exists():
                try:
                    with open(local_path, "r") as f:
                        self._metadata = json.load(f)
                    self.store.set_metadata("cached_registry_metadata", json.dumps(self._metadata))
                except Exception:
                    pass

            # Fallback to remote/cache if local not available
            if not self._metadata:
                try:
                    resp = await client.get(METADATA_MANIFEST_URL, timeout=10.0)
                    if resp.status_code == 200:
                        self._metadata = resp.json()
                        self.store.set_metadata(
                            "cached_registry_metadata", json.dumps(self._metadata)
                        )
                except Exception:
                    cached_str = self.store.get_metadata("cached_registry_metadata")
                    if cached_str:
                        self._metadata = json.loads(cached_str)

        # 3. Load Health Log
        self._health_log = load_health_log(self._health_log_path)

        # Update sync timestamp
        self.store.set_metadata("last_registry_sync", datetime.now().isoformat())

    def _parse_markdown(self, content: str) -> Dict[str, bool]:
        """Parses the yt-dlp Markdown file."""
        results = {}
        lines = content.splitlines()
        for line in lines:
            if not line.strip().startswith("- **"):
                continue

            match = re.search(r"-\s+\*\*([^*]+)\*\*", line)
            if not match:
                continue

            site_name = match.group(1).lower()
            is_broken = "(Currently broken)" in line
            results[site_name] = not is_broken
        return results

    def get_site_info(self, site_name: str) -> Dict:
        """Get enriched info (country, lang, etc) for a site."""
        base_info = {
            "name": site_name,
            "working": self._matrix.get(site_name.lower(), True),
            "country": "Unknown",
            "language": "Universal",
            "description": "No description available.",
        }

        enriched = self._metadata.get(site_name.lower(), {})
        base_info.update(enriched)

        # Merge health verification info
        health_status = self._health_log.get(site_name.lower())
        if health_status:
            base_info["health"] = health_status

        return base_info

    def get_health_status(self, site_name: str) -> Optional[Dict]:
        """Get the latest health verification result for a site."""
        return self._health_log.get(site_name.lower())

    async def verify_single(
        self,
        site_id: str,
        force: bool = False,
    ) -> HealthResult:
        """
        Verify a single site's health on-demand.

        Args:
            site_id: The site identifier
            force: If True, verify even if recently checked

        Returns:
            HealthResult with status
        """
        # Check if we have a recent result (within 1 hour)
        existing = self._health_log.get(site_id.lower())
        if existing and not force:
            try:
                verified_at = datetime.fromisoformat(existing.get("verified_at", ""))
                if datetime.now() - verified_at < timedelta(hours=1):
                    return HealthResult(
                        site=site_id,
                        status=HealthStatus(existing["status"]),
                        latency_ms=existing.get("latency_ms", 0),
                        error=existing.get("error"),
                        verified_at=existing["verified_at"],
                        test_url=existing.get("test_url"),
                    )
            except (ValueError, KeyError):
                pass

        # Get test URL from metadata
        site_meta = self._metadata.get(site_id.lower(), {})
        test_url = site_meta.get("test_url", "")

        result = await verify_site(site_id, test_url)

        # Update health log
        self._health_log[site_id.lower()] = result.to_dict()
        save_health_log([result], self._health_log_path)

        return result

    async def run_smokescreen(
        self,
        sites: Optional[List[str]] = None,
        concurrency: int = 5,
        on_result: Optional[Callable[[HealthResult], None]] = None,
    ) -> List[HealthResult]:
        """
        Run smokescreen verification on multiple sites.

        Args:
            sites: List of site IDs to verify. If None, verifies TOP_SITES.
            concurrency: Max concurrent verifications
            on_result: Callback for each result

        Returns:
            List of HealthResult objects
        """
        if sites is None:
            sites = TOP_SITES

        # Build site info list with test URLs
        site_infos = []
        for site_id in sites:
            site_meta = self._metadata.get(site_id.lower(), {})
            test_url = site_meta.get("test_url", "")
            site_infos.append({"site": site_id, "test_url": test_url})

        results = await verify_sites_batch(
            site_infos,
            concurrency=concurrency,
            on_result=on_result,
        )

        # Update health log with all results
        for result in results:
            self._health_log[result.site.lower()] = result.to_dict()
        save_health_log(results, self._health_log_path)

        return results

    def get_all_health_statuses(self) -> Dict[str, Dict]:
        """Get all health statuses from the log."""
        return self._health_log.copy()


async def get_site_intelligence(store: VideoStore) -> Dict[str, bool]:
    """Helper to get site status matrix."""
    health = SiteHealth(store)
    return await health.get_working_matrix()
