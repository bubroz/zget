"""
Command-line interface for zget.

Routes to direct download when URL provided, or shows information about The Portal.
"""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
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
        help="Video URL to download (if omitted, shows Portal info)",
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
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Use flat output structure (no platform subdirectories)",
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

    # Doctor (Library Health Check)
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run library health check (detect orphaned records)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix issues found by --doctor (clean orphaned records)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview fixes without making changes (use with --doctor --fix)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed status for each item",
    )

    # Special handling for 'config' subcommand before general parsing
    # This avoids conflicts with the positional 'url' argument
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        from zget.commands.config import handle_config

        config_parser = argparse.ArgumentParser(
            prog="zget config", description="Manage persistent configuration settings."
        )
        config_parser.add_argument(
            "config_action",
            nargs="?",
            choices=["show", "set", "unset"],
            default="show",
            help="Action to perform (show, set, unset)",
        )
        config_parser.add_argument("config_params", nargs="*", help="Config key and optional value")

        config_args = config_parser.parse_args(sys.argv[2:])
        handle_config(config_args)
        return

    args = parser.parse_args()

    # Handle non-download commands first
    if args.health:
        import asyncio

        asyncio.run(handle_health(args))
        return

    if args.doctor:
        handle_doctor(args)
        return

    if args.search:
        handle_search(args.search)
        return

    if args.stats:
        handle_stats()
        return

    # No URL provided - show welcome info
    if args.url is None:
        show_welcome()
        return

    # List formats mode
    if args.list_formats:
        handle_list_formats(args)
        return

    # Direct download mode
    handle_download(args)


async def handle_health(args):
    """Handle smokescreen health verification from CLI."""
    from rich.live import Live
    from rich.table import Table

    from zget.health import SiteHealth

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


def show_welcome():
    """Show welcome information and Webport status."""
    import socket

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        webport_url = f"http://{local_ip}:8000"
    except OSError:
        webport_url = "http://localhost:8000"

    console.print(
        Panel(
            f"[bold gold1]zget v0.4.0[/bold gold1]\n\n"
            f"The interactive TUI has been retired in favor of [bold]The Portal[/bold].\n\n"
            f"📱 [bold]Mobile Access:[/bold] [link={webport_url}]{webport_url}[/link]\n"
            f"🌐 [bold]PWA Status:[/bold] Production Ready\n\n"
            f"To download a one-off video via CLI:\n"
            f"[dim]zget <url>[/dim]\n\n"
            f"To start the archival server:\n"
            f"[dim]zget-server --port 8000[/dim]",
            title="Welcome",
            border_style="gold1",
        )
    )


def handle_download(args):
    """Handle direct download from CLI."""
    from datetime import datetime
    from pathlib import Path

    from zget.config import DB_PATH, detect_platform, ensure_directories, get_video_output_dir
    from zget.core import compute_file_hash, download, parse_upload_date
    from zget.db import Video, VideoStore

    ensure_directories()

    # Determine output directory
    platform = detect_platform(args.url)
    if args.output:
        output_dir = Path(args.output)
    else:
        # If --flat is passed, we need to temporarily override the config behavior
        # or just pass it to get_video_output_dir if we update its signature.
        # For now, let's use a trick: if --flat is set, we'll handle it here.
        from zget import config

        original_flat = config.FLAT_OUTPUT_STRUCTURE
        if args.flat:
            config.FLAT_OUTPUT_STRUCTURE = True

        output_dir = get_video_output_dir(platform)

        # Restore (though usually not necessary in a one-off CLI run)
        config.FLAT_OUTPUT_STRUCTURE = original_flat

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

        # Cache thumbnail from metadata
        from zget.config import THUMBNAILS_DIR
        from zget.library.thumbnails import cache_thumbnail_sync

        thumbnail_path = cache_thumbnail_sync(result, THUMBNAILS_DIR)

        # Store in database
        store = VideoStore(DB_PATH)

        video = Video(
            url=args.url,
            platform=platform,
            video_id=result.get("id", ""),
            title=result.get("title", "Untitled"),
            description=result.get("description"),
            uploader=(
                "C-SPAN"
                if platform == "c-span"
                and (
                    not result.get("uploader")
                    or result.get("uploader", "").lower() in ("unknown", "null", "none")
                )
                else result.get("uploader", "unknown")
            ),
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
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            downloaded_at=datetime.now(),
            raw_metadata=result,
        )

        try:
            video.id = store.insert_video(video)
            if not args.quiet:
                console.print(f"[green]✓[/green] Added to library: {video.title}")

            # PLEX INTEGRATION: Generate NFO sidecar and local thumbnail
            if filepath.exists():
                try:
                    import shutil

                    from zget.config import THUMBNAILS_DIR
                    from zget.metadata.nfo import generate_nfo

                    # Generate NFO
                    nfo_path = filepath.with_suffix(".nfo")
                    generate_nfo(video, nfo_path)

                    # Copy thumbnail to video directory
                    if video.thumbnail_path:
                        thumb_src = Path(video.thumbnail_path)
                        if thumb_src.exists():
                            local_thumb = filepath.with_suffix(thumb_src.suffix)
                            if not local_thumb.exists():
                                shutil.copy2(thumb_src, local_thumb)
                except Exception as nfo_error:
                    if not args.quiet:
                        console.print(f"[yellow]⚠[/yellow] NFO generation failed: {nfo_error}")

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
    from rich.table import Table

    from zget.core import list_formats

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
    from rich.table import Table

    from zget.config import DB_PATH, PLATFORM_DISPLAY, ensure_directories
    from zget.db import VideoStore

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
            mins, secs = divmod(int(v.duration_seconds), 60)
            duration = f"{mins}:{secs:02d}"

        platform_name = PLATFORM_DISPLAY.get(v.platform, v.platform.capitalize())
        table.add_row(
            platform_name,
            v.uploader[:15] if v.uploader else "?",
            v.title[:40] if v.title else "?",
            duration,
        )

    console.print(table)
    console.print(f"\n[dim]{len(videos)} result(s)[/dim]")


def handle_stats():
    """Show library statistics."""
    from rich.panel import Panel
    from rich.table import Table

    from zget.config import (
        DB_PATH,
        PLATFORM_DISPLAY,
        VIDEOS_DIR,
        ensure_directories,
    )
    from zget.db import VideoStore

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
        platform_name = PLATFORM_DISPLAY.get(platform, platform.capitalize())
        table.add_row(f"  {platform_name}", str(count))

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


def handle_doctor(args):
    """Run library health check and optionally fix issues."""
    from pathlib import Path

    from rich.panel import Panel
    from rich.table import Table

    from zget.config import DB_PATH, THUMBNAILS_DIR, ensure_directories
    from zget.db import VideoStore
    from zget.safe_delete import TRASH_AVAILABLE, safe_delete

    ensure_directories()
    store = VideoStore(DB_PATH)

    console.print(
        Panel(
            "[bold]🩺 Library Health Check[/bold]",
            border_style="blue",
        )
    )

    # Get all videos from database
    all_videos = store.get_recent(limit=10000)
    total_records = len(all_videos)

    orphaned = []
    healthy = 0
    orphan_size = 0

    console.print(f"\n[dim]Scanning {total_records} records...[/dim]\n")

    for v in all_videos:
        file_exists = False
        if v.local_path:
            path = Path(v.local_path)
            file_exists = path.exists()

        if file_exists:
            healthy += 1
            if args.verbose:
                console.print(f"  [green]✓[/green] {v.id}: {v.title[:50]}")
        else:
            orphaned.append(v)
            if v.file_size_bytes:
                orphan_size += v.file_size_bytes
            if args.verbose:
                console.print(f"  [red]✗[/red] {v.id}: {v.title[:50]} [dim](file missing)[/dim]")

    # Summary
    console.print()
    if orphaned:
        size_str = _format_size(orphan_size)
        console.print(f"[yellow]⚠ Found {len(orphaned)} orphaned record(s)[/yellow]")
        console.print(f"  Recoverable space: [cyan]{size_str}[/cyan]")

        if args.verbose or len(orphaned) <= 10:
            table = Table(title="Orphaned Records", show_header=True)
            table.add_column("ID", style="cyan")
            table.add_column("Title")
            table.add_column("Former Path", style="dim")

            for v in orphaned[:20]:  # Limit display
                table.add_row(
                    str(v.id),
                    (v.title[:40] + "...") if len(v.title or "") > 40 else (v.title or "?"),
                    (v.local_path[:50] + "...")
                    if v.local_path and len(v.local_path) > 50
                    else (v.local_path or "?"),
                )

            if len(orphaned) > 20:
                table.add_row("...", f"({len(orphaned) - 20} more)", "...")

            console.print(table)
    else:
        console.print("[green]✓ No issues found. Library is healthy![/green]")

    # Handle fix
    if args.fix and orphaned:
        console.print()
        if args.dry_run:
            console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
            console.print(f"  Would remove {len(orphaned)} orphaned database record(s)")
            console.print("  Would clean up associated thumbnails")
        else:
            # Actually fix
            console.print("[bold]Cleaning up orphaned records...[/bold]")
            cleaned = 0
            for v in orphaned:
                try:
                    # Delete thumbnail if exists
                    if v.video_id and v.platform:
                        thumb_path = THUMBNAILS_DIR / f"{v.platform}_{v.video_id}.jpg"
                        if thumb_path.exists():
                            safe_delete(thumb_path, use_trash=True)

                    # Delete from database
                    store.delete_video(v.id)
                    cleaned += 1
                except Exception as e:
                    console.print(f"  [red]Error cleaning {v.id}: {e}[/red]")

            trash_note = " (thumbnails moved to trash)" if TRASH_AVAILABLE else ""
            console.print(f"[green]✓ Cleaned {cleaned} orphaned record(s){trash_note}[/green]")

    elif args.fix and not orphaned:
        console.print("\n[dim]Nothing to fix.[/dim]")

    # Final summary
    console.print(
        Panel(
            f"  Healthy Records:  [green]{healthy}[/green]\n"
            f"  Orphaned Records: "
            f"[{'red' if orphaned else 'green'}]"
            f"{len(orphaned)}"
            f"[/{'red' if orphaned else 'green'}]\n"
            f"  Trash Available:  "
            f"[{'green' if TRASH_AVAILABLE else 'yellow'}]"
            f"{'Yes' if TRASH_AVAILABLE else 'No'}"
            f"[/{'green' if TRASH_AVAILABLE else 'yellow'}]",
            title="Summary",
            border_style="blue",
        )
    )


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


if __name__ == "__main__":
    main()
