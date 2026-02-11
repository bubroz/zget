import asyncio
import json
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import (
    DB_PATH,
    HEALTH_LOG_PATH,
    PLATFORM_DISPLAY,
    THUMBNAILS_DIR,
    ensure_directories,
)
from ..db import AsyncVideoStore, VideoStore, get_db_dependency
from ..queue import DownloadQueue, QueueStatus
from ..utils import get_version, guess_media_type, sanitize_filename

# Global instances
ensure_directories()
store = VideoStore(DB_PATH)
queue = DownloadQueue(max_concurrent=4, store=store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown lifecycle."""
    await queue.start()
    yield
    await queue.stop()


# Initialize app
app = FastAPI(title="zget Server", version=get_version(), lifespan=lifespan)

# Enable CORS for local/Tailscale access
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: str
    collection: str | None = None
    tags: list[str] | None = None


class SettingsUpdate(BaseModel):
    zget_home: str
    host: str | None = "0.0.0.0"
    port: int | None = 8000
    output_dir: str | None = None
    flat_output: bool | None = False


# Routes
@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": get_version()}


@app.get("/api/health/status")
def health_status():
    """Return smokescreen health check status and statistics."""

    health_log_path = HEALTH_LOG_PATH

    if not health_log_path.exists():
        return {"last_check": None, "total": 0, "working": 0, "broken": 0, "geo_blocked": 0}

    with open(health_log_path) as f:
        data = json.load(f)

    # Get last check time from most recent entry
    last_check = None
    working = broken = geo_blocked = 0

    for site, info in data.items():
        status = info.get("status", "unknown")
        if status == "ok":
            working += 1
        elif status == "broken":
            broken += 1
        elif status == "geo_blocked":
            geo_blocked += 1

        verified_at = info.get("verified_at")
        if verified_at and (not last_check or verified_at > last_check):
            last_check = verified_at

    return {
        "last_check": last_check,
        "total": len(data),
        "working": working,
        "broken": broken,
        "geo_blocked": geo_blocked,
    }


@app.get("/api/settings")
def get_settings():
    from ..config import CONFIG_FILE, load_persistent_config

    # Load fresh config on each request to reflect recent changes
    config = load_persistent_config()

    host_setting = config.get("host", "0.0.0.0")
    local_ip = "localhost"

    if host_setting == "127.0.0.1":
        local_ip = "127.0.0.1"
    else:
        try:
            # Get local IP for network access info
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except OSError:
            local_ip = "127.0.0.1" if host_setting == "127.0.0.1" else "localhost"

    return {
        "zget_home": config.get("zget_home", str(Path.home() / ".zget")),
        "config_file": str(CONFIG_FILE),
        "local_ip": local_ip,
        "host": host_setting,
        "port": config.get("port", 8000),
        "output_dir": config.get("output_dir", ""),
        "flat_output": config.get("flat_output", False),
        "version": "0.4.0",
    }


@app.post("/api/settings")
def update_settings(update: SettingsUpdate):
    from ..config import CONFIG_DIR, CONFIG_FILE, load_persistent_config

    old_config = load_persistent_config()
    new_config = {
        **old_config,
        "zget_home": update.zget_home,
        "host": update.host,
        "port": update.port,
        "output_dir": update.output_dir if update.output_dir else None,
        "flat_output": update.flat_output,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(new_config, f, indent=4)
    return {"status": "ok", "message": "Settings saved. Restart server to apply."}


@app.post("/api/repair/thumbnails")
async def repair_thumbnails(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_repair)
    return {"status": "started", "message": "Repairing thumbnails in background"}


async def run_repair():

    videos = await asyncio.to_thread(store.get_recent, limit=5000)
    for v in videos:
        if not v.thumbnail_path or not Path(v.thumbnail_path).exists():
            # Try to redownload thumbnail only
            print(f"Repairing thumbnail for {v.id} ({v.platform})")
            from ..core import extract_info

            try:
                info = await asyncio.to_thread(extract_info, v.url)
                if info.get("thumbnail"):
                    import httpx

                    thumb_path = THUMBNAILS_DIR / f"{v.platform}_{v.video_id}.jpg"
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(info["thumbnail"])
                        if resp.status_code == 200:
                            with open(thumb_path, "wb") as f:
                                f.write(resp.content)
                            v.thumbnail_path = str(thumb_path)
                            await asyncio.to_thread(store.update_video, v)
            except Exception as e:
                print(f"Failed repair for {v.id}: {e}")


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@app.delete("/api/media/bulk")
async def bulk_delete_media(request: BulkDeleteRequest):
    """Delete multiple videos at once."""
    from ..library.thumbnails import delete_thumbnail
    from ..safe_delete import safe_delete

    deleted = 0
    errors = []

    for video_id in request.ids:
        try:
            video = store.get_video(video_id)
            if not video:
                errors.append(f"Video {video_id} not found")
                continue

            # Delete file if it exists (move to trash)
            if video.local_path:
                path = Path(video.local_path)
                if path.exists():
                    safe_delete(path, use_trash=True)

            # Delete thumbnail
            delete_thumbnail(video.video_id, video.platform, THUMBNAILS_DIR)

            # Delete from DB
            store.delete_video(video_id)
            deleted += 1
        except Exception as e:
            errors.append(f"Error deleting {video_id}: {str(e)}")

    return {"deleted": deleted, "errors": errors}


@app.get("/api/media/{video_id}")
@app.head("/api/media/{video_id}")
async def get_media(video_id: str, download: bool = False):
    # Search by DB id first, then by platform video_id
    video = None
    if video_id.isdigit():
        video = store.get_video(int(video_id))
    if not video:
        video = store.get_video_by_video_id(video_id)

    if not video or not video.local_path:
        raise HTTPException(status_code=404, detail="Video file not found")

    path = Path(video.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    media_type = guess_media_type(str(path))

    if download:
        filename = f"{sanitize_filename(video.title)}.mp4" if video.title else f"{video_id}.mp4"
        return FileResponse(
            path,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return FileResponse(path, media_type=media_type)


@app.delete("/api/media/{id}")
async def delete_media(id: int):
    from ..safe_delete import safe_delete

    video = store.get_video(id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete file (move to trash)
    if video.local_path:
        path = Path(video.local_path)
        if path.exists():
            safe_delete(path, use_trash=True)

    # Delete thumbnail
    from ..library.thumbnails import delete_thumbnail

    delete_thumbnail(video.video_id, video.platform, THUMBNAILS_DIR)

    # Delete from DB
    store.delete_video(id)
    return {"status": "deleted"}


@app.post("/api/library/doctor")
async def doctor_check():
    """Detect orphaned records (DB entries where video file is missing)."""
    videos = store.get_recent(limit=10000)
    orphaned_ids = []

    for v in videos:
        if not v.local_path or not Path(v.local_path).exists():
            orphaned_ids.append(v.id)

    return {"orphaned_count": len(orphaned_ids), "orphaned_ids": orphaned_ids}


@app.post("/api/library/cleanup")
async def cleanup_orphans():
    """Remove orphaned records (DB entries where video file is missing)."""
    from ..library.thumbnails import delete_thumbnail

    videos = store.get_recent(limit=10000)
    cleaned = 0

    for v in videos:
        if not v.local_path or not Path(v.local_path).exists():
            if v.id is None:
                continue
            # Delete thumbnail if it exists
            delete_thumbnail(v.video_id, v.platform, THUMBNAILS_DIR)
            # Delete from DB
            store.delete_video(v.id)
            cleaned += 1

    return {"cleaned": cleaned}


@app.get("/api/thumbnails/{video_id}")
async def get_thumbnail(video_id: str):
    # Find video by DB id or platform video_id
    video = None
    if video_id.isdigit():
        video = store.get_video(int(video_id))
    if not video:
        video = store.get_video_by_video_id(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    from ..library.thumbnails import get_thumbnail_path

    path = get_thumbnail_path(video.video_id, video.platform, THUMBNAILS_DIR)

    if not path or not path.exists():
        expected = f"{video.platform}_{video.video_id}.jpg"
        raise HTTPException(
            status_code=404, detail=f"Thumbnail missing: expected {expected} in {THUMBNAILS_DIR}"
        )

    return FileResponse(path)


@app.get("/api/registry")
def get_registry():
    """Return the full global site registry with detailed metadata and health."""
    from ..regions import get_popularity_weights, get_sites_for_region, load_regions

    regions = load_regions()
    weights = get_popularity_weights(store)

    all_sites = []
    seen = set()
    categories = set()

    for rid in regions:
        sites = get_sites_for_region(rid, weights=weights)
        for s in sites:
            if s.name not in seen:
                all_sites.append(
                    {
                        "name": s.name,
                        "category": s.category,
                        "description": s.description,
                        "status": s.status,
                        "working": s.status == "working",
                        "weight": weights.get(s.name.lower(), 0) / 1000.0,  # Normalize
                        "categories": [s.category] if s.category else [],
                    }
                )
                seen.add(s.name)
                if s.category:
                    categories.add(s.category)

    # Sort by prominence (normalized weight)
    all_sites.sort(key=lambda x: x["weight"], reverse=True)

    return {"sites": all_sites, "categories": sorted(list(categories))}


@app.get("/api/regions")
def list_regions():
    """Return all regional collections with summary stats."""
    from ..regions import list_all_regions

    summaries = list_all_regions()
    return [
        {
            "id": s.region.id,
            "name": s.region.name,
            "emoji": s.region.emoji,
            "notes": s.region.notes,
            "site_count": s.site_count,
            "working": s.working,
            "failed": s.failed,
            "untested": s.untested,
        }
        for s in summaries
    ]


@app.get("/api/regions/{region_id}")
def get_region_sites(region_id: str):
    """Return all sites in a region with health status and popularity sorting."""
    from ..regions import (
        get_popularity_weights,
        get_region_summary,
        get_sites_for_region,
        load_regions,
    )

    regions = load_regions()
    if region_id not in regions:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")

    region = regions[region_id]
    # Calculate popularity weights from local DB
    weights = get_popularity_weights(store)
    sites = get_sites_for_region(region_id, weights=weights)
    summary = get_region_summary(region_id)

    # Extract unique categories
    categories = sorted(list(set(s.category for s in sites if s.category)))

    return {
        "region": {
            "id": region.id,
            "name": region.name,
            "emoji": region.emoji,
            "notes": region.notes,
        },
        "summary": {
            "site_count": summary.site_count if summary else 0,
            "working": summary.working if summary else 0,
            "failed": summary.failed if summary else 0,
            "untested": summary.untested if summary else 0,
        },
        "categories": categories,
        "sites": [
            {
                "name": s.name,
                "country": s.country,
                "category": s.category,
                "description": s.description,
                "status": s.status,
                "test_url": s.test_url,
                "is_adult": s.is_adult,
            }
            for s in sites
        ],
    }


@app.get("/api/video/{id}")
async def get_video_details(id: int):
    """Get detailed video metadata by ID."""
    video = store.get_video(id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    v_dict = video.__dict__.copy()
    v_dict["platform_display"] = PLATFORM_DISPLAY.get(video.platform, video.platform.capitalize())
    if video.raw_metadata:
        v_dict["uploader_url"] = video.raw_metadata.get("uploader_url")
        v_dict["channel"] = video.raw_metadata.get("channel")
        v_dict["channel_url"] = video.raw_metadata.get("channel_url")

    return v_dict


@app.post("/api/repair/library")
async def repair_library(background_tasks: BackgroundTasks):
    """Trigger a background repair of thumbnails and incompatible video codecs."""
    background_tasks.add_task(run_library_repair)
    return {"status": "Repair started in background"}


async def run_library_repair():
    """Fix missing thumbnails and transcode incompatible codecs (VP9/AV1 on iOS)."""
    import subprocess

    from ..config import THUMBNAILS_DIR
    from ..library.thumbnails import cache_thumbnail

    videos = await asyncio.to_thread(store.get_recent, limit=5000)
    for v in videos:
        # 1. Check/Repair Thumbnails
        from ..library.thumbnails import get_thumbnail_path

        path = get_thumbnail_path(v.video_id, v.platform, THUMBNAILS_DIR)
        if not path or not path.exists():
            if v.raw_metadata:
                await cache_thumbnail(v.raw_metadata, THUMBNAILS_DIR)

        # 2. Check/Repair Video Codec (iOS Compatibility)
        if v.local_path and Path(v.local_path).exists():
            path = Path(v.local_path)
            if path.suffix.lower() == ".mp4":
                try:
                    # Check codec using ffprobe
                    cmd = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=codec_name",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(path),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    codec = result.stdout.strip().lower()

                    if codec in ("vp9", "av1"):
                        # Transcode to H.264
                        temp_path = path.with_suffix(".temp.mp4")
                        transcode_cmd = [
                            "ffmpeg",
                            "-i",
                            str(path),
                            "-c:v",
                            "libx264",
                            "-profile:v",
                            "main",
                            "-level",
                            "4.0",
                            "-pix_fmt",
                            "yuv420p",
                            "-c:a",
                            "copy",
                            "-movflags",
                            "+faststart",
                            "-y",
                            str(temp_path),
                        ]
                        process = subprocess.run(transcode_cmd, capture_output=True, check=False)

                        if process.returncode == 0 and temp_path.exists():
                            # Replace original
                            path.unlink()
                            temp_path.rename(path)
                        else:
                            print(f"Error transcoding {v.id}: ffmpeg returned {process.returncode}")
                            if temp_path.exists():
                                temp_path.unlink()
                except Exception as e:
                    print(f"Error repairing {v.id}: {e}")


@app.get("/api/library")
async def get_library(
    q: str | None = None,
    uploader: str | None = None,
    sort: str = "downloaded_at",
    order: str = "desc",
    limit: int = 50,
    async_store: AsyncVideoStore = Depends(get_db_dependency),
):
    """Get library videos with optional search/filter/sort."""
    if q:
        videos = await async_store.search(q, limit=limit)
    else:
        videos = await async_store.get_sorted(
            sort=sort, order=order, uploader=uploader, limit=limit
        )

    # Enrich with display names and uploader links
    results = []
    for v in videos:
        v_dict = v.__dict__.copy()
        v_dict["platform_display"] = PLATFORM_DISPLAY.get(v.platform, v.platform.capitalize())

        # Extract expanded metadata from raw_metadata if available
        if v.raw_metadata:
            v_dict["uploader_url"] = v.raw_metadata.get("uploader_url")
            v_dict["channel"] = v.raw_metadata.get("channel")
            v_dict["channel_url"] = v.raw_metadata.get("channel_url")

        results.append(v_dict)
    return results


@app.get("/api/uploaders")
def list_uploaders():
    """Return all uploaders with video counts."""
    uploaders = store.get_uploaders()
    return [
        {
            "name": u["uploader"],
            "platform": u["platform"],
            "platform_display": PLATFORM_DISPLAY.get(u["platform"], u["platform"].capitalize()),
            "count": u["count"],
        }
        for u in uploaders
    ]


@app.post("/api/downloads")
async def start_download(request: DownloadRequest):
    """Start a new download."""
    from urllib.parse import urlparse

    parsed = urlparse(request.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")
    item = queue.add(url=request.url, collection=request.collection, tags=request.tags)
    return {"id": item.id, "status": item.status.value}


@app.get("/api/downloads")
def list_downloads():
    from datetime import datetime, timedelta

    # Auto-clear items completed/failed more than 5 minutes ago
    queue.expire_stale(max_age_seconds=300)

    now = datetime.now()

    # Return items that are:
    # - Still in progress (pending/downloading)
    # - OR completed/failed within the last 60 seconds (so user sees the final state briefly)
    return [
        {
            "id": item.id,
            "url": item.url,
            "status": item.status.value,
            "progress": item.progress_percent,
            "title": item.title,
            "speed": item.speed,
            "eta": item.eta_seconds,
            "error": item.error_message,
        }
        for item in queue.items
        if item.status not in (QueueStatus.COMPLETE, QueueStatus.FAILED, QueueStatus.CANCELLED)
        or (item.completed_at and (now - item.completed_at) < timedelta(seconds=60))
    ]


@app.get("/api/downloads/{item_id}")
def get_download_status(item_id: str):
    item = queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Download not found")
    return {
        "id": item.id,
        "url": item.url,
        "status": item.status.value,
        "progress": item.progress_percent,
        "title": item.title,
        "error": item.error_message if item.status == QueueStatus.FAILED else None,
        "video_id": item.video_id,
        "local_path": item.local_path,
    }


@app.delete("/api/downloads/{item_id}")
def cancel_download(item_id: str):
    """Cancel a pending/downloading item or remove a completed/failed item."""
    item = queue.get(item_id)
    if not item:
        # Already gone, that's fine
        return {"status": "removed"}

    # Cancel and fully remove from the queue
    queue.remove_item(item_id)

    return {"status": "removed"}


# Serve thumbnails
app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# Serve static files (PWA)
static_dir = Path(__file__).parent / "static"


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/") or any(
        request.url.path.endswith(ext) for ext in [".js", ".css", ".html", ".json"]
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
