"""
Face detection on video frames using MediaPipe.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_faces_in_clip(
    clip_path: str,
    sample_rate_fps: float = 2.0,
    max_frames: int = 60,
) -> list[dict]:
    """
    Sample frames from clip, detect faces in each.
    Returns list of detection results:
    [{"frame_idx": int, "timestamp_ms": float,
      "faces": [{"bbox": [x, y, w, h], "confidence": float}]}]

    Uses MediaPipe FaceDetector (short-range model).
    Graceful fallback: if mediapipe not installed, return [] with a warning log.
    """
    # Attempt to import cv2 and mediapipe; fall back gracefully
    try:
        import cv2
    except ImportError:
        logger.warning(
            "detect_faces_in_clip: opencv-python not installed — face detection unavailable. "
            "Install with: pip install opencv-python"
        )
        return []

    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_detection
    except ImportError:
        logger.warning(
            "detect_faces_in_clip: mediapipe not installed — face detection unavailable. "
            "Install with: pip install mediapipe"
        )
        return []

    results: list[dict] = []

    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        logger.error("detect_faces_in_clip: cannot open video %s", clip_path)
        return []

    try:
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(round(video_fps / sample_rate_fps)))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_to_sample = min(max_frames, max(1, total_frames // frame_interval))

        with mp_face.FaceDetection(
            model_selection=0,    # 0 = short-range (within 2m), 1 = full-range
            min_detection_confidence=0.5,
        ) as face_detector:
            frame_idx = 0
            sampled = 0

            while sampled < frames_to_sample:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                # Convert BGR → RGB for mediapipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                detection_result = face_detector.process(rgb_frame)

                faces: list[dict] = []
                if detection_result.detections:
                    h_px, w_px = frame.shape[:2]
                    for det in detection_result.detections:
                        bbox = det.location_data.relative_bounding_box
                        # Convert normalized → pixel coords
                        x = int(bbox.xmin * w_px)
                        y = int(bbox.ymin * h_px)
                        w = int(bbox.width * w_px)
                        h = int(bbox.height * h_px)
                        # Clamp to frame bounds
                        x = max(0, x)
                        y = max(0, y)
                        w = min(w, w_px - x)
                        h = min(h, h_px - y)
                        faces.append({
                            "bbox": [x, y, w, h],
                            "confidence": float(det.score[0]) if det.score else 0.0,
                        })

                results.append({
                    "frame_idx": frame_idx,
                    "timestamp_ms": float(timestamp_ms),
                    "faces": faces,
                })

                frame_idx += frame_interval
                sampled += 1

    except Exception as exc:
        logger.error("detect_faces_in_clip: detection error — %s", exc)
    finally:
        cap.release()

    logger.debug(
        "detect_faces_in_clip: sampled %d frames from %s, found faces in %d",
        len(results), clip_path, sum(1 for r in results if r["faces"]),
    )
    return results


def get_dominant_face_position(detections: list[dict]) -> dict | None:
    """
    From a list of frame detections, compute the average bounding box
    of the most consistently detected face.
    Returns {"cx": float, "cy": float, "w": float, "h": float} (normalized 0-1)
    or None if no faces detected.

    Strategy: collect all face bboxes, compute median center position and average size.
    """
    all_bboxes: list[list[int]] = []

    for frame_det in detections:
        faces = frame_det.get("faces", [])
        if not faces:
            continue
        # Use the most confident face in this frame
        best = max(faces, key=lambda f: f.get("confidence", 0.0))
        all_bboxes.append(best["bbox"])

    if not all_bboxes:
        return None

    # We need the source frame dimensions to normalize, but they're not stored
    # in detections. We compute normalized values assuming bbox is already in pixels.
    # The caller must supply reference frame size for true normalization.
    # Here we return the median pixel bbox, and the caller can normalize using source dims.
    # For simplicity, return pixel-space values tagged as unnormalized.
    # NOTE: reframer.compute_crop_box handles the pixel→crop math directly.

    xs = [b[0] + b[2] / 2.0 for b in all_bboxes]  # center x
    ys = [b[1] + b[3] / 2.0 for b in all_bboxes]  # center y
    ws = [b[2] for b in all_bboxes]
    hs = [b[3] for b in all_bboxes]

    def median(vals: list[float]) -> float:
        s = sorted(vals)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0

    return {
        "cx": median(xs),
        "cy": median(ys),
        "w": median(ws),
        "h": median(hs),
        "pixel_space": True,   # indicates values are in pixels, not normalized 0-1
    }
