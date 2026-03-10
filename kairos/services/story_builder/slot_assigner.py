"""
Assign clips to narrative slots defined by a story template.
"""

import logging

from kairos.services.story_builder import clip_ranker

logger = logging.getLogger(__name__)


def assign_slots(
    template: dict,
    clips: list[dict],
    pacing_override: str = None,
) -> dict:
    """
    Assign clips to each slot in the template.

    Returns:
    {
        "slot_assignments": {
            "hook": [clip_dict, ...],
            "peak_1": [clip_dict, ...],
            ...
        },
        "unassigned_clips": [clip_dict, ...],
        "total_duration_ms": int,
        "clip_count": int,
        "coverage_pct": float,
    }

    Algorithm:
    1. Sort slots by position
    2. Process required slots first, then optional
    3. For each slot call clip_ranker.rank_clips_for_slot() with already_used set
    4. Compute total_duration_ms, coverage_pct
    """
    slots = template.get("slots", [])
    if not slots:
        return {
            "slot_assignments":  {},
            "unassigned_clips":  list(clips),
            "total_duration_ms": 0,
            "clip_count":        0,
            "coverage_pct":      0.0,
        }

    # Sort slots by position
    sorted_slots = sorted(slots, key=lambda s: s.get("position", 0))

    # Process required slots first, then optional (preserving position order within each group)
    required_slots  = [s for s in sorted_slots if s.get("required", False)]
    optional_slots  = [s for s in sorted_slots if not s.get("required", False)]
    ordered_slots   = required_slots + optional_slots

    already_used: set[str] = set()
    slot_assignments: dict[str, list[dict]] = {}
    required_filled = 0
    required_total  = len(required_slots)
    total_duration_ms = 0

    for slot in ordered_slots:
        slot_id       = slot.get("slot_id", "unknown")
        score_signals = slot.get("score_signals", ["virality"])
        max_clips     = slot.get("max_clips", 1)
        max_dur       = slot.get("max_duration_ms", 0) or 0

        selected = clip_ranker.rank_clips_for_slot(
            clips=clips,
            score_signals=score_signals,
            max_clips=max_clips,
            max_duration_ms=max_dur,
            already_used=already_used,
        )

        slot_assignments[slot_id] = selected

        if selected:
            if slot.get("required", False):
                required_filled += 1
            for c in selected:
                already_used.add(c["clip_id"])
                total_duration_ms += c.get("duration_ms", 0) or 0
        else:
            if slot.get("required", False):
                logger.warning(
                    "slot_assigner: no clips available for required slot '%s'", slot_id
                )

    # Unassigned clips — clips not picked into any slot but above 0 virality
    unassigned = [c for c in clips if c["clip_id"] not in already_used]

    # coverage_pct: fraction of required slots that were filled
    if required_total > 0:
        coverage_pct = round(required_filled / required_total, 4)
    else:
        coverage_pct = 1.0  # no required slots → 100% coverage

    clip_count = sum(len(v) for v in slot_assignments.values())

    return {
        "slot_assignments":  slot_assignments,
        "unassigned_clips":  unassigned,
        "total_duration_ms": total_duration_ms,
        "clip_count":        clip_count,
        "coverage_pct":      coverage_pct,
    }
