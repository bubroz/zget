import json
import re
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .db.store import VideoStore

SUPPORTED_SITES_URL = "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md"
# Placeholder for the future metadata manifest
METADATA_MANIFEST_URL = "https://raw.githubusercontent.com/bubroz/zget/main/registry_metadata.json"


class SiteHealth:
    """Manages the status and health of supported download sites."""

    def __init__(self, store: VideoStore):
        self.store = store
        self._matrix: Dict[str, bool] = {}
        self._metadata: Dict[str, Dict] = {}
        self._health_log: Dict[str, Dict] = {}

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
                    # Cache the raw matrix in DB as JSON for faster startup
                    self.store.set_metadata("cached_site_matrix", json.dumps(self._matrix))
            except Exception:
                # Fallback to cache if available
                cached_str = self.store.get_metadata("cached_site_matrix")
                if cached_str:
                    self._matrix = json.loads(cached_str)

            # 2. Fetch enriched metadata manifest
            # In dev mode, check local file first
            # Try to find project root relative to this file: src/zget/health.py -> ../../../
            project_root = Path(__file__).resolve().parent.parent.parent
            local_path = project_root / "data/enriched_registry.json"

            if local_path.exists():
                try:
                    with open(local_path, "r") as f:
                        self._metadata = json.load(f)
                    self.store.set_metadata("cached_registry_metadata", json.dumps(self._metadata))
                except Exception:
                    pass

            # If not found locally (or failed), try remote (or cache)
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
                except Exception:
                    cached_str = self.store.get_metadata("cached_registry_metadata")
                    if cached_str:
                        self._metadata = json.loads(cached_str)

        # 3. Load Health Log
        # In dev mode, check local file first
        # Try to find project root relative to this file
        project_root = Path(__file__).resolve().parent.parent.parent
        health_path = project_root / "data/health_log.json"

        if health_path.exists():
            try:
                with open(health_path, "r") as f:
                    logs = json.load(f)
                    # Convert list to dict by site {site: {status, timestamp, latency}}
                    # Sort by timestamp desc to get latest
                    logs.sort(key=lambda x: x["timestamp"])
                    self._health_log = {item["site"]: item for item in logs}
            except Exception:
                pass

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

        # Merge verifying health info
        health_status = self._health_log.get(site_name.lower())
        if health_status:
            base_info["health"] = health_status

        return base_info


async def get_site_intelligence(store: VideoStore) -> Dict[str, bool]:
    """Helper to get site status matrix."""
    health = SiteHealth(store)
    return await health.get_working_matrix()
