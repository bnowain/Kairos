"""
System router — health, config, and job status endpoints.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kairos.config import (
    CUDA_AVAILABLE,
    DATABASE_PATH,
    KAIROS_PORT,
    MEDIA_LIBRARY_ROOT,
    NVENC_AVAILABLE,
    OLLAMA_HOST,
    VIDEO_ENCODER,
    WHISPER_COMPUTE,
    WHISPER_DEVICE,
    WHISPER_MODEL,
)
from kairos.database import get_db
from kairos.models import RenderJob, TranscriptionJob
from kairos.schemas import ConfigOut, HealthOut, JobStatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])

MC_URL = "http://127.0.0.1:8860"
MC_PROJECT_ROOT = Path("/mnt/e/0-Automated-Apps/Mission_Control")


@router.get("/health", response_model=HealthOut)
def health():
    """Service health check. Returns 200 when the API is up."""
    return HealthOut(
        status="ok",
        version="0.1.0",
        cuda_available=CUDA_AVAILABLE,
        nvenc_available=NVENC_AVAILABLE,
    )


@router.get("/config", response_model=ConfigOut)
def get_config():
    """Return current runtime configuration (no secrets)."""
    return ConfigOut(
        port=KAIROS_PORT,
        media_library_root=str(MEDIA_LIBRARY_ROOT),
        database_path=str(DATABASE_PATH),
        ollama_host=OLLAMA_HOST,
        whisper_model=WHISPER_MODEL,
        whisper_device=WHISPER_DEVICE,
        whisper_compute=WHISPER_COMPUTE,
        video_encoder=VIDEO_ENCODER,
        cuda_available=CUDA_AVAILABLE,
        nvenc_available=NVENC_AVAILABLE,
    )


@router.get("/jobs", response_model=list[JobStatusOut])
def list_recent_jobs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """
    Return the 50 most recent jobs across render and transcription queues,
    ordered by creation time descending.
    """
    render_jobs = (
        db.query(RenderJob)
        .order_by(RenderJob.created_at.desc())
        .limit(25)
        .all()
    )
    transcription_jobs = (
        db.query(TranscriptionJob)
        .order_by(TranscriptionJob.created_at.desc())
        .limit(25)
        .all()
    )

    results: list[dict[str, Any]] = []

    for rj in render_jobs:
        results.append(JobStatusOut(
            job_type="render",
            job_id=rj.render_id,
            timeline_id=rj.timeline_id,
            job_status=rj.render_status,
            error_msg=rj.error_msg,
            started_at=rj.started_at,
            completed_at=rj.completed_at,
            created_at=rj.created_at,
        ))

    for tj in transcription_jobs:
        results.append(JobStatusOut(
            job_type="transcription",
            job_id=tj.job_id,
            item_id=tj.item_id,
            job_status=tj.job_status,
            error_msg=tj.error_msg,
            started_at=tj.started_at,
            completed_at=tj.completed_at,
            created_at=tj.created_at,
        ))

    # Sort combined list by created_at descending
    results.sort(key=lambda j: j.created_at, reverse=True)
    return results[:50]


# ── Mission Control status / control ─────────────────────────────────────────

@router.get("/mc/status")
def mc_status():
    """Check if Mission Control is reachable at localhost:8860."""
    try:
        resp = httpx.get(f"{MC_URL}/api/health", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            return {"available": True, "status": data.get("status", "ok")}
    except Exception:
        pass
    return {"available": False, "status": "offline"}


@router.post("/mc/start")
def mc_start():
    """
    Start Mission Control as a background process.
    Returns immediately — caller should poll /api/mc/status to confirm it's up.
    """
    run_script = MC_PROJECT_ROOT / "run.py"
    if not run_script.exists():
        return {"started": False, "error": "Mission Control not found at expected path"}

    mc_venv_python = MC_PROJECT_ROOT / ".venv" / "bin" / "python"
    python_exe = str(mc_venv_python) if mc_venv_python.exists() else sys.executable

    try:
        subprocess.Popen(
            [python_exe, str(run_script), "--no-browser", "--no-cleanup"],
            cwd=str(MC_PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("mc_start: launched Mission Control via %s", run_script)
        return {"started": True}
    except Exception as exc:
        logger.error("mc_start: failed to launch Mission Control: %s", exc)
        return {"started": False, "error": str(exc)}
