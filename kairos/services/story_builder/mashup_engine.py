"""
Multi-source mashup: combine clips from multiple MediaItems into one timeline.
"""

import logging
from typing import Optional

from kairos.services.story_builder import clip_ranker, slot_assigner, flow_enforcer, timeline_builder

logger = logging.getLogger(__name__)


def build_mashup(
    db,
    name: str,
    item_ids: list[str],
    template_id: str,
    aspect_ratio: str = "16:9",
    min_score: float = 0.5,
    project_id: Optional[str] = None,
) -> dict:
    """
    Build a mashup timeline from clips across multiple source videos.

    Algorithm:
    1. Load all ready clips from all item_ids via clip_ranker.load_clips_with_scores()
    2. Filter to clips with composite virality_score >= min_score
    3. Load template
    4. Run slot_assigner.assign_slots()
    5. Run flow_enforcer.enforce_flow()
    6. Run timeline_builder.build_timeline()
    7. Return timeline dict
    """
    from kairos.services.story_builder.template_loader import load_template

    logger.info(
        "mashup_engine: building mashup '%s' from %d source(s) using template '%s'",
        name, len(item_ids), template_id,
    )

    # Step 1: Load all ready clips with their scores
    clips = clip_ranker.load_clips_with_scores(db, item_ids=item_ids)
    logger.info("mashup_engine: loaded %d ready clips", len(clips))

    # Step 2: Filter by min_score (composite score)
    if min_score > 0:
        clips = [
            c for c in clips
            if (c.get("scores", {}).get("composite", 0.0) or 0.0) >= min_score
            or (c.get("virality_score", 0.0) or 0.0) >= min_score
        ]
        logger.info(
            "mashup_engine: %d clips pass min_score=%.2f filter", len(clips), min_score
        )

    # Step 3: Load template
    template = load_template(template_id)

    # Step 4: Assign clips to narrative slots
    assignment_result = slot_assigner.assign_slots(template=template, clips=clips)
    logger.info(
        "mashup_engine: slot assignment — %d clips in slots, coverage=%.1f%%",
        assignment_result["clip_count"],
        assignment_result["coverage_pct"] * 100,
    )

    # Step 5: Enforce flow
    elements = flow_enforcer.enforce_flow(
        slot_assignments=assignment_result["slot_assignments"],
        template=template,
    )
    logger.info("mashup_engine: flow enforcer produced %d elements", len(elements))

    # Step 6: Build and persist timeline
    timeline = timeline_builder.build_timeline(
        db=db,
        name=name,
        template_id=template_id,
        elements=elements,
        aspect_ratio=aspect_ratio,
        project_id=project_id,
    )

    logger.info(
        "mashup_engine: created timeline %s — %d elements, %dms total",
        timeline["timeline_id"],
        timeline["element_count"],
        timeline["target_duration_ms"] or 0,
    )

    return timeline
