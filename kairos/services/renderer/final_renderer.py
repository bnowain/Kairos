"""
High-quality final renderer.
Tries NVENC first, falls back to libx264 -preset slow.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from kairos.config import NVENC_AVAILABLE, VIDEO_ENCODER
from kairos.services.renderer.ffmpeg_builder import build_render_command
from kairos.services.renderer.queue_manager import get_ffprobe_duration_ms

logger = logging.getLogger(__name__)


def _try_render(ffmpeg_args: list[str], label: str) -> tuple[bool, str]:
    """
    Run FFmpeg with given args. Returns (success, error_message).
    """
    try:
        result = subprocess.run(
            ["ffmpeg"] + ffmpeg_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        return False, f"{label}: FFmpeg timed out after 3600s"
    except FileNotFoundError:
        return False, f"{label}: ffmpeg not found in PATH"

    if result.returncode != 0:
        logger.error(
            "%s: FFmpeg failed (rc=%d) stderr:\n%s",
            label, result.returncode, result.stderr[-3000:],
        )
        return False, f"FFmpeg exit code {result.returncode}: {result.stderr[-500:]}"

    return True, ""


def render_final(
    timeline_elements: list[dict],
    clip_file_map: dict[str, str],
    output_path: str,
    aspect_ratio: str = "16:9",
    caption_ass_path: str = None,
    crop_params: dict = None,
) -> dict:
    """
    High-quality final render. Tries NVENC first, falls back to libx264.
    Returns {"success": bool, "output_path": str, "duration_ms": int,
             "encoder_used": str, "error": str|None}
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Determine encoder strategy
    encoders_to_try: list[str] = []
    if NVENC_AVAILABLE:
        encoders_to_try.append("h264_nvenc")
    encoders_to_try.append("libx264")

    encoder_used = ""
    last_error = ""

    for enc in encoders_to_try:
        try:
            ffmpeg_args = build_render_command(
                timeline_elements=timeline_elements,
                clip_file_map=clip_file_map,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                quality="final",
                caption_ass_path=caption_ass_path,
                encoder=enc,
                crop_params=crop_params,
            )
        except ValueError as exc:
            logger.error("render_final: build_render_command failed — %s", exc)
            return {
                "success": False,
                "output_path": output_path,
                "duration_ms": 0,
                "encoder_used": "",
                "error": str(exc),
            }

        logger.info("render_final: attempting encode with %s → %s", enc, output_path)
        t0 = time.perf_counter()

        success, err = _try_render(ffmpeg_args, label=f"render_final[{enc}]")
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        if success:
            encoder_used = enc
            logger.info("render_final: completed with %s in %dms — %s", enc, elapsed_ms, output_path)
            duration_ms = get_ffprobe_duration_ms(output_path)
            return {
                "success": True,
                "output_path": output_path,
                "duration_ms": duration_ms,
                "encoder_used": encoder_used,
                "error": None,
            }

        last_error = err
        logger.warning("render_final: %s failed, trying next encoder. Error: %s", enc, err[:200])

    # All encoders failed
    logger.error("render_final: all encoders failed. Last error: %s", last_error)
    return {
        "success": False,
        "output_path": output_path,
        "duration_ms": 0,
        "encoder_used": "",
        "error": last_error,
    }
