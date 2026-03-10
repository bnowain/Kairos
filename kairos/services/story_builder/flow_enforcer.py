"""
Enforce narrative flow: deduplication, pacing gaps, transition selection.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pacing: minimum gap between clips (ms) — also the transition duration
PACING_GAPS: dict[str, int] = {
    "fast":     0,     # hard cuts, no gap
    "medium":   500,   # brief pause
    "slow":     1000,  # deliberate pause
    "moderate": 500,   # treat moderate same as medium
}

# Transition default per pacing
PACING_TRANSITIONS: dict[str, str] = {
    "fast":     "cut",
    "medium":   "fade",
    "slow":     "fade",
    "moderate": "fade",
}


def _similarity(text_a: str, text_b: str) -> float:
    """
    Simple word-overlap similarity: 2 * |intersection| / (|A| + |B|).
    Range 0–1. Returns 0.0 if either text is empty.
    """
    if not text_a or not text_b:
        return 0.0
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    total = len(words_a) + len(words_b)
    if total == 0:
        return 0.0
    return 2.0 * len(words_a & words_b) / total


def enforce_flow(
    slot_assignments: dict,
    template: dict,
    pacing: Optional[str] = None,
) -> list[dict]:
    """
    Convert slot_assignments into an ordered flat list of timeline elements.

    Steps:
    1. Flatten slots in position order into a sequence of clip elements
    2. Between clips: insert transition elements based on pacing
    3. Before first clip: optionally insert title_card if template has intro_title
    4. Remove near-duplicate clips: if two adjacent clips share > 80% transcript text,
       drop the lower-scored one
    5. Enforce pacing_gap between clips (transition duration_ms = gap)

    Returns list of element dicts.
    """
    # Resolve pacing
    effective_pacing = pacing or template.get("pacing", "medium")
    gap_ms           = PACING_GAPS.get(effective_pacing, 500)
    transition_type  = template.get("transition_default") or PACING_TRANSITIONS.get(effective_pacing, "fade")

    # Sort slots by their position in the template
    slot_positions: dict[str, int] = {
        s["slot_id"]: s.get("position", 0)
        for s in template.get("slots", [])
    }

    # Build an ordered list of (position, slot_id)
    ordered_slot_ids = sorted(
        slot_assignments.keys(),
        key=lambda sid: slot_positions.get(sid, 999),
    )

    # Flatten to clip sequence
    raw_clips: list[dict] = []
    for slot_id in ordered_slot_ids:
        for clip in slot_assignments.get(slot_id, []):
            raw_clips.append(clip)

    if not raw_clips:
        return []

    # Step 4: remove near-duplicates (adjacent clips with >80% transcript overlap)
    deduped: list[dict] = [raw_clips[0]]
    for clip in raw_clips[1:]:
        prev = deduped[-1]
        text_prev = prev.get("clip_transcript") or ""
        text_curr = clip.get("clip_transcript") or ""
        sim = _similarity(text_prev, text_curr)
        if sim > 0.80:
            # Keep higher-scored clip
            prev_score = prev.get("slot_score", prev.get("virality_score", 0.0)) or 0.0
            curr_score = clip.get("slot_score", clip.get("virality_score", 0.0)) or 0.0
            if curr_score > prev_score:
                deduped[-1] = clip
            # else drop curr silently
            logger.debug(
                "flow_enforcer: dropped near-duplicate clip %s (similarity=%.2f)",
                clip["clip_id"], sim,
            )
        else:
            deduped.append(clip)

    # Step 3: optional title_card from template intro_title
    elements: list[dict] = []
    intro_title = template.get("intro_title")
    if intro_title:
        elements.append({
            "element_type": "title_card",
            "duration_ms":  3000,
            "params":       {"text": intro_title},
        })

    # Step 1 + 2 + 5: build final sequence with transitions
    position_counter = len(elements)  # account for any title_card at start
    for i, clip in enumerate(deduped):
        elements.append({
            "element_type": "clip",
            "clip_id":      clip["clip_id"],
            "duration_ms":  clip.get("duration_ms", 0) or 0,
            "position":     position_counter,
        })
        position_counter += 1

        # Insert transition between clips (not after the last one)
        if i < len(deduped) - 1:
            trans_duration = gap_ms  # gap IS the transition duration
            if trans_duration > 0 or transition_type != "cut":
                # Always insert even for 0ms cut transitions so the editor knows
                elements.append({
                    "element_type":    "transition",
                    "transition_type": transition_type,
                    "duration_ms":     trans_duration,
                    "position":        position_counter,
                })
                position_counter += 1

    return elements
