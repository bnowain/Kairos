"""
Acquisition router — on-demand downloads and monitored source management.
"""

import logging
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.models import AcquisitionSource, MediaItem
from kairos.schemas import (
    AcquisitionSourceCreate,
    AcquisitionSourceOut,
    AcquisitionSourceUpdate,
    DownloadRequest,
    DownloadResponse,
)
from kairos.services.acquisition.deduplicator import is_duplicate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _detect_platform(url: str) -> str:
    """Infer platform from URL for pre-creating the MediaItem."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "instagram.com" in url_lower:
        return "instagram"
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    if "rumble.com" in url_lower:
        return "rumble"
    if "vimeo.com" in url_lower:
        return "vimeo"
    return "other"


# ── Camera-roll / file upload ─────────────────────────────────────────────────

@router.post("/upload", response_model=DownloadResponse, status_code=202)
def upload_video(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Accept a video file uploaded from the user's device (camera roll, local file).
    Saves to media_library/local/{year}/ and immediately enqueues the ingest pipeline.
    """
    from kairos.tasks import ingest_task
    from kairos.config import MEDIA_LIBRARY_ROOT

    now = _now()
    year = now[:4]
    item_id = str(uuid.uuid4())

    original_name = file.filename or "upload.mp4"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "mp4"

    dest_dir = MEDIA_LIBRARY_ROOT / "local" / year
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{item_id}.{ext}"

    try:
        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")
    finally:
        file.file.close()

    # Store path relative to BASE_DIR so ingest_task can resolve it
    from kairos.config import BASE_DIR
    rel_path = str(dest_path.relative_to(BASE_DIR))

    item = MediaItem(
        item_id=item_id,
        platform="local",
        item_title=title or original_name,
        file_path=rel_path,
        item_status="downloaded",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()

    ingest_task(item_id)

    logger.info("Uploaded local file: item_id=%s path=%s", item_id, rel_path)
    return DownloadResponse(
        item_id=item_id,
        status="ingesting",
        message=f"File saved. Track progress via GET /api/library/{item_id}",
    )


# ── On-demand download ────────────────────────────────────────────────────────

@router.post("/download", response_model=DownloadResponse, status_code=202)
def enqueue_download(req: DownloadRequest, db: Session = Depends(get_db)):
    """
    Enqueue a one-off video download.

    Creates a MediaItem in 'queued' status and dispatches a download_task
    to the huey_light worker queue. Returns immediately with the item_id.
    """
    from kairos.tasks import download_task

    platform = _detect_platform(req.url)

    # Create MediaItem record so the caller can track progress via item_id
    item_id = str(uuid.uuid4())
    now = _now()
    item = MediaItem(
        item_id=item_id,
        source_id=req.source_id,
        platform=platform,
        original_url=req.url,
        item_status="queued",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()

    # Dispatch background download task
    download_task(url=req.url, item_id=item_id, source_id=req.source_id)

    logger.info("Enqueued download: item_id=%s url=%s", item_id, req.url)
    return DownloadResponse(
        item_id=item_id,
        status="queued",
        message=f"Download queued. Track progress via GET /api/library/{item_id}",
    )


# ── Acquisition sources ───────────────────────────────────────────────────────

@router.get("/sources", response_model=list[AcquisitionSourceOut])
def list_sources(db: Session = Depends(get_db)):
    """List all configured acquisition sources."""
    return db.query(AcquisitionSource).order_by(AcquisitionSource.created_at.desc()).all()


@router.post("/sources", response_model=AcquisitionSourceOut, status_code=201)
def create_source(body: AcquisitionSourceCreate, db: Session = Depends(get_db)):
    """
    Add a new monitored source (YouTube channel, TikTok user, RSS feed, etc.).
    Kairos will poll this source according to schedule_cron.
    """
    existing = db.query(AcquisitionSource).filter(
        AcquisitionSource.source_url == body.source_url
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A source with this URL already exists.")

    now = _now()
    source = AcquisitionSource(
        source_id=str(uuid.uuid4()),
        source_type=body.source_type,
        source_url=body.source_url,
        source_name=body.source_name,
        platform=body.platform,
        schedule_cron=body.schedule_cron,
        enabled=body.enabled,
        download_quality=body.download_quality,
        created_at=now,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    logger.info("Created acquisition source: %s (%s)", source.source_id, body.source_url)
    return source


@router.put("/sources/{source_id}", response_model=AcquisitionSourceOut)
def update_source(
    source_id: str,
    body: AcquisitionSourceUpdate,
    db: Session = Depends(get_db),
):
    """Update a source's name, cron schedule, enabled flag, or download quality."""
    source = db.query(AcquisitionSource).filter(
        AcquisitionSource.source_id == source_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if body.source_name is not None:
        source.source_name = body.source_name
    if body.schedule_cron is not None:
        source.schedule_cron = body.schedule_cron
    if body.enabled is not None:
        source.enabled = body.enabled
    if body.download_quality is not None:
        source.download_quality = body.download_quality

    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    """Delete a monitored source. Does not delete already-downloaded items."""
    source = db.query(AcquisitionSource).filter(
        AcquisitionSource.source_id == source_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    db.delete(source)
    db.commit()
    logger.info("Deleted acquisition source: %s", source_id)


@router.post("/sources/{source_id}/poll", response_model=dict)
def poll_source_now(source_id: str, db: Session = Depends(get_db)):
    """
    Manually trigger an immediate poll of a monitored source.
    Discovers new items from the channel/feed and enqueues downloads for any
    not already in the library.
    """
    from kairos.tasks import download_task

    source = db.query(AcquisitionSource).filter(
        AcquisitionSource.source_id == source_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source is disabled. Enable it before polling.")

    # Use yt-dlp to list available items from the source URL without downloading.
    # Each item that isn't already in the library gets a MediaItem created and a
    # download_task enqueued.
    import subprocess
    import json as _json

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", '{"id": %(id)j, "title": %(title)j, "url": %(webpage_url)j, "duration": %(duration)j}',
        "--no-warnings",
        source.source_url,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=120
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="yt-dlp timed out while polling source.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="yt-dlp not installed.")

    queued = 0
    skipped = 0
    errors = 0

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            entry = _json.loads(line)
        except _json.JSONDecodeError:
            errors += 1
            continue

        video_id = entry.get("id")
        video_url = entry.get("url") or source.source_url
        if not video_id and not video_url:
            errors += 1
            continue

        # Check for duplicate by platform_video_id
        platform = source.platform
        existing = is_duplicate(db, platform, video_id)
        if existing:
            skipped += 1
            continue

        # Create MediaItem and enqueue download
        now = _now()
        item_id = str(uuid.uuid4())
        item = MediaItem(
            item_id=item_id,
            source_id=source_id,
            platform=platform,
            platform_video_id=video_id,
            item_title=entry.get("title"),
            duration_seconds=entry.get("duration"),
            original_url=video_url,
            item_status="queued",
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        db.commit()

        download_task(url=video_url, item_id=item_id, source_id=source_id)
        queued += 1

    # Update last_polled_at
    source.last_polled_at = _now()
    db.commit()

    logger.info(
        "Poll source %s: queued=%d skipped=%d errors=%d",
        source_id, queued, skipped, errors,
    )
    return {
        "source_id": source_id,
        "queued": queued,
        "skipped_duplicates": skipped,
        "parse_errors": errors,
    }
