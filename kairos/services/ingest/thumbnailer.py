"""
Thumbnail generator for Kairos media items.

Uses FFmpeg to seek to 10% of the video duration and extract a single frame,
scaled to 640x360 (16:9 standard preview size).

Output: media/thumbs/{item_id}.jpg
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_THUMB_WIDTH  = 640
_THUMB_HEIGHT = 360


def generate_thumbnail(
    video_path: str,
    output_path: str,
    duration_seconds: float = 0.0,
) -> bool:
    """
    Extract a thumbnail frame from a video file.

    Seeks to 10% of the video duration (or 5 seconds if duration is unknown).
    Scales the frame to 640x360, maintaining aspect ratio with black-bar padding.

    Args:
        video_path:       Absolute path to the source video file.
        output_path:      Absolute path for the output JPEG thumbnail.
        duration_seconds: Known duration in seconds; used to pick seek position.
                          If 0, ffprobe is used to determine duration.

    Returns:
        True on success, False if ffmpeg fails (non-raising — thumbnail is optional).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Determine seek position (10% of video duration, min 1s, max 60s)
    if duration_seconds <= 0:
        duration_seconds = _probe_duration(video_path)

    if duration_seconds > 0:
        seek_sec = max(1.0, min(duration_seconds * 0.1, 60.0))
    else:
        seek_sec = 5.0  # safe default for unknown-length content

    # Scale filter: fit into 640x360 box, pad with black bars (preserves aspect ratio)
    scale_filter = (
        f"scale={_THUMB_WIDTH}:{_THUMB_HEIGHT}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={_THUMB_WIDTH}:{_THUMB_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{seek_sec:.2f}",   # fast seek before input
        "-i", video_path,
        "-vf", scale_filter,
        "-vframes", "1",            # extract exactly one frame
        "-q:v", "3",               # JPEG quality (2=best, 31=worst; 3 is visually lossless)
        output_path,
    ]

    logger.info("Thumbnail command: %s", " ".join(cmd))

    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logger.warning(
            "Thumbnail generation failed (exit %d) for %s:\n%s",
            result.returncode,
            video_path,
            result.stderr[-500:],
        )
        return False

    if not Path(output_path).exists():
        logger.warning("ffmpeg exited 0 but thumbnail not found at %s", output_path)
        return False

    logger.info("Thumbnail generated: %s (seek=%.1fs)", output_path, seek_sec)
    return True


def _probe_duration(video_path: str) -> float:
    """Return video duration in seconds using ffprobe."""
    import json

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        return 0.0
    try:
        info = json.loads(result.stdout)
        return float(info["format"].get("duration", 0.0))
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0
