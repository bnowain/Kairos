"""
Generate ASS/SRT caption data from TranscriptionSegments for a timeline.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def generate_timeline_captions(
    db,
    timeline_elements: list[dict],
    clip_file_map: dict[str, str],
    style: dict = None,
) -> list[dict]:
    """
    Build a list of caption cue dicts for all clip elements in the timeline.

    For each clip element:
    1. Find the source item_id and segment time range (start_ms, end_ms)
    2. Query TranscriptionSegments that overlap the clip's time range
    3. Adjust segment timestamps relative to the clip's position in the timeline
       (add element.start_ms to each segment's start/end)
    4. Return caption cues:
       [{"start_ms": int, "end_ms": int, "text": str, "speaker": str|None,
         "words": [...]}]
    """
    from kairos.models import Clip, TranscriptionSegment

    caption_cues: list[dict] = []

    clip_elements = [e for e in timeline_elements if e.get("element_type") == "clip"]
    if not clip_elements:
        logger.info("generate_timeline_captions: no clip elements found in timeline")
        return caption_cues

    # Track cumulative timeline position for each element
    # element.start_ms is the position within the timeline
    for el in clip_elements:
        clip_id = el.get("clip_id")
        if not clip_id:
            continue

        # Load the Clip row to get item_id and source time range
        clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
        if not clip:
            logger.warning("generate_timeline_captions: clip_id %s not found, skipping", clip_id)
            continue

        item_id = clip.item_id
        clip_start_ms = clip.start_ms    # offset into source video
        clip_end_ms = clip.end_ms        # end offset in source video
        timeline_start_ms = el.get("start_ms", 0)  # position in output timeline

        # Query segments that overlap [clip_start_ms, clip_end_ms] in the source
        segments = (
            db.query(TranscriptionSegment)
            .filter(
                TranscriptionSegment.item_id == item_id,
                TranscriptionSegment.start_ms < clip_end_ms,
                TranscriptionSegment.end_ms > clip_start_ms,
            )
            .order_by(TranscriptionSegment.start_ms)
            .all()
        )

        if not segments:
            logger.debug(
                "generate_timeline_captions: no segments found for clip %s "
                "[%d–%d ms] in item %s",
                clip_id, clip_start_ms, clip_end_ms, item_id,
            )
            continue

        for seg in segments:
            # Clamp segment to clip boundaries (source time)
            seg_start = max(seg.start_ms, clip_start_ms)
            seg_end = min(seg.end_ms, clip_end_ms)

            # Translate to timeline time:
            # timeline_pos = timeline_start_ms + (source_pos - clip_start_ms)
            tl_start = timeline_start_ms + (seg_start - clip_start_ms)
            tl_end = timeline_start_ms + (seg_end - clip_start_ms)

            if tl_end <= tl_start:
                continue

            # Parse word timestamps and adjust to timeline time
            words: list[dict] = []
            if seg.word_timestamps:
                try:
                    raw_words = json.loads(seg.word_timestamps)
                    for w in raw_words:
                        w_start = w.get("start_ms", seg.start_ms)
                        w_end = w.get("end_ms", seg.end_ms)
                        # Only include words within clip range
                        if w_start >= clip_end_ms or w_end <= clip_start_ms:
                            continue
                        words.append({
                            "word": w.get("word", ""),
                            "start_ms": timeline_start_ms + (max(w_start, clip_start_ms) - clip_start_ms),
                            "end_ms": timeline_start_ms + (min(w_end, clip_end_ms) - clip_start_ms),
                        })
                except Exception as exc:
                    logger.warning(
                        "generate_timeline_captions: failed to parse word_timestamps for seg %s: %s",
                        seg.segment_id, exc,
                    )

            caption_cues.append({
                "start_ms": tl_start,
                "end_ms": tl_end,
                "text": seg.segment_text,
                "speaker": seg.speaker_label,
                "words": words,
            })

    # Sort by timeline start time
    caption_cues.sort(key=lambda c: c["start_ms"])
    logger.info("generate_timeline_captions: generated %d caption cues", len(caption_cues))
    return caption_cues
