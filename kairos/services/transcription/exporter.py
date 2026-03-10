"""
Export aligned transcription segments to SRT, VTT, and JSON formats.

All functions write to the given output_path and return the path as a string.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Timestamp formatters ──────────────────────────────────────────────────────

def format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    total_ms  = int(round(seconds * 1000))
    ms        = total_ms % 1000
    total_s   = total_ms // 1000
    s         = total_s % 60
    total_min = total_s // 60
    m         = total_min % 60
    h         = total_min // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as WebVTT timestamp: HH:MM:SS.mmm"""
    total_ms  = int(round(seconds * 1000))
    ms        = total_ms % 1000
    total_s   = total_ms // 1000
    s         = total_s % 60
    total_min = total_s // 60
    m         = total_min % 60
    h         = total_min // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ── Exporters ─────────────────────────────────────────────────────────────────

def export_srt(aligned_segments: list[dict], output_path: str) -> str:
    """
    Export aligned segments to SRT format.

    Each segment becomes one subtitle cue. Speaker label is prepended to the
    text when present (e.g. "[SPEAKER_00] Hello world").

    Returns the output_path string.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for i, seg in enumerate(aligned_segments, start=1):
        start_ts = format_timestamp_srt(seg["start"])
        end_ts   = format_timestamp_srt(seg["end"])
        speaker  = seg.get("speaker", "")
        text     = seg.get("text", "").strip()

        if speaker:
            display_text = f"[{speaker}] {text}"
        else:
            display_text = text

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(display_text)
        lines.append("")   # blank line between cues

    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Exported SRT: %s (%d cues)", output_path, len(aligned_segments))
    return str(path)


def export_vtt(aligned_segments: list[dict], output_path: str) -> str:
    """
    Export aligned segments to WebVTT format.

    Returns the output_path string.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["WEBVTT", ""]

    for i, seg in enumerate(aligned_segments, start=1):
        start_ts = format_timestamp_vtt(seg["start"])
        end_ts   = format_timestamp_vtt(seg["end"])
        speaker  = seg.get("speaker", "")
        text     = seg.get("text", "").strip()

        if speaker:
            display_text = f"[{speaker}] {text}"
        else:
            display_text = text

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(display_text)
        lines.append("")

    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Exported VTT: %s (%d cues)", output_path, len(aligned_segments))
    return str(path)


def export_json(aligned_segments: list[dict], output_path: str) -> str:
    """
    Export aligned segments to JSON format with full word-level data.

    Returns the output_path string.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(aligned_segments, f, ensure_ascii=False, indent=2)

    logger.info("Exported JSON: %s (%d segments)", output_path, len(aligned_segments))
    return str(path)
