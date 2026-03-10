"""
Batch clip extraction orchestration.

Provides helpers to query pending clips and enqueue extract_clip_task for each.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def get_pending_clips(db, item_id: str = None) -> list:
    """
    Query Clip rows with clip_status='pending'.

    If item_id is provided, filters to that item only.
    Returns a list of Clip ORM objects.
    """
    from kairos.models import Clip

    query = db.query(Clip).filter(Clip.clip_status == "pending")
    if item_id:
        query = query.filter(Clip.item_id == item_id)
    return query.all()


def enqueue_pending_clips(db, item_id: str = None) -> int:
    """
    Find all pending clips and enqueue extract_clip_task for each.

    Marks each clip as clip_status='extracting' before enqueuing.
    Returns the count of tasks enqueued.
    """
    from kairos.models import Clip
    from kairos.tasks import extract_clip_task

    clips = get_pending_clips(db, item_id=item_id)
    if not clips:
        logger.info(
            "enqueue_pending_clips: no pending clips%s",
            f" for item {item_id}" if item_id else "",
        )
        return 0

    now_ts = _now()
    count = 0
    for clip in clips:
        clip.clip_status = "extracting"
        clip.updated_at  = now_ts
        db.commit()
        extract_clip_task(clip.clip_id)
        count += 1
        logger.info(
            "enqueue_pending_clips: enqueued extract_clip_task for clip %s", clip.clip_id
        )

    logger.info(
        "enqueue_pending_clips: enqueued %d task(s)%s",
        count,
        f" for item {item_id}" if item_id else "",
    )
    return count
