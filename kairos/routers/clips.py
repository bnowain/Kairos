"""
Clip CRUD + extraction API router.

Endpoints:
  GET    /api/clips                    — list clips (filters: item_id, status, source, limit, offset)
  POST   /api/clips                    — create a manual clip and enqueue extraction
  GET    /api/clips/{clip_id}          — single clip detail
  PATCH  /api/clips/{clip_id}          — update clip_title
  DELETE /api/clips/{clip_id}          — delete clip row + files on disk
  GET    /api/clips/{clip_id}/download — FileResponse for the clip video
  GET    /api/clips/{clip_id}/thumbnail — FileResponse for the clip thumbnail
  POST   /api/clips/{clip_id}/extract  — re-trigger extraction for a clip
  POST   /api/clips/batch/extract      — enqueue extraction for all pending clips
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from kairos.config import BASE_DIR
from kairos.database import SessionLocal
from kairos.models import Clip, MediaItem
from kairos.schemas import ClipCreate, ClipOut, ClipUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clips", tags=["clips"])


# ── Dependency ────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_clip_or_404(clip_id: str, db) -> Clip:
    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id!r} not found")
    return clip


def _delete_file_if_exists(relative_path: Optional[str]) -> None:
    """Delete a file stored at BASE_DIR / relative_path, if it exists."""
    if not relative_path:
        return
    abs_path = BASE_DIR / relative_path
    try:
        if abs_path.exists():
            abs_path.unlink()
            logger.info("_delete_file_if_exists: deleted %s", abs_path)
    except Exception as exc:
        logger.warning("_delete_file_if_exists: could not delete %s — %s", abs_path, exc)


# ── GET /api/clips ────────────────────────────────────────────────────────────

@router.get("", response_model=List[ClipOut])
def list_clips(
    item_id: Optional[str] = Query(None, description="Filter by media item"),
    status:  Optional[str] = Query(None, description="Filter by clip_status"),
    source:  Optional[str] = Query(None, description="Filter by clip_source: ai | manual"),
    limit:   int           = Query(50, ge=1, le=500),
    offset:  int           = Query(0, ge=0),
    db = Depends(get_db),
):
    query = db.query(Clip)
    if item_id:
        query = query.filter(Clip.item_id == item_id)
    if status:
        query = query.filter(Clip.clip_status == status)
    if source:
        query = query.filter(Clip.clip_source == source)
    query = query.order_by(Clip.created_at.desc())
    clips = query.offset(offset).limit(limit).all()
    return clips


# ── POST /api/clips ───────────────────────────────────────────────────────────

@router.post("", response_model=ClipOut, status_code=201)
def create_clip(body: ClipCreate, db = Depends(get_db)):
    """Create a manual clip and enqueue extraction immediately."""
    # Validate item exists and is ready
    item = db.query(MediaItem).filter(MediaItem.item_id == body.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"MediaItem {body.item_id!r} not found")
    if item.item_status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"MediaItem {body.item_id!r} is not ready (status={item.item_status!r})",
        )
    if not item.file_path:
        raise HTTPException(
            status_code=422,
            detail=f"MediaItem {body.item_id!r} has no file_path",
        )

    # Validate boundaries
    if body.start_ms >= body.end_ms:
        raise HTTPException(
            status_code=422,
            detail="start_ms must be less than end_ms",
        )
    duration_ms = body.end_ms - body.start_ms
    if duration_ms < 500:
        raise HTTPException(
            status_code=422,
            detail="Clip duration must be at least 500 ms",
        )

    now_ts  = _now()
    clip_id = str(uuid.uuid4())

    clip = Clip(
        clip_id         = clip_id,
        item_id         = body.item_id,
        clip_title      = body.clip_title,
        start_ms        = body.start_ms,
        end_ms          = body.end_ms,
        duration_ms     = duration_ms,
        clip_file_path  = None,
        clip_thumb_path = None,
        virality_score  = None,
        clip_status     = "pending",
        clip_source     = "manual",
        speaker_label   = None,
        clip_transcript = None,
        error_msg       = None,
        created_at      = now_ts,
        updated_at      = now_ts,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)

    # Enqueue extraction
    from kairos.tasks import extract_clip_task
    extract_clip_task(clip_id, remove_silence=body.remove_silence)
    logger.info("create_clip: enqueued extract_clip_task for clip %s", clip_id)

    return clip


# ── GET /api/clips/{clip_id} ──────────────────────────────────────────────────

@router.get("/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: str, db = Depends(get_db)):
    return _get_clip_or_404(clip_id, db)


# ── PATCH /api/clips/{clip_id} ────────────────────────────────────────────────

@router.patch("/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: str, body: ClipUpdate, db = Depends(get_db)):
    clip = _get_clip_or_404(clip_id, db)
    if body.clip_title is not None:
        clip.clip_title = body.clip_title
    clip.updated_at = _now()
    db.commit()
    db.refresh(clip)
    return clip


# ── DELETE /api/clips/{clip_id} ───────────────────────────────────────────────

@router.delete("/{clip_id}")
def delete_clip(clip_id: str, db = Depends(get_db)):
    clip = _get_clip_or_404(clip_id, db)

    # Delete files from disk
    _delete_file_if_exists(clip.clip_file_path)
    _delete_file_if_exists(clip.clip_thumb_path)

    db.delete(clip)
    db.commit()
    logger.info("delete_clip: deleted clip %s", clip_id)
    return {"deleted": True}


# ── GET /api/clips/{clip_id}/download ────────────────────────────────────────

@router.get("/{clip_id}/download")
def download_clip(clip_id: str, db = Depends(get_db)):
    clip = _get_clip_or_404(clip_id, db)

    if clip.clip_status != "ready" or not clip.clip_file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Clip {clip_id!r} is not ready (status={clip.clip_status!r})",
        )

    abs_path = BASE_DIR / clip.clip_file_path
    if not abs_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Clip file not found on disk: {clip.clip_file_path}",
        )

    filename = abs_path.name
    return FileResponse(
        path=str(abs_path),
        media_type="video/mp4",
        filename=filename,
        headers={"Accept-Ranges": "bytes"},
    )


# ── GET /api/clips/{clip_id}/thumbnail ───────────────────────────────────────

@router.get("/{clip_id}/thumbnail")
def get_clip_thumbnail(clip_id: str, db = Depends(get_db)):
    clip = _get_clip_or_404(clip_id, db)

    if not clip.clip_thumb_path:
        raise HTTPException(
            status_code=404,
            detail=f"Clip {clip_id!r} has no thumbnail",
        )

    abs_path = BASE_DIR / clip.clip_thumb_path
    if not abs_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Thumbnail file not found on disk: {clip.clip_thumb_path}",
        )

    return FileResponse(path=str(abs_path), media_type="image/jpeg")


# ── POST /api/clips/{clip_id}/extract ────────────────────────────────────────

@router.post("/{clip_id}/extract")
def re_extract_clip(clip_id: str, db = Depends(get_db)):
    """Re-trigger extraction for a clip (useful for retrying errors)."""
    clip = _get_clip_or_404(clip_id, db)

    clip.clip_status = "pending"
    clip.error_msg   = None
    clip.updated_at  = _now()
    db.commit()

    from kairos.tasks import extract_clip_task
    extract_clip_task(clip_id)
    logger.info("re_extract_clip: re-enqueued extract_clip_task for clip %s", clip_id)

    return {"clip_id": clip_id, "status": "queued"}


# ── POST /api/clips/batch/extract ────────────────────────────────────────────

@router.post("/batch/extract")
def batch_extract(
    body: Optional[dict] = None,
    db = Depends(get_db),
):
    """
    Enqueue extract_clip_task for all pending clips.

    Optional body: {"item_id": "<uuid>"} to restrict to one item.
    """
    item_id = None
    if body:
        item_id = body.get("item_id")

    from kairos.services.clip_engine.batch_clipper import enqueue_pending_clips
    count = enqueue_pending_clips(db, item_id=item_id)

    return {"enqueued": count}
