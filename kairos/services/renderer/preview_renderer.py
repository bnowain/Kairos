"""
Fast low-quality preview renderer.
Uses libx264 ultrafast, 1280px wide, no NVENC.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from kairos.services.renderer.ffmpeg_builder import build_render_command
from kairos.services.renderer.queue_manager import get_ffprobe_duration_ms

logger = logging.getLogger(__name__)


def render_preview(
    timeline_elements: list[dict],
    clip_file_map: dict[str, str],
    output_path: str,
    aspect_ratio: str = "16:9",
    caption_ass_path: str = None,
) -> dict:
    """
    Fast low-quality render for preview/scrubbing.
    Uses libx264 ultrafast, 1280px wide, no NVENC.
    Returns {"success": bool, "output_path": str, "duration_ms": int, "error": str|None}
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg_args = build_render_command(
            timeline_elements=timeline_elements,
            clip_file_map=clip_file_map,
            output_path=output_path,
            aspect_ratio=aspect_ratio,
            quality="preview",
            caption_ass_path=caption_ass_path,
            encoder="libx264",
            crop_params=None,
        )
    except ValueError as exc:
        logger.error("render_preview: build_render_command failed — %s", exc)
        return {"success": False, "output_path": output_path, "duration_ms": 0, "error": str(exc)}

    logger.info("render_preview: starting FFmpeg for output=%s", output_path)
    t0 = time.perf_counter()

    try:
        result = subprocess.run(
            ["ffmpeg"] + ffmpeg_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        msg = "render_preview: FFmpeg timed out after 3600s"
        logger.error(msg)
        return {"success": False, "output_path": output_path, "duration_ms": 0, "error": msg}
    except FileNotFoundError:
        msg = "render_preview: ffmpeg not found in PATH"
        logger.error(msg)
        return {"success": False, "output_path": output_path, "duration_ms": 0, "error": msg}

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if result.returncode != 0:
        logger.error(
            "render_preview: FFmpeg failed (rc=%d) stderr:\n%s",
            result.returncode,
            result.stderr[-3000:],
        )
        return {
            "success": False,
            "output_path": output_path,
            "duration_ms": 0,
            "error": f"FFmpeg exit code {result.returncode}: {result.stderr[-500:]}",
        }

    logger.info("render_preview: completed in %dms — %s", elapsed_ms, output_path)

    duration_ms = get_ffprobe_duration_ms(output_path)

    return {
        "success": True,
        "output_path": output_path,
        "duration_ms": duration_ms,
        "error": None,
    }
