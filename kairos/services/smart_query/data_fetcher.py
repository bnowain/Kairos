"""
Fetch candidate segments from Kairos library based on structured filters.

SQ-1 supports Kairos-only queries. SQ-4 will add civic_media via Atlas.
"""

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from kairos.models import MediaItem, TranscriptionSegment

logger = logging.getLogger(__name__)


def fetch_kairos_candidates(
    db: Session,
    filters: Optional[dict] = None,
    max_candidates: int = 100,
) -> list[dict]:
    """
    Query transcription_segments from Kairos library with optional filters.

    Supported filters:
        speaker: str          — partial match on speaker_label
        item_id: str          — exact match on item_id
        item_channel: str     — partial match on media_items.item_channel
        date_after: str       — ISO 8601, media_items.published_at >= value
        date_before: str      — ISO 8601, media_items.published_at <= value
        keyword: str          — substring match on segment_text

    Returns list of dicts ready for intent scoring.
    """
    filters = filters or {}

    query = (
        db.query(TranscriptionSegment, MediaItem)
        .join(MediaItem, TranscriptionSegment.item_id == MediaItem.item_id)
        .filter(MediaItem.item_status == "ready")
    )

    if filters.get("speaker"):
        query = query.filter(
            TranscriptionSegment.speaker_label.ilike(f"%{filters['speaker']}%")
        )

    if filters.get("item_id"):
        query = query.filter(TranscriptionSegment.item_id == filters["item_id"])

    if filters.get("item_channel"):
        query = query.filter(
            MediaItem.item_channel.ilike(f"%{filters['item_channel']}%")
        )

    if filters.get("date_after"):
        query = query.filter(MediaItem.published_at >= filters["date_after"])

    if filters.get("date_before"):
        query = query.filter(MediaItem.published_at <= filters["date_before"])

    if filters.get("keyword"):
        query = query.filter(
            TranscriptionSegment.segment_text.ilike(f"%{filters['keyword']}%")
        )

    rows = query.order_by(TranscriptionSegment.start_ms).limit(max_candidates).all()

    candidates = []
    for seg, item in rows:
        candidates.append({
            "candidate_origin": "kairos",
            "candidate_item_id": seg.item_id,
            "candidate_segment_id": seg.segment_id,
            "candidate_speaker": seg.speaker_label,
            "candidate_text": seg.segment_text,
            "candidate_start_ms": seg.start_ms,
            "candidate_end_ms": seg.end_ms,
            "candidate_video_title": item.item_title,
            "candidate_video_date": item.published_at,
            "candidate_source_url": item.original_url,
        })

    logger.info(
        "data_fetcher: found %d candidates from Kairos (filters=%s)",
        len(candidates), filters,
    )
    return candidates
