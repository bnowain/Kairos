"""
Transcription API endpoints for Kairos.

Routes:
  POST   /api/transcription/{item_id}/start    — create job + enqueue transcribe_task
  GET    /api/transcription/{item_id}/status   — job status + segment count
  GET    /api/transcription/{item_id}/segments — paginated segments
  GET    /api/transcription/{item_id}/export/{format} — srt|vtt|json FileResponse
  DELETE /api/transcription/{item_id}          — delete all segments + job
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from kairos.database import SessionLocal
from kairos.models import MediaItem, TranscriptionJob, TranscriptionSegment
from kairos.schemas import TranscriptionJobOut, TranscriptionSegmentOut
from kairos.config import BASE_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transcription", tags=["transcription"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ── POST /api/transcription/{item_id}/start ───────────────────────────────────

@router.post("/{item_id}/start", response_model=TranscriptionJobOut, status_code=202)
def start_transcription(item_id: str, db=Depends(_get_db)):
    """
    Create a TranscriptionJob and enqueue the GPU transcription task.

    Returns 404 if the item does not exist.
    Returns 409 if a job is already queued or running for this item.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"MediaItem {item_id!r} not found")

    if not item.audio_path:
        raise HTTPException(
            status_code=422,
            detail="MediaItem has no audio_path — run ingest pipeline first",
        )

    # Check for an existing active job
    existing = (
        db.query(TranscriptionJob)
        .filter(
            TranscriptionJob.item_id == item_id,
            TranscriptionJob.job_status.in_(["queued", "running"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Transcription job {existing.job_id!r} already {existing.job_status} for this item",
        )

    from kairos.config import WHISPER_MODEL
    job = TranscriptionJob(
        job_id        = str(uuid.uuid4()),
        item_id       = item_id,
        whisper_model = WHISPER_MODEL,
        language      = "en",
        job_status    = "queued",
        created_at    = _now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue GPU task
    from kairos.tasks import transcribe_task
    transcribe_task(item_id)

    # segment_count is always 0 at creation
    return TranscriptionJobOut(
        job_id        = job.job_id,
        item_id       = job.item_id,
        whisper_model = job.whisper_model,
        language      = job.language,
        job_status    = job.job_status,
        error_msg     = job.error_msg,
        started_at    = job.started_at,
        completed_at  = job.completed_at,
        created_at    = job.created_at,
        segment_count = 0,
    )


# ── GET /api/transcription/{item_id}/status ───────────────────────────────────

@router.get("/{item_id}/status", response_model=TranscriptionJobOut)
def get_transcription_status(item_id: str, db=Depends(_get_db)):
    """Return the latest TranscriptionJob status for an item, plus segment count."""
    job = (
        db.query(TranscriptionJob)
        .filter(TranscriptionJob.item_id == item_id)
        .order_by(TranscriptionJob.created_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail=f"No transcription job found for item {item_id!r}")

    segment_count = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id == item_id)
        .count()
    )

    return TranscriptionJobOut(
        job_id        = job.job_id,
        item_id       = job.item_id,
        whisper_model = job.whisper_model,
        language      = job.language,
        job_status    = job.job_status,
        error_msg     = job.error_msg,
        started_at    = job.started_at,
        completed_at  = job.completed_at,
        created_at    = job.created_at,
        segment_count = segment_count,
    )


# ── GET /api/transcription/{item_id}/segments ─────────────────────────────────

@router.get("/{item_id}/segments", response_model=list[TranscriptionSegmentOut])
def get_segments(
    item_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    speaker: str | None = Query(None, description="Filter by speaker label, e.g. SPEAKER_00"),
    db=Depends(_get_db),
):
    """
    Return paginated transcription segments for an item.

    Optional ?speaker= filter to return only segments from a specific speaker.
    """
    q = db.query(TranscriptionSegment).filter(TranscriptionSegment.item_id == item_id)
    if speaker:
        q = q.filter(TranscriptionSegment.speaker_label == speaker)

    q = q.order_by(TranscriptionSegment.start_ms)
    offset = (page - 1) * limit
    segments = q.offset(offset).limit(limit).all()

    return [
        TranscriptionSegmentOut(
            segment_id      = s.segment_id,
            item_id         = s.item_id,
            speaker_label   = s.speaker_label,
            start_ms        = s.start_ms,
            end_ms          = s.end_ms,
            segment_text    = s.segment_text,
            word_timestamps = s.word_timestamps,
            avg_logprob     = s.avg_logprob,
            no_speech_prob  = s.no_speech_prob,
        )
        for s in segments
    ]


# ── GET /api/transcription/{item_id}/export/{format} ─────────────────────────

@router.get("/{item_id}/export/{fmt}")
def export_transcription(item_id: str, fmt: str, db=Depends(_get_db)):
    """
    Download a transcription export file.

    fmt must be one of: srt, vtt, json
    """
    fmt = fmt.lower()
    if fmt not in ("srt", "vtt", "json"):
        raise HTTPException(status_code=400, detail="format must be srt, vtt, or json")

    export_dir = BASE_DIR / "media" / "exports" / item_id
    export_path = export_dir / f"transcript.{fmt}"

    if not export_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Export file not found — run transcription first (looked for {export_path})",
        )

    media_types = {
        "srt":  "application/x-subrip",
        "vtt":  "text/vtt",
        "json": "application/json",
    }

    return FileResponse(
        path=str(export_path),
        media_type=media_types[fmt],
        filename=f"{item_id}.{fmt}",
    )


# ── DELETE /api/transcription/{item_id} ───────────────────────────────────────

@router.delete("/{item_id}", status_code=200)
def delete_transcription(item_id: str, db=Depends(_get_db)):
    """
    Delete all TranscriptionSegments and TranscriptionJobs for an item.

    Does not delete the MediaItem or its audio file.
    Returns a count of deleted records.
    """
    seg_count = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id == item_id)
        .delete(synchronize_session=False)
    )
    job_count = (
        db.query(TranscriptionJob)
        .filter(TranscriptionJob.item_id == item_id)
        .delete(synchronize_session=False)
    )
    db.commit()

    logger.info(
        "Deleted transcription for item %s: %d segments, %d jobs",
        item_id, seg_count, job_count,
    )

    return {
        "deleted_segments": seg_count,
        "deleted_jobs":     job_count,
        "item_id":          item_id,
    }
