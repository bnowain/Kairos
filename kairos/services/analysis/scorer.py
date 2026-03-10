"""
Composite virality score aggregation.
Combines all analysis signals into a single ranked score per segment.

Weights sum to 1.0. Adjust here to tune scoring behaviour.
"""

import logging

logger = logging.getLogger(__name__)

# ── Score weights (must sum to 1.0) ───────────────────────────────────────────
WEIGHTS = {
    "llm_virality":          0.30,
    "llm_hook":              0.15,
    "llm_emotional":         0.10,
    "llm_controversy":       0.10,
    "heuristic_emotion":     0.10,
    "heuristic_controversy": 0.10,
    "audience_reaction":     0.10,
    "topic_coherence":       0.05,
}

AUTO_CLIP_THRESHOLD = 0.60  # segments above this score get auto-clip rows created

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"


def _safe_float(value, default: float = 0.0) -> float:
    """Convert a value to float, returning default on failure."""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def compute_composite_scores(
    segments: list[dict],
    llm_scores: list[dict],
    reaction_scores: list[dict],
    emotion_scores: list[dict],
    controversy_scores: list[dict],
    embedding_scores: list[dict],
) -> list[dict]:
    """
    Returns segments with 'composite_virality_score' (0.0-1.0) added.
    Also adds 'is_auto_clip_candidate' = True if score > AUTO_CLIP_THRESHOLD.

    All input score lists are derived from the same original segment list —
    matched by positional index. Missing signals default to 0.0.

    Segments are sorted by composite_virality_score descending.
    """
    # Build lookup maps by segment_id for each score source
    # We also keep positional fallback (index) in case segment_ids diverge

    def _build_map(score_list: list[dict], id_key: str = "segment_id") -> dict:
        return {item[id_key]: item for item in score_list if id_key in item}

    llm_map          = _build_map(llm_scores)
    reaction_map     = _build_map(reaction_scores, "segment_id") if reaction_scores else {}
    emotion_map      = _build_map(emotion_scores, "segment_id") if emotion_scores else {}
    controversy_map  = _build_map(controversy_scores, "segment_id") if controversy_scores else {}
    embedding_map    = _build_map(embedding_scores, "segment_id") if embedding_scores else {}

    # Build positional fallbacks (for score lists that used the segment dict directly)
    # reaction/emotion/controversy/embedding scores are added IN PLACE to segment dicts,
    # so they're already in the segments list. We read them from there.

    result = []
    for i, seg in enumerate(segments):
        seg_id = seg.get("segment_id", "")

        # ── LLM scores (separate list, matched by segment_id) ─────────────────
        llm = llm_map.get(seg_id, {})
        # Positional fallback if id not found
        if not llm and i < len(llm_scores):
            llm = llm_scores[i]

        llm_virality    = _safe_float(llm.get("virality_score",    0.0))
        llm_hook        = _safe_float(llm.get("hook_score",        0.0))
        llm_emotional   = _safe_float(llm.get("emotional_score",   0.0))
        llm_controversy = _safe_float(llm.get("controversy_score", 0.0))

        # ── Heuristic scores (embedded in segment dict by scorers) ─────────────
        heuristic_emotion     = _safe_float(seg.get("heuristic_emotion_score",     0.0))
        heuristic_controversy = _safe_float(seg.get("heuristic_controversy_score", 0.0))
        audience_reaction     = _safe_float(seg.get("audience_reaction_score",     0.0))
        topic_coherence       = _safe_float(seg.get("topic_coherence_score",       0.5))

        # ── Composite weighted sum ─────────────────────────────────────────────
        composite = (
            WEIGHTS["llm_virality"]          * llm_virality
            + WEIGHTS["llm_hook"]              * llm_hook
            + WEIGHTS["llm_emotional"]         * llm_emotional
            + WEIGHTS["llm_controversy"]       * llm_controversy
            + WEIGHTS["heuristic_emotion"]     * heuristic_emotion
            + WEIGHTS["heuristic_controversy"] * heuristic_controversy
            + WEIGHTS["audience_reaction"]     * audience_reaction
            + WEIGHTS["topic_coherence"]       * topic_coherence
        )
        composite = round(max(0.0, min(1.0, composite)), 4)

        # Build enriched copy of segment
        enriched = dict(seg)
        enriched["composite_virality_score"]  = composite
        enriched["is_auto_clip_candidate"]    = composite >= AUTO_CLIP_THRESHOLD
        enriched["llm_virality_score"]        = llm_virality
        enriched["llm_hook_score"]            = llm_hook
        enriched["llm_emotional_score"]       = llm_emotional
        enriched["llm_controversy_score"]     = llm_controversy
        enriched["highlight_reason"]          = llm.get("highlight_reason", "")
        enriched["is_hook_candidate"]         = bool(llm.get("is_hook_candidate", False))

        result.append(enriched)

    # Sort by composite score descending
    result.sort(key=lambda s: s["composite_virality_score"], reverse=True)

    logger.info(
        "scorer: computed composite scores for %d segments — %d above threshold %.2f",
        len(result),
        sum(1 for s in result if s["is_auto_clip_candidate"]),
        AUTO_CLIP_THRESHOLD,
    )

    return result
