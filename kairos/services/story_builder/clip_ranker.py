"""
Multi-signal clip ranking for Story Builder slot assignment.
Ranks a pool of clips by relevance to a given set of score signals.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Signal → AnalysisScore.score_type mapping
SIGNAL_TO_SCORE_TYPE: dict[str, str] = {
    "virality":    "composite",
    "emotional":   "emotional",
    "controversy": "controversy",
    "hook":        "hook",
    "reaction":    "audience_reaction",
    "coherence":   "topic_coherence",
    # qa is not covered by SIGNAL_TO_SCORE_TYPE — fall back gracefully
    "qa":          "composite",
}


def rank_clips_for_slot(
    clips: list[dict],
    score_signals: list[str],
    max_clips: int,
    max_duration_ms: int,
    already_used: set[str],
) -> list[dict]:
    """
    Rank and select clips for a single narrative slot.

    Algorithm:
    1. Filter out already_used clip_ids
    2. For each clip, compute slot_score = mean of score_values for the requested signals
       (use 0.0 if a signal score is missing for that clip)
    3. Sort by slot_score descending
    4. Select top clips respecting max_clips and max_duration_ms constraints
       (accumulate duration_ms, stop when limit reached)
    5. Return selected clips in order

    Returns list of clip dicts with 'slot_score' added.
    """
    # Step 1: filter already-used
    candidates = [c for c in clips if c["clip_id"] not in already_used]

    if not candidates:
        return []

    if not score_signals:
        # No signals specified — rank by composite virality_score
        score_signals = ["virality"]

    # Step 2: compute slot_score per candidate
    scored: list[dict] = []
    for clip in candidates:
        scores_dict = clip.get("scores", {})
        signal_values: list[float] = []
        for signal in score_signals:
            score_type = SIGNAL_TO_SCORE_TYPE.get(signal, signal)
            val = scores_dict.get(score_type)
            if val is None:
                # Also try virality_score top-level field for composite
                if score_type == "composite":
                    val = clip.get("virality_score", 0.0) or 0.0
                else:
                    val = 0.0
            signal_values.append(float(val))

        slot_score = sum(signal_values) / len(signal_values) if signal_values else 0.0
        clip_copy = dict(clip)
        clip_copy["slot_score"] = round(slot_score, 6)
        scored.append(clip_copy)

    # Step 3: sort descending by slot_score
    scored.sort(key=lambda c: c["slot_score"], reverse=True)

    # Step 4: accumulate under max_clips + max_duration_ms
    selected: list[dict] = []
    accumulated_ms = 0
    for clip in scored:
        if len(selected) >= max_clips:
            break
        clip_dur = clip.get("duration_ms", 0) or 0
        if max_duration_ms > 0 and accumulated_ms + clip_dur > max_duration_ms:
            # Try to fit if nothing selected yet (allow at least one clip)
            if not selected:
                selected.append(clip)
                accumulated_ms += clip_dur
            continue
        selected.append(clip)
        accumulated_ms += clip_dur

    return selected


def load_clips_with_scores(
    db,
    item_ids: Optional[list[str]] = None,
    clip_ids: Optional[list[str]] = None,
) -> list[dict]:
    """
    Load Clip rows from DB and join their AnalysisScore values into a flat dict.

    Returns list of clip dicts with a nested 'scores' dict for all score types.
    Filters to only clips with clip_status='ready'.
    Joins AnalysisScore via item_id matching segment start_ms/end_ms overlap.
    """
    from kairos.models import AnalysisScore, Clip

    # Build base query for ready clips
    query = db.query(Clip).filter(Clip.clip_status == "ready")

    if clip_ids is not None:
        query = query.filter(Clip.clip_id.in_(clip_ids))
    elif item_ids is not None:
        query = query.filter(Clip.item_id.in_(item_ids))

    clips_orm = query.all()

    if not clips_orm:
        return []

    # Collect all item_ids represented in this clip set
    all_item_ids = list({c.item_id for c in clips_orm})

    # Load all AnalysisScores for these items in one query
    score_rows = (
        db.query(AnalysisScore)
        .filter(AnalysisScore.item_id.in_(all_item_ids))
        .filter(AnalysisScore.segment_id.isnot(None))
        .all()
    )

    # Load TranscriptionSegments to map segment → time range
    from kairos.models import TranscriptionSegment
    seg_rows = (
        db.query(TranscriptionSegment)
        .filter(TranscriptionSegment.item_id.in_(all_item_ids))
        .all()
    )

    # Build segment_id → {start_ms, end_ms} lookup
    seg_map: dict[str, dict] = {
        s.segment_id: {"start_ms": s.start_ms, "end_ms": s.end_ms}
        for s in seg_rows
    }

    # Build (item_id, segment_id) → {score_type: score_value}
    seg_scores: dict[tuple[str, str], dict[str, float]] = {}
    for row in score_rows:
        key = (row.item_id, row.segment_id)
        if key not in seg_scores:
            seg_scores[key] = {}
        seg_scores[key][row.score_type] = float(row.score_value)

    result: list[dict] = []
    for clip in clips_orm:
        # Find overlapping scores: segments whose time range overlaps this clip's range
        aggregated: dict[str, list[float]] = {}
        for (item_id, seg_id), scores_dict in seg_scores.items():
            if item_id != clip.item_id:
                continue
            seg = seg_map.get(seg_id)
            if seg is None:
                continue
            # Overlap check: segment overlaps clip if seg.start < clip.end and seg.end > clip.start
            if seg["start_ms"] < clip.end_ms and seg["end_ms"] > clip.start_ms:
                for score_type, score_val in scores_dict.items():
                    aggregated.setdefault(score_type, []).append(score_val)

        # Average each score type across overlapping segments
        averaged: dict[str, float] = {
            st: round(sum(vals) / len(vals), 6)
            for st, vals in aggregated.items()
            if vals
        }

        # Ensure all expected score types are present (default 0.0)
        for st in ("composite", "emotional", "controversy", "hook", "audience_reaction", "topic_coherence"):
            averaged.setdefault(st, 0.0)

        result.append({
            "clip_id":          clip.clip_id,
            "item_id":          clip.item_id,
            "start_ms":         clip.start_ms,
            "end_ms":           clip.end_ms,
            "duration_ms":      clip.duration_ms,
            "clip_file_path":   clip.clip_file_path,
            "clip_status":      clip.clip_status,
            "clip_transcript":  clip.clip_transcript,
            "speaker_label":    clip.speaker_label,
            "virality_score":   float(clip.virality_score or 0.0),
            "scores":           averaged,
        })

    return result
