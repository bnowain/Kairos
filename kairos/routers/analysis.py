"""
Analysis API endpoints for Kairos Phase 3.

Routes:
  POST   /api/analysis/{item_id}/start          — enqueue analysis_task
  GET    /api/analysis/{item_id}/status         — analysis status + score counts
  GET    /api/analysis/{item_id}/scores         — all AnalysisScore rows
  GET    /api/analysis/{item_id}/highlights     — top scored segments with clip metadata
  POST   /api/analysis/{item_id}/clips/generate — create Clip rows for top segments
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from kairos.database import SessionLocal
from kairos.models import AnalysisScore, Clip, MediaItem, TranscriptionSegment
from kairos.schemas import (
    AnalysisScoreOut,
    ClipOut,
    HighlightSegmentOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ── POST /api/analysis/{item_id}/start ───────────────────────────────────────

@router.post("/{item_id}/start", status_code=202)
def start_analysis(item_id: str, db=Depends(_get_db)):
    """
    Enqueue the analysis task for a MediaItem.

    Requires:
      - item.item_status == "ready"
      - at least one TranscriptionSegment for this item

    Returns {"item_id": ..., "job_id": ..., "status": "queued"}
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"MediaItem {item_id!r} not found")

    if item.item_status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"MediaItem must have status='ready' (current: {item.item_status!r})",
        )

    segment_count = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id == item_id)
        .count()
    )
    if segment_count == 0:
        raise HTTPException(
            status_code=422,
            detail="MediaItem has no transcription segments — run transcription first",
        )

    job_id = str(uuid.uuid4())

    # Enqueue GPU analysis task
    from kairos.tasks import analysis_task
    analysis_task(item_id)

    logger.info("analysis: enqueued analysis_task for item %s (job_id %s)", item_id, job_id)

    return {
        "item_id": item_id,
        "job_id":  job_id,
        "status":  "queued",
    }


# ── GET /api/analysis/{item_id}/status ───────────────────────────────────────

@router.get("/{item_id}/status")
def get_analysis_status(item_id: str, db=Depends(_get_db)):
    """
    Return current analysis status: score counts per type, clip count.
    """
    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"MediaItem {item_id!r} not found")

    # Count scores by type
    score_rows = (
        db.query(AnalysisScore)
        .filter(AnalysisScore.item_id == item_id)
        .all()
    )

    type_counts: dict[str, int] = {}
    for row in score_rows:
        type_counts[row.score_type] = type_counts.get(row.score_type, 0) + 1

    clip_count = (
        db.query(Clip)
        .filter(Clip.item_id == item_id, Clip.clip_source == "ai")
        .count()
    )

    has_scores = len(score_rows) > 0
    segment_count = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id == item_id)
        .count()
    )

    if not has_scores and segment_count == 0:
        analysis_status = "no_segments"
    elif not has_scores:
        analysis_status = "not_started"
    else:
        analysis_status = "complete"

    return {
        "item_id":         item_id,
        "analysis_status": analysis_status,
        "segment_count":   segment_count,
        "score_counts":    type_counts,
        "total_scores":    len(score_rows),
        "ai_clip_count":   clip_count,
    }


# ── GET /api/analysis/{item_id}/scores ───────────────────────────────────────

@router.get("/{item_id}/scores", response_model=list[AnalysisScoreOut])
def get_analysis_scores(
    item_id: str,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    score_type: Optional[str] = Query(None, description="Filter by score_type (e.g. virality, composite)"),
    limit: int = Query(50, ge=1, le=1000),
    db=Depends(_get_db),
):
    """
    Return AnalysisScore rows for this item.
    Grouped by segment_id; includes composite score.
    """
    q = (
        db.query(AnalysisScore)
        .filter(
            AnalysisScore.item_id == item_id,
            AnalysisScore.score_value >= min_score,
        )
    )

    if score_type:
        q = q.filter(AnalysisScore.score_type == score_type)

    q = q.order_by(AnalysisScore.score_value.desc()).limit(limit)
    rows = q.all()

    return [
        AnalysisScoreOut(
            score_id      = row.score_id,
            item_id       = row.item_id,
            segment_id    = row.segment_id,
            score_type    = row.score_type,
            score_value   = row.score_value,
            score_reason  = row.score_reason,
            scorer_model  = row.scorer_model,
            created_at    = row.created_at,
        )
        for row in rows
    ]


# ── GET /api/analysis/{item_id}/highlights ───────────────────────────────────

@router.get("/{item_id}/highlights", response_model=list[HighlightSegmentOut])
def get_highlights(
    item_id: str,
    limit: int = Query(10, ge=1, le=200),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    db=Depends(_get_db),
):
    """
    Return top N scored segments with clip metadata.
    Sorted by composite virality score descending.
    """
    # Get composite scores for this item
    composite_scores = (
        db.query(AnalysisScore)
        .filter(
            AnalysisScore.item_id == item_id,
            AnalysisScore.score_type == "composite",
            AnalysisScore.score_value >= threshold,
        )
        .order_by(AnalysisScore.score_value.desc())
        .limit(limit)
        .all()
    )

    if not composite_scores:
        return []

    # Collect segment_ids and look up segment data
    segment_ids = [s.segment_id for s in composite_scores if s.segment_id]

    segments_map: dict[str, TranscriptionSegment] = {}
    if segment_ids:
        segs = (
            db.query(TranscriptionSegment)
            .filter(TranscriptionSegment.segment_id.in_(segment_ids))
            .all()
        )
        segments_map = {s.segment_id: s for s in segs}

    # Build per-segment score lookup (all score types)
    all_scores_for_item = (
        db.query(AnalysisScore)
        .filter(
            AnalysisScore.item_id == item_id,
            AnalysisScore.segment_id.in_(segment_ids),
        )
        .all()
    )

    scores_by_seg: dict[str, dict[str, AnalysisScore]] = {}
    for score_row in all_scores_for_item:
        if score_row.segment_id not in scores_by_seg:
            scores_by_seg[score_row.segment_id] = {}
        scores_by_seg[score_row.segment_id][score_row.score_type] = score_row

    # Check which segments already have clips
    clips_for_segs = (
        db.query(Clip)
        .filter(
            Clip.item_id == item_id,
            Clip.clip_source == "ai",
        )
        .all()
    )
    # Map start_ms → clip_id as a heuristic (exact clip row not directly linked to segment)
    clip_by_start: dict[int, str] = {c.start_ms: c.clip_id for c in clips_for_segs}

    results: list[HighlightSegmentOut] = []
    for cs in composite_scores:
        seg_id = cs.segment_id
        seg = segments_map.get(seg_id)
        if not seg:
            continue

        seg_scores = scores_by_seg.get(seg_id, {})
        virality_row    = seg_scores.get("virality")
        hook_row        = seg_scores.get("hook")
        emotional_row   = seg_scores.get("emotional")
        controversy_row = seg_scores.get("controversy")

        clip_id = clip_by_start.get(seg.start_ms)

        results.append(HighlightSegmentOut(
            segment_id               = seg_id,
            item_id                  = item_id,
            speaker_label            = seg.speaker_label,
            start_ms                 = seg.start_ms,
            end_ms                   = seg.end_ms,
            segment_text             = seg.segment_text,
            composite_virality_score = cs.score_value,
            llm_virality_score       = virality_row.score_value if virality_row else None,
            hook_score               = hook_row.score_value if hook_row else None,
            emotional_score          = emotional_row.score_value if emotional_row else None,
            controversy_score        = controversy_row.score_value if controversy_row else None,
            highlight_reason         = cs.score_reason or "",
            is_hook_candidate        = bool(hook_row and hook_row.score_value >= 0.6),
            clip_id                  = clip_id,
        ))

    return results


# ── POST /api/analysis/{item_id}/clips/generate ──────────────────────────────

@router.post("/{item_id}/clips/generate", status_code=201)
def generate_clips(item_id: str, db=Depends(_get_db)):
    """
    For segments above AUTO_CLIP_THRESHOLD, create Clip rows in DB.
    Returns count of clips created.
    Returns 409 if AI clips already exist for this item.
    """
    from kairos.services.analysis.scorer import AUTO_CLIP_THRESHOLD

    item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"MediaItem {item_id!r} not found")

    # 409 if AI clips already exist
    existing_clips = (
        db.query(Clip)
        .filter(Clip.item_id == item_id, Clip.clip_source == "ai")
        .count()
    )
    if existing_clips > 0:
        raise HTTPException(
            status_code=409,
            detail=f"AI clips already generated for item {item_id!r} ({existing_clips} clips exist)",
        )

    # Get composite scores above threshold
    high_scores = (
        db.query(AnalysisScore)
        .filter(
            AnalysisScore.item_id == item_id,
            AnalysisScore.score_type == "composite",
            AnalysisScore.score_value >= AUTO_CLIP_THRESHOLD,
        )
        .order_by(AnalysisScore.score_value.desc())
        .all()
    )

    if not high_scores:
        return {
            "item_id":       item_id,
            "clips_created": 0,
            "message":       f"No segments above threshold {AUTO_CLIP_THRESHOLD}",
        }

    segment_ids = [s.segment_id for s in high_scores if s.segment_id]
    segments_map: dict[str, TranscriptionSegment] = {}
    if segment_ids:
        segs = (
            db.query(TranscriptionSegment)
            .filter(TranscriptionSegment.segment_id.in_(segment_ids))
            .all()
        )
        segments_map = {s.segment_id: s for s in segs}

    now_ts = _now()
    clip_rows = []
    for score_row in high_scores:
        seg_id = score_row.segment_id
        seg = segments_map.get(seg_id)
        if not seg:
            continue

        duration_ms = max(0, seg.end_ms - seg.start_ms)
        clip_rows.append(Clip(
            clip_id        = str(uuid.uuid4()),
            item_id        = item_id,
            clip_title     = None,
            start_ms       = seg.start_ms,
            end_ms         = seg.end_ms,
            duration_ms    = duration_ms,
            clip_file_path = None,
            clip_thumb_path= None,
            virality_score = score_row.score_value,
            clip_status    = "pending",
            clip_source    = "ai",
            speaker_label  = seg.speaker_label,
            clip_transcript= seg.segment_text,
            error_msg      = None,
            created_at     = now_ts,
            updated_at     = now_ts,
        ))

    db.bulk_save_objects(clip_rows)
    db.commit()

    logger.info(
        "analysis: generated %d AI clips for item %s", len(clip_rows), item_id
    )

    return {
        "item_id":       item_id,
        "clips_created": len(clip_rows),
        "threshold":     AUTO_CLIP_THRESHOLD,
    }
