"""
Audio event detection using librosa.
Identifies timestamps with high energy bursts (laughter, applause, cheering).

Uses RMS energy frame analysis to find audience reaction moments.
No ML model required — pure signal processing.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Minimum duration (seconds) for a detected event to be kept
MIN_EVENT_DURATION = 0.3
# Gap (seconds) between frames to merge into one event
MERGE_GAP = 0.5
# Default sample rate for loading audio
SAMPLE_RATE = 16000


def detect_reactions(audio_path: str, hop_length: int = 512) -> list[dict]:
    """
    Returns list of reaction events detected from audio energy bursts.

    Each event:
        {"start": float, "end": float, "type": "reaction", "intensity": float}

    Method:
    1. Load audio with librosa (sr=16000, mono)
    2. Compute RMS energy frame-by-frame
    3. Find frames where energy > mean + 1.5 * std (outlier burst)
    4. Merge adjacent frames within MERGE_GAP seconds into events
    5. Filter events shorter than MIN_EVENT_DURATION

    Returns empty list on any error (missing file, librosa unavailable, etc.)
    """
    try:
        import librosa
    except ImportError:
        logger.warning("audio_events: librosa not installed — skipping audio event detection")
        return []

    try:
        y, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    except Exception as exc:
        logger.warning("audio_events: failed to load audio from %s (%s)", audio_path, exc)
        return []

    # Compute RMS energy per frame
    try:
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]  # shape: (n_frames,)
    except Exception as exc:
        logger.warning("audio_events: RMS computation failed (%s)", exc)
        return []

    if len(rms) == 0:
        return []

    # Frame timestamps
    frame_times = librosa.frames_to_time(
        np.arange(len(rms)), sr=sr, hop_length=hop_length
    )

    # Threshold: mean + 1.5 * std
    mean_rms = float(np.mean(rms))
    std_rms = float(np.std(rms))
    threshold = mean_rms + 1.5 * std_rms

    # Find high-energy frames
    high_frames = np.where(rms > threshold)[0]

    if len(high_frames) == 0:
        return []

    # Merge adjacent high-energy frames into events
    events: list[dict] = []
    event_start_idx = high_frames[0]
    prev_idx = high_frames[0]

    for idx in high_frames[1:]:
        t_gap = frame_times[idx] - frame_times[prev_idx]
        if t_gap <= MERGE_GAP:
            # Continue current event
            prev_idx = idx
        else:
            # Close current event, start new one
            event_start = float(frame_times[event_start_idx])
            event_end = float(frame_times[prev_idx])
            duration = event_end - event_start

            if duration >= MIN_EVENT_DURATION:
                # Intensity = peak RMS within event normalised to 0-1
                event_frames = np.arange(event_start_idx, prev_idx + 1)
                peak_rms = float(np.max(rms[event_frames]))
                # Normalise: peak / (mean + 3 * std), capped at 1.0
                intensity = min(1.0, peak_rms / max(mean_rms + 3 * std_rms, 1e-9))
                events.append({
                    "start":     event_start,
                    "end":       event_end,
                    "type":      "reaction",
                    "intensity": round(intensity, 4),
                })

            event_start_idx = idx
            prev_idx = idx

    # Close the last event
    event_start = float(frame_times[event_start_idx])
    event_end = float(frame_times[prev_idx])
    duration = event_end - event_start
    if duration >= MIN_EVENT_DURATION:
        event_frames = np.arange(event_start_idx, prev_idx + 1)
        peak_rms = float(np.max(rms[event_frames]))
        intensity = min(1.0, peak_rms / max(mean_rms + 3 * std_rms, 1e-9))
        events.append({
            "start":     event_start,
            "end":       event_end,
            "type":      "reaction",
            "intensity": round(intensity, 4),
        })

    logger.info(
        "audio_events: detected %d reaction events in %s",
        len(events), audio_path,
    )
    return events


def score_segments_by_reactions(
    segments: list[dict],
    reaction_events: list[dict],
) -> list[dict]:
    """
    For each segment, compute audience_reaction_score (0.0-1.0) based on
    how much reaction event time overlaps with the segment's time range.
    Adds 'audience_reaction_score' to each segment dict (modifies in place).

    Overlap score = total overlap seconds / segment duration seconds,
    weighted by event intensity, capped at 1.0.
    """
    if not reaction_events:
        for seg in segments:
            seg["audience_reaction_score"] = 0.0
        return segments

    for seg in segments:
        start_s = seg.get("start_ms", 0) / 1000.0
        end_s = seg.get("end_ms", 0) / 1000.0
        duration_s = max(end_s - start_s, 0.001)  # avoid divide-by-zero

        weighted_overlap = 0.0
        for event in reaction_events:
            # Compute overlap
            overlap_start = max(start_s, event["start"])
            overlap_end = min(end_s, event["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > 0:
                weighted_overlap += overlap * event.get("intensity", 1.0)

        score = min(1.0, weighted_overlap / duration_s)
        seg["audience_reaction_score"] = round(score, 4)

    return segments
