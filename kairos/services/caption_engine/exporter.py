"""
Export per-clip captions to SRT/VTT/ASS from DB segments.
Timeline-aware: adjusts timestamps to be relative to clip start (not source video).

Different from transcription/exporter.py — this is timeline-aware.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _ms_to_srt_time(ms: int) -> str:
    """Convert ms to SRT timestamp: HH:MM:SS,mmm"""
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    millis = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def _ms_to_vtt_time(ms: int) -> str:
    """Convert ms to VTT timestamp: HH:MM:SS.mmm"""
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    millis = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"


def _ms_to_ass_time(ms: int) -> str:
    """Convert ms to ASS timestamp: H:MM:SS.cc"""
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    cs = int(round((total_sec - int(total_sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _load_clip_captions(db, clip_id: str) -> list[dict]:
    """
    Load TranscriptionSegments for a clip, adjusted to clip-relative timestamps.
    Returns list of dicts: {start_ms, end_ms, text, speaker, words}
    """
    from kairos.models import Clip, TranscriptionSegment

    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
    if not clip:
        logger.warning("_load_clip_captions: clip_id %s not found", clip_id)
        return []

    clip_start_ms = clip.start_ms
    clip_end_ms = clip.end_ms

    segments = (
        db.query(TranscriptionSegment)
        .filter(
            TranscriptionSegment.item_id == clip.item_id,
            TranscriptionSegment.start_ms < clip_end_ms,
            TranscriptionSegment.end_ms > clip_start_ms,
        )
        .order_by(TranscriptionSegment.start_ms)
        .all()
    )

    cues: list[dict] = []
    for seg in segments:
        # Clamp and translate to clip-relative time
        seg_start = max(seg.start_ms, clip_start_ms) - clip_start_ms
        seg_end = min(seg.end_ms, clip_end_ms) - clip_start_ms

        if seg_end <= seg_start:
            continue

        words: list[dict] = []
        if seg.word_timestamps:
            try:
                raw_words = json.loads(seg.word_timestamps)
                for w in raw_words:
                    w_start = w.get("start_ms", seg.start_ms)
                    w_end = w.get("end_ms", seg.end_ms)
                    if w_start >= clip_end_ms or w_end <= clip_start_ms:
                        continue
                    words.append({
                        "word": w.get("word", ""),
                        "start_ms": max(w_start, clip_start_ms) - clip_start_ms,
                        "end_ms": min(w_end, clip_end_ms) - clip_start_ms,
                    })
            except Exception:
                pass

        cues.append({
            "start_ms": seg_start,
            "end_ms": seg_end,
            "text": seg.segment_text,
            "speaker": seg.speaker_label,
            "words": words,
        })

    return cues


def export_clip_captions(db, clip_id: str, fmt: str = "srt", style: dict = None) -> str:
    """
    Export captions for a single clip.
    Queries TranscriptionSegments for the clip's item_id + time range.
    Adjusts timestamps to be relative to clip start (not source video).
    Returns file content as string.
    fmt: 'srt' | 'vtt' | 'ass'
    """
    cues = _load_clip_captions(db, clip_id)

    if not cues:
        logger.info("export_clip_captions: no captions found for clip %s", clip_id)
        return ""

    fmt = fmt.lower()

    if fmt == "srt":
        lines: list[str] = []
        for idx, cue in enumerate(cues, start=1):
            start_ts = _ms_to_srt_time(cue["start_ms"])
            end_ts = _ms_to_srt_time(cue["end_ms"])
            text = cue.get("text", "")
            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    elif fmt == "vtt":
        lines = ["WEBVTT", ""]
        for idx, cue in enumerate(cues, start=1):
            start_ts = _ms_to_vtt_time(cue["start_ms"])
            end_ts = _ms_to_vtt_time(cue["end_ms"])
            text = cue.get("text", "")
            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    elif fmt == "ass":
        from kairos.services.caption_engine.styler import (
            get_default_style, build_ass_header, build_ass_events,
        )
        effective_style = style if style else get_default_style()
        header = build_ass_header(effective_style, (1920, 1080))
        events = build_ass_events(cues, effective_style)
        return header + events + "\n"

    else:
        raise ValueError(f"export_clip_captions: unsupported format '{fmt}' — use srt, vtt, or ass")
