"""
Smokescreen Health Verification Engine

Active health verification for yt-dlp extractors using --simulate mode.
Tests sites with their test URLs to determine actual health status.
Supports proxies and multi-region testing.
"""

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Callable


class HealthStatus(str, Enum):
    """Health status for a site."""

    OK = "ok"
    BROKEN = "broken"
    TIMEOUT = "timeout"
    GEO_BLOCKED = "geo_blocked"
    NO_TEST_URL = "no_test_url"
    UNKNOWN = "unknown"


@dataclass
class HealthResult:
    """Result of a health verification check."""

    site: str
    status: HealthStatus
    latency_ms: int
    error: Optional[str]
    verified_at: str
    test_url: Optional[str] = None
    tested_from: str = "local"  # e.g., 'local', 'us', 'nl', 'se'

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "site": self.site,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "verified_at": self.verified_at,
            "test_url": self.test_url,
            "tested_from": self.tested_from,
        }


# Common geo-blocking error patterns
GEO_BLOCK_PATTERNS = [
    "not available in your country",
    "geo-restricted",
    "geoblocked",
    "not available in your region",
    "content is not available",
    "video is not available in your location",
    "access denied",
    "blocked in your territory",
]


async def verify_site(
    site_id: str,
    test_url: str,
    timeout: int = 15,
    proxy: Optional[str] = None,
    tested_from: str = "local",
) -> HealthResult:
    """
    Verify a site's health by running yt-dlp --simulate on its test URL.

    Args:
        site_id: The site identifier (e.g., 'youtube', 'tiktok')
        test_url: The test URL to verify
        timeout: Maximum time to wait (seconds)
        proxy: Optional proxy string (e.g., 'socks5://user:pass@host:port')
        tested_from: Identifier for test location

    Returns:
        HealthResult with status, latency, and any error message
    """
    if not test_url:
        return HealthResult(
            site=site_id,
            status=HealthStatus.NO_TEST_URL,
            latency_ms=0,
            error="No test URL available",
            verified_at=datetime.utcnow().isoformat() + "Z",
            tested_from=tested_from,
        )

    start_time = time.time()

    cmd = [
        "yt-dlp",
        "--simulate",
        "--no-warnings",
        "--no-playlist",
        "--socket-timeout",
        "10",
    ]

    if proxy:
        cmd.extend(["--proxy", proxy])

    cmd.append(test_url)

    try:
        # Run yt-dlp in simulate mode (no download)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            latency_ms = int((time.time() - start_time) * 1000)
            return HealthResult(
                site=site_id,
                status=HealthStatus.TIMEOUT,
                latency_ms=latency_ms,
                error=f"Timeout after {timeout}s",
                verified_at=datetime.utcnow().isoformat() + "Z",
                test_url=test_url,
                tested_from=tested_from,
            )

        latency_ms = int((time.time() - start_time) * 1000)

        if proc.returncode == 0:
            return HealthResult(
                site=site_id,
                status=HealthStatus.OK,
                latency_ms=latency_ms,
                error=None,
                verified_at=datetime.utcnow().isoformat() + "Z",
                test_url=test_url,
                tested_from=tested_from,
            )

        # Check for geo-blocking
        error_text = stderr.decode("utf-8", errors="replace").lower()
        stdout_text = stdout.decode("utf-8", errors="replace").lower()
        combined = error_text + stdout_text

        for pattern in GEO_BLOCK_PATTERNS:
            if pattern in combined:
                return HealthResult(
                    site=site_id,
                    status=HealthStatus.GEO_BLOCKED,
                    latency_ms=latency_ms,
                    error=f"Geo-blocked: {pattern}",
                    verified_at=datetime.utcnow().isoformat() + "Z",
                    test_url=test_url,
                    tested_from=tested_from,
                )

        # Generic broken
        error_msg = stderr.decode("utf-8", errors="replace")[:200]
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=latency_ms,
            error=error_msg.strip() or "Unknown error",
            verified_at=datetime.utcnow().isoformat() + "Z",
            test_url=test_url,
            tested_from=tested_from,
        )

    except FileNotFoundError:
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=0,
            error="yt-dlp not found in PATH",
            verified_at=datetime.utcnow().isoformat() + "Z",
            test_url=test_url,
            tested_from=tested_from,
        )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=latency_ms,
            error=str(e)[:200],
            verified_at=datetime.utcnow().isoformat() + "Z",
            test_url=test_url,
            tested_from=tested_from,
        )


async def verify_sites_batch(
    sites: List[Dict[str, str]],
    concurrency: int = 5,
    proxy: Optional[str] = None,
    tested_from: str = "local",
    on_result: Optional[Callable[[HealthResult], None]] = None,
) -> List[HealthResult]:
    """
    Verify multiple sites concurrently.

    Args:
        sites: List of dicts with 'site' and 'test_url' keys
        concurrency: Max concurrent verifications
        proxy: Optional proxy string
        tested_from: Location tag
        on_result: Optional callback for each result

    Returns:
        List of HealthResult objects
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def verify_with_semaphore(site_info: Dict[str, str]) -> HealthResult:
        async with semaphore:
            result = await verify_site(
                site_id=site_info["site"],
                test_url=site_info.get("test_url", ""),
                proxy=proxy,
                tested_from=tested_from,
            )
            if on_result:
                on_result(result)
            return result

    tasks = [verify_with_semaphore(site) for site in sites]
    results = await asyncio.gather(*tasks)

    return list(results)


def save_health_log(results: List[HealthResult], path: Path) -> None:
    """Save health results to JSON file, merging with existing data."""
    # Load existing results
    existing = {}
    if path.exists():
        try:
            with open(path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = {}

    # Update with new results
    for result in results:
        # We store as {site_id: { ... }}
        # If multiple locations test the same site, we might want to store all or latest
        # For simplicity, we store by site, but could be nested by location
        existing[result.site] = result.to_dict()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def load_health_log(path: Path) -> Dict[str, dict]:
    """Load health log from JSON file, with auto-migration for legacy list format."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)

        # Handle legacy list format: [{site: '...', ...}, ...]
        if isinstance(data, list):
            migrated = {}
            for item in data:
                site = item.get("site")
                if site:
                    # Convert legacy fields if necessary
                    # Older versions used 'timestamp' instead of 'verified_at'
                    # and 'latency' (seconds) instead of 'latency_ms'
                    result = {
                        "site": site,
                        "status": item.get("status", "unknown").lower(),
                        "latency_ms": item.get("latency_ms") or int(item.get("latency", 0) * 1000),
                        "error": item.get("error"),
                        "verified_at": item.get("verified_at") or item.get("timestamp"),
                        "test_url": item.get("test_url"),
                        "tested_from": item.get("tested_from", "local"),
                    }
                    migrated[site.lower()] = result
            return migrated

        return data
    except (json.JSONDecodeError, IOError):
        return {}


# Quick test utility
if __name__ == "__main__":
    import sys

    async def test_sites():
        # Test a few known sites
        test_cases = []

        print("Testing Smokescreen engine with proxy support...")
        results = await verify_sites_batch(
            test_cases,
            tested_from="test_runner",
            on_result=lambda r: print(
                f"  {r.site}: {r.status.value} ({r.latency_ms}ms) from {r.tested_from}"
            ),
        )

        print(f"\nTotal: {len(results)} sites tested")

    asyncio.run(test_sites())
