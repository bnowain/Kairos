"""
Render job state machine helpers.
All functions accept a SQLAlchemy session and operate synchronously.
"""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def create_render_job(db, timeline_id: str, quality: str = "preview", render_params: str = None):
    """
    Create a RenderJob row with status='queued'. Return ORM object.
    render_params: optional JSON string with extra params (apply_captions, caption_style_id, etc.)
    """
    from kairos.models import RenderJob

    job = RenderJob(
        render_id=str(uuid.uuid4()),
        timeline_id=timeline_id,
        render_quality=quality,
        output_path=None,
        encoder=None,
        render_status="queued",
        error_msg=None,
        render_params=render_params,
        started_at=None,
        completed_at=None,
        created_at=_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_render_job(db, render_id: str) -> None:
    """Set status='running', started_at=now."""
    from kairos.models import RenderJob

    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        logger.error("start_render_job: render_id %s not found", render_id)
        return
    job.render_status = "running"
    job.started_at = _now()
    db.commit()


def complete_render_job(db, render_id: str, output_path: str, encoder: str) -> None:
    """Set status='done', output_path, encoder, completed_at=now."""
    from kairos.models import RenderJob

    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        logger.error("complete_render_job: render_id %s not found", render_id)
        return
    job.render_status = "done"
    job.output_path = output_path
    job.encoder = encoder
    job.completed_at = _now()
    db.commit()


def fail_render_job(db, render_id: str, error_msg: str) -> None:
    """Set status='error', error_msg, completed_at=now."""
    from kairos.models import RenderJob

    job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if not job:
        logger.error("fail_render_job: render_id %s not found", render_id)
        return
    job.render_status = "error"
    job.error_msg = str(error_msg)[:1000]
    job.completed_at = _now()
    db.commit()


def get_ffprobe_duration_ms(file_path: str) -> int:
    """
    Run ffprobe to get video duration in ms. Returns 0 on failure.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            duration_sec = float(result.stdout.strip())
            return int(duration_sec * 1000)
    except Exception as exc:
        logger.warning("get_ffprobe_duration_ms: failed for %s — %s", file_path, exc)
    return 0
