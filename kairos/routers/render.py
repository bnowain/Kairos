"""
Render queue API — Phase 6.

POST /api/render            — enqueue a render job for a timeline
GET  /api/render            — list render jobs
GET  /api/render/{id}       — single job detail
GET  /api/render/{id}/download  — FileResponse for completed render
DELETE /api/render/{id}     — delete job + output file
POST /api/render/{id}/retry — re-enqueue a failed job
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.models import RenderJob, Timeline
from kairos.schemas import RenderJobOut, RenderRequest
from kairos.services.renderer.queue_manager import create_render_job, start_render_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/render", tags=["render"])


# ── POST /api/render ──────────────────────────────────────────────────────────

@router.post("", response_model=RenderJobOut, status_code=201)
def enqueue_render(req: RenderRequest, db: Session = Depends(get_db)):
    """
    Create a RenderJob and enqueue render_task on huey_gpu.
    Timeline must exist.
    """
    timeline = db.query(Timeline).filter(Timeline.timeline_id == req.timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline {req.timeline_id} not found")

    if req.quality not in ("preview", "final"):
        raise HTTPException(status_code=422, detail="quality must be 'preview' or 'final'")

    if req.reframe_aspect_ratio is not None and req.reframe_aspect_ratio not in ("16:9", "9:16", "1:1"):
        raise HTTPException(
            status_code=422,
            detail="reframe_aspect_ratio must be '16:9', '9:16', '1:1', or null",
        )

    # Store extra render params as JSON
    render_params = json.dumps({
        "apply_captions": req.apply_captions,
        "caption_style_id": req.caption_style_id,
        "reframe_aspect_ratio": req.reframe_aspect_ratio,
    })

    job = create_render_job(
        db=db,
        timeline_id=req.timeline_id,
        quality=req.quality,
        render_params=render_params,
    )

    # Enqueue on huey_gpu
    try:
        from kairos.tasks import render_task
        render_task(job.render_id)
        logger.info("enqueue_render: queued render_id=%s quality=%s", job.render_id, req.quality)
    except Exception as exc:
        logger.error("enqueue_render: failed to enqueue render_task — %s", exc)
        # Job is already created in DB; mark it as error
        job.render_status = "error"
        job.error_msg = f"Failed to enqueue task: {exc}"
        db.commit()

    return job


# ── GET /api/render ───────────────────────────────────────────────────────────

@router.get("", response_model=list[RenderJobOut])
def list_render_jobs(
    timeline_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List render jobs. Filter by timeline_id and/or status."""
    q = db.query(RenderJob)
    if timeline_id:
        q = q.filter(RenderJob.timeline_id == timeline_id)
    if status:
        q = q.filter(RenderJob.render_status == status)
    q = q.order_by(RenderJob.created_at.desc()).limit(limit)
    return q.all()


# ── GET /api/render/{render_id} ───────────────────────────────────────────────

@router.get("/{render_id}", response_model=RenderJobOut)
def get_render_job(render_id: str, db: Session = Depends(get_db)):
    """Get single render job detail."""
    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"RenderJob {render_id} not found")
    return job


# ── GET /api/render/{render_id}/download ─────────────────────────────────────

@router.get("/{render_id}/download")
def download_render(render_id: str, db: Session = Depends(get_db)):
    """
    Stream the completed render output as a FileResponse.
    Returns 404 if job not done or output file missing.
    """
    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"RenderJob {render_id} not found")

    if job.render_status != "done":
        raise HTTPException(
            status_code=404,
            detail=f"RenderJob {render_id} is not done yet (status={job.render_status})",
        )

    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Output file not found for render {render_id}",
        )

    filename = Path(job.output_path).name
    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=filename,
    )


# ── DELETE /api/render/{render_id} ───────────────────────────────────────────

@router.delete("/{render_id}")
def delete_render_job(render_id: str, db: Session = Depends(get_db)):
    """Delete the render job record and its output file."""
    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"RenderJob {render_id} not found")

    # Delete output file if it exists
    if job.output_path:
        try:
            output = Path(job.output_path)
            if output.exists():
                output.unlink()
                logger.info("delete_render_job: deleted file %s", job.output_path)
        except Exception as exc:
            logger.warning("delete_render_job: could not delete file %s — %s", job.output_path, exc)

    db.delete(job)
    db.commit()
    return {"deleted": True, "render_id": render_id}


# ── POST /api/render/{render_id}/retry ───────────────────────────────────────

@router.post("/{render_id}/retry", response_model=RenderJobOut)
def retry_render_job(render_id: str, db: Session = Depends(get_db)):
    """Reset a failed/errored render job to queued and re-enqueue it."""
    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"RenderJob {render_id} not found")

    if job.render_status == "running":
        raise HTTPException(status_code=409, detail="Job is currently running — cannot retry")

    # Reset state
    job.render_status = "queued"
    job.error_msg = None
    job.output_path = None
    job.encoder = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)

    try:
        from kairos.tasks import render_task
        render_task(job.render_id)
        logger.info("retry_render_job: re-queued render_id=%s", render_id)
    except Exception as exc:
        logger.error("retry_render_job: failed to re-enqueue — %s", exc)
        job.render_status = "error"
        job.error_msg = f"Failed to enqueue task: {exc}"
        db.commit()

    return job
