"""
Site health monitoring.

Parses yt-dlp's supported sites list to identify known broken extractors.
"""

import re
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta

SUPPORTED_SITES_URL = "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md"


class SiteHealth:
    """Manages the status and health of supported download sites."""

    def __init__(self, cache_file: Optional[str] = None):
        self.cache_file = cache_file
        self._site_cache: Dict[str, bool] = {}  # domain -> is_working
        self._last_updated: Optional[datetime] = None

    async def fetch_status_matrix(self) -> Dict[str, bool]:
        """
        Fetch supportedsites.md and parse for broken markers.
        Returns a dict of {site_name: is_working}.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(SUPPORTED_SITES_URL, timeout=10.0)
                response.raise_for_status()
                content = response.text
                return self._parse_markdown(content)
            except Exception as e:
                # Fallback to local cache or empty if failed
                return {}

    def _parse_markdown(self, content: str) -> Dict[str, bool]:
        """
        Parses the Markdown file.
        Example line: - **20min**: (**Currently broken**)
        """
        results = {}
        # Lines look like:  - **SiteName**: Details...
        lines = content.splitlines()

        for line in lines:
            if not line.strip().startswith("- **"):
                continue

            # Extract site name: - **NAME**:
            match = re.search(r"-\s+\*\*([^*]+)\*\*:", line)
            if not match:
                continue

            site_name = match.group(1).lower()
            is_broken = "(Currently broken)" in line

            # Map name to status
            results[site_name] = not is_broken

        return results

    def is_known_broken(self, site_name: str, matrix: Dict[str, bool]) -> bool:
        """Check if a site is explicitly marked as broken upstream."""
        # Simple name match
        return not matrix.get(site_name.lower(), True)


async def get_site_intelligence() -> Dict[str, bool]:
    """Helper to get site status matrix."""
    health = SiteHealth()
    return await health.fetch_status_matrix()
