"""
Quick Jobs API — Mobile M1.

POST /api/jobs/quick          — create + start an orchestrated quick job
GET  /api/jobs/{job_id}       — poll job status / progress
GET  /api/jobs                — list recent quick jobs (newest first)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.models import QuickJob
from kairos.schemas import QuickJobIn, QuickJobOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _to_out(job: QuickJob) -> QuickJobOut:
    return QuickJobOut(
        job_id           = job.job_id,
        job_status       = job.job_status,
        stage_label      = job.stage_label,
        progress         = job.progress,
        item_ids         = json.loads(job.item_ids) if job.item_ids else None,
        timeline_id      = job.timeline_id,
        render_id        = job.render_id,
        output_path      = job.output_path,
        error_msg        = job.error_msg,
        created_at       = job.created_at,
        updated_at       = job.updated_at,
    )


# ── POST /api/jobs/quick ──────────────────────────────────────────────────────

@router.post("/quick", response_model=QuickJobOut, status_code=202)
def create_quick_job(req: QuickJobIn, db: Session = Depends(get_db)):
    """
    Create and immediately start a single-touch pipeline job.

    Chains: download → transcribe → analyze → generate story → render.
    Returns the job_id for polling via GET /api/jobs/{job_id}.
    """
    if not req.urls:
        raise HTTPException(status_code=422, detail="urls must contain at least one URL")

    if req.aspect_ratio not in ("9:16", "16:9", "1:1"):
        raise HTTPException(status_code=422, detail="aspect_ratio must be 9:16, 16:9, or 1:1")

    now = _now()
    job = QuickJob(
        job_id           = str(uuid.uuid4()),
        urls             = json.dumps(req.urls),
        template_id      = req.template_id,
        caption_style_id = req.caption_style_id,
        aspect_ratio     = req.aspect_ratio,
        job_status       = "queued",
        stage_label      = "Queued",
        progress         = 0,
        created_at       = now,
        updated_at       = now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch background orchestration thread
    from kairos.services.orchestrator import start_quick_job
    start_quick_job(job.job_id)

    logger.info("Quick job %s created for %d URL(s)", job.job_id, len(req.urls))
    return _to_out(job)


# ── GET /api/jobs/{job_id} ────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=QuickJobOut)
def get_quick_job(job_id: str, db: Session = Depends(get_db)):
    """Return current status / progress for a quick job."""
    job = db.query(QuickJob).filter(QuickJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"QuickJob {job_id!r} not found")
    return _to_out(job)


# ── GET /api/jobs ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[QuickJobOut])
def list_quick_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return recent quick jobs, newest first."""
    jobs = (
        db.query(QuickJob)
        .order_by(QuickJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_out(j) for j in jobs]
