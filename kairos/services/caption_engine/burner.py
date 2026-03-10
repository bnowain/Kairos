"""
Burn ASS subtitles into a video using FFmpeg.

Note: this is mostly superseded by passing caption_ass_path to the main render command,
but kept for standalone use (e.g. re-burn after caption edit).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from kairos.config import VIDEO_ENCODER

logger = logging.getLogger(__name__)


def burn_captions(
    input_video: str,
    ass_path: str,
    output_path: str,
    encoder: str = None,
) -> dict:
    """
    Burn subtitles from .ass file into video.
    Uses FFmpeg subtitles filter: -vf subtitles={ass_path}
    Returns {"success": bool, "output_path": str, "error": str|None}

    Note: this is now mostly superseded by passing caption_ass_path to the
    main render command, but kept for standalone use (e.g. re-burn after edit).
    """
    if encoder is None:
        encoder = VIDEO_ENCODER

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Escape path for FFmpeg filter syntax
    safe_ass = ass_path.replace("\\", "/").replace("'", "\\'").replace(":", "\\:")

    if encoder == "h264_nvenc":
        video_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    else:
        video_args = ["-c:v", "libx264", "-preset", "slow", "-crf", "20"]

    ffmpeg_args = [
        "-y",
        "-i", input_video,
        "-vf", f"subtitles='{safe_ass}'",
    ] + video_args + [
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(
            ["ffmpeg"] + ffmpeg_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        msg = "burn_captions: FFmpeg timed out after 3600s"
        logger.error(msg)
        return {"success": False, "output_path": output_path, "error": msg}
    except FileNotFoundError:
        msg = "burn_captions: ffmpeg not found in PATH"
        logger.error(msg)
        return {"success": False, "output_path": output_path, "error": msg}

    if result.returncode != 0:
        logger.error(
            "burn_captions: FFmpeg failed (rc=%d) stderr:\n%s",
            result.returncode, result.stderr[-3000:],
        )
        return {
            "success": False,
            "output_path": output_path,
            "error": f"FFmpeg exit code {result.returncode}: {result.stderr[-500:]}",
        }

    logger.info("burn_captions: completed — %s", output_path)
    return {"success": True, "output_path": output_path, "error": None}
