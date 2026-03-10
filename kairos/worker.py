"""
Huey task queue entry points for Kairos.

Two SqliteHuey instances:
  huey_gpu   — GPU-heavy tasks (transcription, diarization, analysis) — 1 worker
  huey_light — I/O-bound tasks (download, ingest, thumb, audio extract) — 2 workers

Both use SQLite backends in database/ — no external service required.

Worker commands (run in separate terminals):
  huey_consumer kairos.worker.huey_gpu  -w 1 -k thread
  huey_consumer kairos.worker.huey_light -w 2 -k thread
"""

import logging
import os
import sys

from huey import SqliteHuey

from kairos.config import HUEY_GPU_DB, HUEY_LIGHT_DB

logger = logging.getLogger(__name__)


def _set_below_normal_priority():
    """Set worker process priority to below-normal so it never starves the desktop."""
    try:
        if sys.platform == "win32":
            import ctypes
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
            logger.info("Worker priority set to BELOW_NORMAL")
        else:
            os.nice(5)
            logger.info("Worker niceness increased by 5")
    except Exception as exc:
        logger.warning("Could not set process priority (non-fatal): %s", exc)


_set_below_normal_priority()

huey_gpu   = SqliteHuey("kairos_gpu",   filename=str(HUEY_GPU_DB))
huey_light = SqliteHuey("kairos_light", filename=str(HUEY_LIGHT_DB))


def _recover_orphaned_jobs():
    """
    On worker startup, any MediaItems stuck in 'downloading' or 'ingesting' are
    orphans from a previous crash. Reset them to 'error' so they can be retried.
    TranscriptionJobs stuck in 'running' are also reset.
    """
    try:
        from kairos.database import SessionLocal
        from kairos.models import MediaItem, TranscriptionJob
        from datetime import datetime

        db = SessionLocal()
        try:
            # Reset stuck media items
            stuck_items = (
                db.query(MediaItem)
                .filter(MediaItem.item_status.in_(["downloading", "ingesting"]))
                .all()
            )
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            for item in stuck_items:
                item.item_status = "error"
                item.error_msg = "Worker restart — reset from stuck state"
                item.updated_at = now
            if stuck_items:
                logger.info(
                    "Self-heal: reset %d stuck media item(s) to error",
                    len(stuck_items),
                )

            # Reset stuck transcription jobs
            stuck_jobs = (
                db.query(TranscriptionJob)
                .filter(TranscriptionJob.job_status == "running")
                .all()
            )
            for job in stuck_jobs:
                job.job_status = "error"
                job.error_msg = "Worker restart — reset from running state"
                job.completed_at = now
            if stuck_jobs:
                logger.info(
                    "Self-heal: reset %d stuck transcription job(s) to error",
                    len(stuck_jobs),
                )

            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("recover_orphaned_jobs failed (non-fatal): %s", exc)


# Run orphan recovery when this module is first imported (i.e. when the worker starts).
_recover_orphaned_jobs()

# Import tasks so their @huey_light.task() / @huey_gpu.task() decorators register
# them in the Huey task registry. Without this import, the consumer cannot find tasks.
import kairos.tasks  # noqa: F401, E402
