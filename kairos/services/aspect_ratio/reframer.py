"""
Compute crop boxes for aspect ratio conversion.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

# Output resolution map
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
}


def get_source_dimensions(video_path: str) -> tuple[int, int]:
    """Use ffprobe to get (width, height) of a video file."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("x")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as exc:
        logger.warning("get_source_dimensions: ffprobe failed for %s — %s", video_path, exc)
    return (1920, 1080)  # safe default


def compute_crop_box(
    source_w: int,
    source_h: int,
    target_ratio: str,
    face_position: dict = None,
) -> dict:
    """
    Compute the FFmpeg crop box {x, y, w, h} to convert source to target_ratio.

    Strategy:
    - Compute the largest rectangle of target_ratio that fits in source
    - If face_position provided: center the crop on the face's cx/cy
    - Else: center crop
    - Clamp x/y to valid bounds (0 to source_w-w, 0 to source_h-h)

    Returns {"x": int, "y": int, "w": int, "h": int,
             "scale_w": int, "scale_h": int,  # target output size
             "ffmpeg_vf": str}  # ready-to-use vf string: "crop=w:h:x:y,scale=sw:sh"
    """
    target_out = RESOLUTIONS.get(target_ratio, RESOLUTIONS["16:9"])
    scale_w, scale_h = target_out

    # Parse target aspect ratio as a fraction
    ratio_parts = target_ratio.split(":")
    if len(ratio_parts) == 2:
        target_ar = float(ratio_parts[0]) / float(ratio_parts[1])
    else:
        target_ar = 16.0 / 9.0

    source_ar = source_w / source_h if source_h > 0 else 1.0

    # Compute crop dimensions: largest box of target_ar that fits in source
    if source_ar > target_ar:
        # Source is wider — crop width
        crop_h = source_h
        crop_w = int(round(crop_h * target_ar))
    else:
        # Source is taller or equal — crop height
        crop_w = source_w
        crop_h = int(round(crop_w / target_ar))

    # Ensure crop fits within source
    crop_w = min(crop_w, source_w)
    crop_h = min(crop_h, source_h)

    # Determine crop origin
    if face_position is not None and face_position.get("pixel_space"):
        # Center crop on face
        face_cx = face_position.get("cx", source_w / 2.0)
        face_cy = face_position.get("cy", source_h / 2.0)
        x = int(round(face_cx - crop_w / 2.0))
        y = int(round(face_cy - crop_h / 2.0))
    else:
        # Center crop
        x = (source_w - crop_w) // 2
        y = (source_h - crop_h) // 2

    # Clamp to valid bounds
    x = max(0, min(x, source_w - crop_w))
    y = max(0, min(y, source_h - crop_h))

    ffmpeg_vf = f"crop={crop_w}:{crop_h}:{x}:{y},scale={scale_w}:{scale_h}"

    return {
        "x": x,
        "y": y,
        "w": crop_w,
        "h": crop_h,
        "scale_w": scale_w,
        "scale_h": scale_h,
        "ffmpeg_vf": ffmpeg_vf,
    }
