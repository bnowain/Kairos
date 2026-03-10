"""
Audio extraction service for Kairos.

Converts any video file to mono 16kHz WAV using FFmpeg.
Output: media/audio/{item_id}.wav

Preprocessing chain (speech-optimised):
  1. High-pass filter at 90 Hz — removes HVAC rumble and low-frequency noise
  2. EBU R128 loudnorm — normalises loudness (single-pass)
     Target: I=-16 LUFS, True Peak=-1.5 dBTP, LRA=11 LU
  3. Mono, 16 kHz, PCM s16le — Whisper's native format

FFmpeg command is logged at INFO level for reproducibility.
"""

import json
import logging
import subprocess
import wave
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ── Preprocessing constants ───────────────────────────────────────────────────
HPF_FREQ_HZ  = 90      # high-pass cutoff in Hz
LOUDNORM_I   = -16     # integrated loudness target (LUFS)
LOUDNORM_TP  = -1.5    # true peak ceiling (dBTP)
LOUDNORM_LRA = 11      # loudness range target (LU)


def extract_audio(
    video_path: str,
    output_path: str,
    on_progress: Optional[Callable[[float], None]] = None,
) -> float:
    """
    Extract preprocessed mono 16kHz PCM WAV from a video file.

    Args:
        video_path:  Absolute path to the source video file.
        output_path: Absolute path for the output WAV file.
        on_progress: Optional callback receiving progress fraction 0.0–1.0.

    Returns:
        Duration of the extracted audio in seconds.

    Raises:
        RuntimeError: If ffmpeg exits non-zero.
    """
    duration = _probe_duration(video_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    af = (
        f"highpass=f={HPF_FREQ_HZ},"
        f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
    )

    cmd = [
        "ffmpeg",
        "-y",                     # overwrite output
        "-i", video_path,
        "-vn",                    # drop video stream
        "-ac", "1",               # mono
        "-ar", "16000",           # 16 kHz
        "-af", af,                # preprocessing chain
        "-acodec", "pcm_s16le",   # 16-bit PCM
        output_path,
    ]

    logger.info("Audio extraction command: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg audio extraction failed (exit {result.returncode}):\n{result.stderr[-1000:]}"
        )

    # Use WAV duration as ground truth (more accurate than container metadata)
    wav_dur = _get_wav_duration(output_path)
    actual_duration = wav_dur if wav_dur > 0 else duration

    logger.info(
        "Audio extracted: %.1f min  filter=%s  output=%s",
        actual_duration / 60,
        af,
        output_path,
    )
    return actual_duration


def _probe_duration(video_path: str) -> float:
    """Return video/audio duration in seconds using ffprobe."""
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


def _get_wav_duration(wav_path: str) -> float:
    """Return duration of a WAV file in seconds using the wave stdlib module."""
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate   = wf.getframerate()
            return frames / float(rate) if rate > 0 else 0.0
    except Exception:
        return _probe_duration(wav_path)
