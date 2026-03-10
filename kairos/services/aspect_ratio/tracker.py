"""
Smooth face tracking over clip duration for dynamic reframing.
"""

from __future__ import annotations

import logging
from collections import deque

logger = logging.getLogger(__name__)


def compute_tracking_crop(
    clip_path: str,
    target_ratio: str = "9:16",
    smoothing_window: int = 15,
) -> list[dict]:
    """
    For each sampled frame, detect dominant face and compute crop box.
    Apply temporal smoothing (rolling average of cx/cy) to prevent jitter.

    Returns list of keyframe crop instructions:
    [{"timestamp_ms": float, "crop": {"x": int, "y": int, "w": int, "h": int}}]

    This output can be used to generate an FFmpeg crop filter with
    send_cmd/filter expressions for dynamic reframing (advanced).
    For simpler use: just use the median crop across all frames (get_median_crop).
    """
    from kairos.services.aspect_ratio.detector import detect_faces_in_clip
    from kairos.services.aspect_ratio.reframer import compute_crop_box, get_source_dimensions

    source_w, source_h = get_source_dimensions(clip_path)

    detections = detect_faces_in_clip(clip_path, sample_rate_fps=2.0, max_frames=60)

    if not detections:
        logger.info(
            "compute_tracking_crop: no detections from %s — using center crop",
            clip_path,
        )
        crop = compute_crop_box(source_w, source_h, target_ratio, face_position=None)
        return [{"timestamp_ms": 0.0, "crop": {"x": crop["x"], "y": crop["y"], "w": crop["w"], "h": crop["h"]}}]

    # Rolling averages for cx and cy
    cx_window: deque[float] = deque(maxlen=smoothing_window)
    cy_window: deque[float] = deque(maxlen=smoothing_window)

    tracking_crops: list[dict] = []

    for frame_det in detections:
        faces = frame_det.get("faces", [])
        timestamp_ms = frame_det.get("timestamp_ms", 0.0)

        if faces:
            best_face = max(faces, key=lambda f: f.get("confidence", 0.0))
            bbox = best_face["bbox"]
            face_cx = bbox[0] + bbox[2] / 2.0
            face_cy = bbox[1] + bbox[3] / 2.0
        else:
            # No face in this frame — use last known or center
            face_cx = cx_window[-1] if cx_window else source_w / 2.0
            face_cy = cy_window[-1] if cy_window else source_h / 2.0

        cx_window.append(face_cx)
        cy_window.append(face_cy)

        # Smoothed position
        smooth_cx = sum(cx_window) / len(cx_window)
        smooth_cy = sum(cy_window) / len(cy_window)

        face_pos = {
            "cx": smooth_cx,
            "cy": smooth_cy,
            "pixel_space": True,
        }
        crop = compute_crop_box(source_w, source_h, target_ratio, face_position=face_pos)

        tracking_crops.append({
            "timestamp_ms": timestamp_ms,
            "crop": {
                "x": crop["x"],
                "y": crop["y"],
                "w": crop["w"],
                "h": crop["h"],
            },
        })

    logger.debug(
        "compute_tracking_crop: %d keyframes from %s",
        len(tracking_crops), clip_path,
    )
    return tracking_crops


def get_median_crop(tracking_crops: list[dict]) -> dict:
    """
    Compute the median crop box from a list of tracking crops.
    Useful as a static crop when dynamic reframing is not needed.
    Returns a single crop dict {"x", "y", "w", "h"}.
    """
    if not tracking_crops:
        return {"x": 0, "y": 0, "w": 1920, "h": 1080}

    def _median(vals: list[int]) -> int:
        s = sorted(vals)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) // 2

    xs = [tc["crop"]["x"] for tc in tracking_crops]
    ys = [tc["crop"]["y"] for tc in tracking_crops]
    ws = [tc["crop"]["w"] for tc in tracking_crops]
    hs = [tc["crop"]["h"] for tc in tracking_crops]

    return {
        "x": _median(xs),
        "y": _median(ys),
        "w": _median(ws),
        "h": _median(hs),
    }
