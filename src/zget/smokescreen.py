"""
Smokescreen Health Verification Engine

Active health verification for yt-dlp extractors using --simulate mode.
Tests sites with their test URLs to determine actual health status.
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

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "site": self.site,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "verified_at": self.verified_at,
            "test_url": self.test_url,
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
) -> HealthResult:
    """
    Verify a site's health by running yt-dlp --simulate on its test URL.

    Args:
        site_id: The site identifier (e.g., 'youtube', 'tiktok')
        test_url: The test URL to verify
        timeout: Maximum time to wait (seconds)

    Returns:
        HealthResult with status, latency, and any error message
    """
    if not test_url:
        return HealthResult(
            site=site_id,
            status=HealthStatus.NO_TEST_URL,
            latency_ms=0,
            error="No test URL available",
            verified_at=datetime.now().isoformat(),
        )

    start_time = time.time()

    try:
        # Run yt-dlp in simulate mode (no download)
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--simulate",
            "--no-warnings",
            "--no-playlist",
            "--socket-timeout",
            "10",
            test_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            latency_ms = int((time.time() - start_time) * 1000)
            return HealthResult(
                site=site_id,
                status=HealthStatus.TIMEOUT,
                latency_ms=latency_ms,
                error=f"Timeout after {timeout}s",
                verified_at=datetime.now().isoformat(),
                test_url=test_url,
            )

        latency_ms = int((time.time() - start_time) * 1000)

        if proc.returncode == 0:
            return HealthResult(
                site=site_id,
                status=HealthStatus.OK,
                latency_ms=latency_ms,
                error=None,
                verified_at=datetime.now().isoformat(),
                test_url=test_url,
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
                    verified_at=datetime.now().isoformat(),
                    test_url=test_url,
                )

        # Generic broken
        error_msg = stderr.decode("utf-8", errors="replace")[:200]
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=latency_ms,
            error=error_msg.strip() or "Unknown error",
            verified_at=datetime.now().isoformat(),
            test_url=test_url,
        )

    except FileNotFoundError:
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=0,
            error="yt-dlp not found in PATH",
            verified_at=datetime.now().isoformat(),
            test_url=test_url,
        )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return HealthResult(
            site=site_id,
            status=HealthStatus.BROKEN,
            latency_ms=latency_ms,
            error=str(e)[:200],
            verified_at=datetime.now().isoformat(),
            test_url=test_url,
        )


async def verify_sites_batch(
    sites: List[Dict[str, str]],
    concurrency: int = 5,
    on_result: Optional[Callable[[HealthResult], None]] = None,
) -> List[HealthResult]:
    """
    Verify multiple sites concurrently.

    Args:
        sites: List of dicts with 'site' and 'test_url' keys
        concurrency: Max concurrent verifications
        on_result: Optional callback for each result

    Returns:
        List of HealthResult objects
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def verify_with_semaphore(site_info: Dict[str, str]) -> HealthResult:
        async with semaphore:
            result = await verify_site(
                site_id=site_info["site"],
                test_url=site_info.get("test_url", ""),
            )
            if on_result:
                on_result(result)
            return result

    tasks = [verify_with_semaphore(site) for site in sites]
    results = await asyncio.gather(*tasks)

    return list(results)


def save_health_log(results: List[HealthResult], path: Path) -> None:
    """Save health results to JSON file."""
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
        existing[result.site] = result.to_dict()

    # Save
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def load_health_log(path: Path) -> Dict[str, dict]:
    """Load health log from JSON file."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


# Quick test utility
if __name__ == "__main__":
    import sys

    async def test_sites():
        # Test a few known sites
        test_cases = [
            {"site": "youtube", "test_url": "https://www.youtube.com/watch?v=BaW_jenozKc"},
            {"site": "vimeo", "test_url": "https://vimeo.com/76979871"},
        ]

        print("Testing Smokescreen engine...")
        results = await verify_sites_batch(
            test_cases,
            on_result=lambda r: print(f"  {r.site}: {r.status.value} ({r.latency_ms}ms)"),
        )

        print(f"\nTotal: {len(results)} sites tested")
        for status in HealthStatus:
            count = sum(1 for r in results if r.status == status)
            if count:
                print(f"  {status.value}: {count}")

    asyncio.run(test_sites())
