"""
Library router — browse, inspect, and manage downloaded media items.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from kairos.config import BASE_DIR, MEDIA_LIBRARY_ROOT, THUMBS_DIR

MIME_MAP = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".m4v": "video/mp4",
}
from kairos.database import get_db
from kairos.models import Clip, MediaItem, TranscriptionJob, TranscriptionSegment
from kairos.schemas import MediaItemDetail, MediaItemOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/library", tags=["library"])


def _to_absolute(relative_path: str | None, base: Path) -> Path | None:
    """Resolve a relative media path against a base directory."""
    if not relative_path:
        return None
    p = Path(relative_path)
    if p.is_absolute():
        return p
    return base / p


@router.get("", response_model=list[MediaItemOut])
def list_items(
    status: Optional[str] = Query(None, description="Filter by item_status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List media items in the library, optionally filtered by status or platform.
    Ordered by created_at descending (newest first).
    """
    q = db.query(MediaItem)
    if status:
        q = q.filter(MediaItem.item_status == status)
    if platform:
        q = q.filter(MediaItem.platform == platform)
    q = q.order_by(MediaItem.created_at.desc()).offset(offset).limit(limit)
    return q.all()


@router.get("/{item_id}", response_model=MediaItemDetail)
def get_item(item_id: str, db: Session = Depends(get_db)):
    """
    Return full detail for a single media item, including transcription status,
    segment count, and clip count.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found.")

    # Get latest transcription job status
    tj = (
        db.query(TranscriptionJob)
        .filter(TranscriptionJob.item_id == item_id)
        .order_by(TranscriptionJob.created_at.desc())
        .first()
    )
    segment_count = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id == item_id)
        .count()
    )
    clip_count = (
        db.query(Clip)
        .filter(Clip.item_id == item_id)
        .count()
    )

    detail = MediaItemDetail.model_validate(item)
    detail.transcription_job_status = tj.job_status if tj else None
    detail.transcription_job_id = tj.job_id if tj else None
    detail.segment_count = segment_count
    detail.clip_count = clip_count
    return detail


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(get_db)):
    """
    Delete a media item and all associated files (video, audio, thumbnail).
    Does NOT delete clips derived from this item — they keep their rendered files.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found.")

    # Delete files
    files_to_remove = []

    if item.file_path:
        abs_path = _to_absolute(item.file_path, MEDIA_LIBRARY_ROOT)
        if abs_path:
            files_to_remove.append(abs_path)

    if item.audio_path:
        abs_path = _to_absolute(item.audio_path, BASE_DIR / "media")
        if abs_path:
            files_to_remove.append(abs_path)

    if item.thumb_path:
        abs_path = _to_absolute(item.thumb_path, BASE_DIR / "media")
        if abs_path:
            files_to_remove.append(abs_path)

    for fpath in files_to_remove:
        try:
            if fpath.exists():
                fpath.unlink()
                logger.info("Deleted file: %s", fpath)
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", fpath, exc)

    # Delete transcription segments and jobs
    db.query(TranscriptionSegment).filter(
        TranscriptionSegment.item_id == item_id
    ).delete(synchronize_session=False)
    db.query(TranscriptionJob).filter(
        TranscriptionJob.item_id == item_id
    ).delete(synchronize_session=False)

    db.delete(item)
    db.commit()
    logger.info("Deleted media item %s and associated data", item_id)


@router.get("/{item_id}/thumbnail")
def get_thumbnail(item_id: str, db: Session = Depends(get_db)):
    """
    Serve the thumbnail image for a media item.
    Returns 404 if no thumbnail has been generated yet.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found.")
    if not item.thumb_path:
        raise HTTPException(status_code=404, detail="No thumbnail available for this item.")

    # thumb_path is stored relative to media/thumbs or as absolute
    thumb = _to_absolute(item.thumb_path, BASE_DIR / "media")
    if thumb is None or not thumb.exists():
        # Try direct resolution from project root
        thumb = BASE_DIR / item.thumb_path
        if not thumb.exists():
            raise HTTPException(status_code=404, detail="Thumbnail file not found on disk.")

    return FileResponse(
        path=str(thumb),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{item_id}/stream")
def stream_video(item_id: str, db: Session = Depends(get_db)):
    """
    Stream the source video file for a media item.
    Starlette FileResponse handles HTTP 206 range requests natively.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found.")
    if not item.file_path:
        raise HTTPException(status_code=404, detail="No video file for this item.")

    abs_path = _to_absolute(item.file_path, MEDIA_LIBRARY_ROOT)
    if abs_path is None or not abs_path.exists():
        abs_path = BASE_DIR / item.file_path
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk.")

    ext = abs_path.suffix.lower()
    media_type = MIME_MAP.get(ext, "video/mp4")

    return FileResponse(
        path=str(abs_path),
        media_type=media_type,
        headers={"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"},
    )
