"""
Command-line interface for zget.

Routes to TUI when no args, or direct download when URL provided.
"""

import argparse
import sys
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


console = Console()


def main():
    """Main entry point for zget CLI."""
    parser = argparse.ArgumentParser(
        prog="zget",
        description="Personal media command center - download videos and manage your library.",
    )

    # URL is optional - if not provided, launch TUI
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="Video URL to download (if omitted, launches TUI)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        help="Output directory (default: auto by platform)",
    )
    parser.add_argument(
        "-a",
        "--audio-only",
        action="store_true",
        help="Extract audio only",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="best",
        help="Max video quality (default: best, or e.g., 1080, 720)",
    )
    parser.add_argument(
        "-f",
        "--format",
        metavar="ID",
        help="Specific format ID to download (from --list-formats)",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List available formats for URL (don't download)",
    )
    parser.add_argument(
        "--cookies-from",
        metavar="BROWSER",
        help="Extract cookies from browser (chrome, firefox, safari)",
    )
    parser.add_argument(
        "--cookies",
        metavar="FILE",
        help="Path to cookies.txt file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help="Search library and print results",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show library statistics",
    )

    # Smokescreen Health Verification
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run smokescreen health verification",
    )
    parser.add_argument(
        "--proxy",
        help="SOCKS5/HTTP proxy for health checks",
    )
    parser.add_argument(
        "--location",
        default="local",
        help="Location identifier for health checks",
    )
    parser.add_argument(
        "--all-sites",
        action="store_true",
        help="Verify ALL sites in registry (caution: slow)",
    )

    args = parser.parse_args()

    # Handle non-download commands first
    if args.health:
        import asyncio

        asyncio.run(handle_health(args))
        return

    if args.search:
        handle_search(args.search)
        return

    if args.stats:
        handle_stats()
        return

    # No URL provided - launch TUI
    if args.url is None:
        launch_tui()
        return

    # List formats mode
    if args.list_formats:
        handle_list_formats(args)
        return

    # Direct download mode
    handle_download(args)


async def handle_health(args):
    """Handle smokescreen health verification from CLI."""
    from zget.health import SiteHealth
    from rich.live import Live
    from rich.table import Table

    health = SiteHealth()
    # Ensure metadata is loaded
    await health.sync()

    sites = None
    if args.all_sites:
        sites = list(health._metadata.keys())
    elif args.url:
        # If a URL or site name was passed as positional arg
        sites = [args.url]

    table = Table(title=f"Smokescreen Health Check: {args.location}")
    table.add_column("Site")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Details")

    all_results = []
    with Live(table, console=console, refresh_per_second=4):

        def on_result(r):
            all_results.append(r)
            status_color = (
                "green" if r.status == "ok" else "yellow" if r.status == "geo_blocked" else "red"
            )
            table.add_row(
                r.site,
                f"[{status_color}]{r.status.value.upper()}[/{status_color}]",
                f"{r.latency_ms}ms",
                r.error or "-",
            )

        await health.run_smokescreen(
            sites=sites, proxy=args.proxy, tested_from=args.location, on_result=on_result
        )

    # Persist results after verification
    if all_results:
        health.save_health_log(all_results)
        console.print(
            f"\n[bold green]✓[/bold green] Saved {len(all_results)} verification results."
        )


def launch_tui():
    """Launch the TUI application."""
    try:
        from zget.tui.app import ZgetApp

        app = ZgetApp()
        app.run()
    except Exception as e:
        console.print(f"[red]Failed to launch TUI: {e}[/red]")
        sys.exit(1)


def handle_download(args):
    """Handle direct download from CLI."""
    from zget.core import download
    from zget.config import detect_platform, get_video_output_dir, DB_PATH, ensure_directories
    from zget.db import VideoStore, Video
    from zget.core import compute_file_hash, parse_upload_date
    from pathlib import Path
    from datetime import datetime

    ensure_directories()

    # Determine output directory
    platform = detect_platform(args.url)
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = get_video_output_dir(platform)

    try:
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            disable=args.quiet,
        ) as progress:
            task_id = progress.add_task("Downloading...", total=None)

            def progress_callback(d):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)

                    if total:
                        progress.update(task_id, completed=downloaded, total=total)
                    else:
                        progress.update(
                            task_id, description=f"Downloading... {downloaded // 1024} KB"
                        )
                elif d["status"] == "finished":
                    progress.update(task_id, description="Processing...")

            result = download(
                url=args.url,
                output_dir=output_dir,
                format_id=args.format,
                audio_only=args.audio_only,
                max_quality=args.quality,
                cookies_from=args.cookies_from,
                cookies_file=args.cookies,
                progress_callback=None if args.quiet else progress_callback,
                quiet=args.quiet,
            )

        # Get filepath and compute hash
        filepath = Path(result.get("_zget_filepath", ""))
        if filepath.exists():
            file_hash = compute_file_hash(filepath)
            file_size = filepath.stat().st_size
        else:
            file_hash = None
            file_size = None

        # Store in database
        store = VideoStore(DB_PATH)

        video = Video(
            url=args.url,
            platform=platform,
            video_id=result.get("id", ""),
            title=result.get("title", "Untitled"),
            description=result.get("description"),
            uploader=result.get("uploader", "unknown"),
            uploader_id=result.get("uploader_id"),
            upload_date=parse_upload_date(result.get("upload_date")),
            duration_seconds=result.get("duration"),
            view_count=result.get("view_count"),
            like_count=result.get("like_count"),
            resolution=f"{result.get('width', '?')}x{result.get('height', '?')}",
            fps=result.get("fps"),
            codec=result.get("vcodec"),
            file_size_bytes=file_size,
            file_hash_sha256=file_hash,
            local_path=str(filepath) if filepath.exists() else None,
            downloaded_at=datetime.now(),
            raw_metadata=result,
        )

        try:
            video.id = store.insert_video(video)
            if not args.quiet:
                console.print(f"[green]✓[/green] Added to library: {video.title}")
        except Exception as e:
            if not args.quiet:
                console.print(f"[yellow]⚠[/yellow] Downloaded but not added to library: {e}")

        if not args.quiet:
            console.print(f"[green]✓[/green] Downloaded: {result.get('title', 'video')}")
            console.print(f"  → {filepath}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Download cancelled[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


def handle_list_formats(args):
    """List available formats for a URL."""
    from zget.core import list_formats
    from rich.table import Table

    try:
        console.print(f"[dim]Fetching formats for: {args.url}[/dim]\n")

        formats = list_formats(
            args.url,
            cookies_from=args.cookies_from,
            cookies_file=args.cookies,
        )

        table = Table(title="Available Formats")
        table.add_column("ID", style="cyan")
        table.add_column("Ext", style="green")
        table.add_column("Resolution")
        table.add_column("FPS")
        table.add_column("Video")
        table.add_column("Audio")
        table.add_column("Size", justify="right")

        for f in formats:
            size = ""
            if f.get("filesize"):
                size_mb = f["filesize"] / (1024 * 1024)
                size = f"{size_mb:.1f} MB"

            table.add_row(
                f.get("format_id", "?"),
                f.get("ext", "?"),
                f.get("resolution", "?"),
                str(f.get("fps", "")) if f.get("fps") else "",
                f.get("vcodec", "-") if f.get("has_video") else "-",
                f.get("acodec", "-") if f.get("has_audio") else "-",
                size,
            )

        console.print(table)
        console.print("\n[dim]Use -f FORMAT_ID to download a specific format[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def handle_search(query: str):
    """Search library and print results."""
    from zget.db import VideoStore
    from zget.config import DB_PATH, ensure_directories
    from rich.table import Table

    ensure_directories()
    store = VideoStore(DB_PATH)

    videos = store.search(query, limit=50)

    if not videos:
        console.print(f"[yellow]No results for: {query}[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("Platform", style="cyan")
    table.add_column("Uploader")
    table.add_column("Title")
    table.add_column("Duration", justify="right")

    for v in videos:
        duration = ""
        if v.duration_seconds:
            mins, secs = divmod(v.duration_seconds, 60)
            duration = f"{mins}:{secs:02d}"

        table.add_row(
            v.platform,
            v.uploader[:15] if v.uploader else "?",
            v.title[:40] if v.title else "?",
            duration,
        )

    console.print(table)
    console.print(f"\n[dim]{len(videos)} result(s)[/dim]")


def handle_stats():
    """Show library statistics."""
    from zget.db import VideoStore
    from zget.config import DB_PATH, VIDEOS_DIR, THUMBNAILS_DIR, ensure_directories
    from rich.panel import Panel
    from rich.table import Table

    ensure_directories()
    store = VideoStore(DB_PATH)

    stats = store.get_stats()

    # Format size
    size_bytes = stats["total_size_bytes"]
    if size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    # Platform breakdown
    table = Table(show_header=False, box=None)
    table.add_column("Platform")
    table.add_column("Count", justify="right")

    for platform, count in stats["platforms"].items():
        table.add_row(f"  {platform}", str(count))

    console.print(
        Panel(
            f"[bold]📊 Library Statistics[/bold]\n\n"
            f"  Total Videos:  [cyan]{stats['total_videos']}[/cyan]\n"
            f"  Total Size:    [cyan]{size_str}[/cyan]\n"
            f"  Videos Dir:    [dim]{VIDEOS_DIR}[/dim]\n\n"
            f"[bold]By Platform:[/bold]",
            title="zget",
        )
    )
    console.print(table)


if __name__ == "__main__":
    main()
