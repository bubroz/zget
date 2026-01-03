import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.responses import FileResponse

from ..config import DB_PATH, THUMBNAILS_DIR, ensure_directories, PLATFORM_DISPLAY
from ..db import VideoStore
from ..queue import DownloadQueue, QueueStatus

# Initialize app
app = FastAPI(title="zget Server", version="0.3.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
ensure_directories()
store = VideoStore(DB_PATH)
queue = DownloadQueue(max_concurrent=4)  # Default to 4 for server


# Background startup
@app.on_event("startup")
async def startup_event():
    await queue.start()


@app.on_event("shutdown")
async def shutdown_event():
    await queue.stop()


# Models
class DownloadRequest(BaseModel):
    url: str
    collection: Optional[str] = None
    tags: Optional[list[str]] = None


# Routes
@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/api/media/{video_id}")
async def get_media(video_id: str):
    # Try to find by platform video_id (string) or internal ID (int)
    # Search in library
    videos = store.get_recent(limit=1000)  # Simple search for now
    video = next((v for v in videos if v.video_id == video_id), None)

    if not video:
        # Try finding by internal ID
        try:
            v_id = int(video_id)
            all_v = store.get_recent(limit=5000)
            video = next((v for v in all_v if v.id == v_id), None)
        except ValueError:
            pass

    if not video or not video.local_path:
        raise HTTPException(status_code=404, detail="Video file not found")

    path = Path(video.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@app.get("/api/library")
def get_library(q: Optional[str] = None, limit: int = 50):
    if q:
        videos = store.search(q, limit=limit)
    else:
        videos = store.get_recent(limit=limit)

    # Enrich with display names
    results = []
    for v in videos:
        v_dict = v.__dict__.copy()
        v_dict["platform_display"] = PLATFORM_DISPLAY.get(v.platform, v.platform.capitalize())
        results.append(v_dict)
    return results


@app.post("/api/downloads")
async def start_download(request: DownloadRequest):
    item = queue.add(url=request.url, collection=request.collection, tags=request.tags)
    return {"id": item.id, "status": item.status.value}


@app.get("/api/downloads")
def list_downloads():
    return [
        {
            "id": item.id,
            "url": item.url,
            "status": item.status.value,
            "progress": item.progress_percent,
            "title": item.title,
            "speed": item.speed,
            "eta": item.eta_seconds,
        }
        for item in queue._items.values()
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


# Serve thumbnails
app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# Serve static files (PWA)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
