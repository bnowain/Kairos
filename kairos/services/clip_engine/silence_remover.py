"""
Silence removal using FFmpeg's silencedetect filter.

Detects silent segments and re-splices the clip without them using the
FFmpeg concat demuxer. Short silences (below min_silence_duration) are kept
to preserve natural speech rhythm.
"""

import logging
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex patterns for FFmpeg silencedetect output
_RE_SILENCE_START = re.compile(r"silence_start:\s*([\d.]+)")
_RE_SILENCE_END   = re.compile(r"silence_end:\s*([\d.]+)")
_RE_SILENCE_DUR   = re.compile(r"silence_duration:\s*([\d.]+)")


def _run_ffmpeg(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )


def _get_duration_sec(path: str) -> float:
    """Return duration of media file in seconds via ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as exc:
        logger.warning("_get_duration_sec: ffprobe failed for %s — %s", path, exc)
    return 0.0


def detect_silence(
    clip_path: str,
    noise_threshold: float = -35.0,
    min_silence_duration: float = 0.5,
) -> list[dict]:
    """
    Run FFmpeg silencedetect on clip_path.

    Returns a list of dicts:
        [{"start": float, "end": float, "duration": float}, ...]

    All times are in seconds.
    """
    cmd = [
        "ffmpeg",
        "-i", clip_path,
        "-af", f"silencedetect=noise={noise_threshold}dB:duration={min_silence_duration}",
        "-f", "null",
        "-",
    ]

    result = _run_ffmpeg(cmd)

    # silencedetect writes to stderr regardless of return code
    stderr = result.stderr

    silences: list[dict] = []
    current_start: float | None = None

    for line in stderr.splitlines():
        m_start = _RE_SILENCE_START.search(line)
        m_end   = _RE_SILENCE_END.search(line)
        m_dur   = _RE_SILENCE_DUR.search(line)

        if m_start:
            current_start = float(m_start.group(1))

        if m_end and m_dur and current_start is not None:
            end_sec = float(m_end.group(1))
            dur_sec = float(m_dur.group(1))
            silences.append({
                "start":    current_start,
                "end":      end_sec,
                "duration": dur_sec,
            })
            current_start = None

    logger.debug(
        "detect_silence: found %d silent segment(s) in %s",
        len(silences), clip_path,
    )
    return silences


def remove_silence(
    input_path: str,
    output_path: str,
    noise_threshold: float = -35.0,
    min_silence_duration: float = 0.5,
    keep_padding_ms: int = 150,
) -> dict:
    """
    Remove long silence from input_path and save result to output_path.

    Steps:
      1. detect_silence() to find silent regions
      2. If no silence found, or total silence < 10% of clip → copy unchanged
      3. Build FFmpeg concat demuxer file listing non-silent segments
      4. Run FFmpeg concat to produce output

    Returns:
        {
            "success": bool,
            "input_duration_ms": int,
            "output_duration_ms": int,
            "silence_removed_ms": int,
            "error": str | None,
        }
    """
    keep_padding_sec = keep_padding_ms / 1000.0

    input_duration_sec = _get_duration_sec(input_path)
    input_duration_ms  = int(input_duration_sec * 1000)

    if input_duration_sec <= 0:
        return {
            "success": False,
            "input_duration_ms": input_duration_ms,
            "output_duration_ms": 0,
            "silence_removed_ms": 0,
            "error": f"Could not determine duration of {input_path}",
        }

    silences = detect_silence(
        input_path,
        noise_threshold=noise_threshold,
        min_silence_duration=min_silence_duration,
    )

    total_silence_sec = sum(s["duration"] for s in silences)

    # Skip silence removal if silence is trivial (< 10% of clip)
    if not silences or total_silence_sec < input_duration_sec * 0.10:
        logger.info(
            "remove_silence: silence total (%.1fs) < 10%% of clip (%.1fs) — copying unchanged",
            total_silence_sec, input_duration_sec,
        )
        # Copy file using FFmpeg (lossless stream copy)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        copy_cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c", "copy",
            output_path,
        ]
        result = subprocess.run(
            copy_cmd, capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "input_duration_ms": input_duration_ms,
                "output_duration_ms": 0,
                "silence_removed_ms": 0,
                "error": f"FFmpeg copy failed: {result.stderr[-500:]}",
            }
        output_duration_ms = int(_get_duration_sec(output_path) * 1000)
        return {
            "success": True,
            "input_duration_ms": input_duration_ms,
            "output_duration_ms": output_duration_ms,
            "silence_removed_ms": 0,
            "error": None,
        }

    # Build the list of non-silent segments to keep
    # Each silent region defines a gap; we keep everything outside those gaps
    # (with keep_padding on each side of cuts)
    kept_segments: list[tuple[float, float]] = []  # (start_sec, end_sec)

    cursor = 0.0
    for silence in sorted(silences, key=lambda s: s["start"]):
        cut_start = silence["start"] + keep_padding_sec
        cut_end   = silence["end"]   - keep_padding_sec

        # If the silence is too short after padding, skip
        if cut_end <= cut_start:
            continue

        # Keep segment from cursor to cut_start (end of speech before silence)
        if cut_start > cursor:
            kept_segments.append((cursor, cut_start))

        cursor = cut_end

    # Keep everything after the last silence
    if cursor < input_duration_sec:
        kept_segments.append((cursor, input_duration_sec))

    if not kept_segments:
        logger.warning("remove_silence: no kept segments — copying input unchanged")
        kept_segments = [(0.0, input_duration_sec)]

    logger.info(
        "remove_silence: will concat %d kept segment(s) (removing ~%.1fs of silence)",
        len(kept_segments), total_silence_sec,
    )

    # Write concat demuxer file to a temp file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as fh:
            demux_path = fh.name
            for seg_start, seg_end in kept_segments:
                duration = seg_end - seg_start
                if duration <= 0:
                    continue
                fh.write(f"file '{input_path}'\n")
                fh.write(f"inpoint {seg_start:.6f}\n")
                fh.write(f"outpoint {seg_end:.6f}\n")

        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", demux_path,
            "-c", "copy",
            output_path,
        ]

        result = subprocess.run(
            concat_cmd, capture_output=True, text=True, encoding="utf-8", timeout=300,
        )

        if result.returncode != 0:
            logger.error(
                "remove_silence: FFmpeg concat failed (returncode=%d).\nstderr:\n%s",
                result.returncode, result.stderr[-2000:],
            )
            return {
                "success": False,
                "input_duration_ms": input_duration_ms,
                "output_duration_ms": 0,
                "silence_removed_ms": int(total_silence_sec * 1000),
                "error": f"FFmpeg concat exited {result.returncode}: {result.stderr[-500:]}",
            }

    finally:
        try:
            Path(demux_path).unlink(missing_ok=True)
        except Exception:
            pass

    output_duration_ms  = int(_get_duration_sec(output_path) * 1000)
    silence_removed_ms  = max(0, input_duration_ms - output_duration_ms)

    logger.info(
        "remove_silence: done — input=%dms  output=%dms  removed=%dms",
        input_duration_ms, output_duration_ms, silence_removed_ms,
    )

    return {
        "success": True,
        "input_duration_ms": input_duration_ms,
        "output_duration_ms": output_duration_ms,
        "silence_removed_ms": silence_removed_ms,
        "error": None,
    }
