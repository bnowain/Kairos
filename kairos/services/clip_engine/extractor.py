"""
FFmpeg-based clip extraction with GPU (NVENC) and CPU fallback.

All subprocess calls use capture_output=True, text=True, encoding="utf-8", timeout=300.
NVENC failures are detected automatically and retried with libx264.
"""

import logging
import subprocess
from pathlib import Path

from kairos.config import BASE_DIR, VIDEO_ENCODER

logger = logging.getLogger(__name__)


def _run_ffmpeg(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run an FFmpeg command. Returns the CompletedProcess result."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )


def _ms_to_sec(ms: int) -> float:
    return ms / 1000.0


def _build_nvenc_cmd(
    source: str,
    output: str,
    start_sec: float,
    end_sec: float,
) -> list[str]:
    return [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-to", f"{end_sec:.3f}",
        "-i", source,
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-cq", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output,
    ]


def _build_cpu_cmd(
    source: str,
    output: str,
    start_sec: float,
    end_sec: float,
) -> list[str]:
    return [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-to", f"{end_sec:.3f}",
        "-i", source,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output,
    ]


def _nvenc_failed(result: subprocess.CompletedProcess) -> bool:
    """Return True if FFmpeg stderr indicates an NVENC-specific failure."""
    if result.returncode == 0:
        return False
    stderr_lower = result.stderr.lower()
    nvenc_errors = [
        "nvenc",
        "nvcuda",
        "cuda",
        "no capable devices found",
        "no nvidia",
        "gpu",
        "encoder initialization failed",
        "nvencodeapicreateinstance",
    ]
    return any(token in stderr_lower for token in nvenc_errors)


def _get_clip_duration_ms(clip_path: str) -> int:
    """Use ffprobe to get the actual duration of a clip in milliseconds."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                clip_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()) * 1000)
    except Exception as exc:
        logger.warning("_get_clip_duration_ms: ffprobe failed for %s — %s", clip_path, exc)
    return 0


def extract_clip(
    source_path: str,
    output_path: str,
    start_ms: int,
    end_ms: int,
    encoder: str = None,
    pad_start_ms: int = 0,
    pad_end_ms: int = 0,
) -> dict:
    """
    Extract a clip from source_path between start_ms and end_ms.

    Applies optional padding (pad_start_ms before, pad_end_ms after).
    Uses NVENC by default; auto-retries with libx264 if NVENC fails.

    Returns:
        {
            "success": bool,
            "output_path": str,
            "duration_ms": int,
            "error": str | None,
        }
    """
    effective_encoder = encoder or VIDEO_ENCODER

    # Apply padding (clamp to 0 floor)
    padded_start_ms = max(0, start_ms - pad_start_ms)
    padded_end_ms = end_ms + pad_end_ms

    start_sec = _ms_to_sec(padded_start_ms)
    end_sec   = _ms_to_sec(padded_end_ms)

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Choose command based on encoder
    if effective_encoder == "h264_nvenc":
        cmd = _build_nvenc_cmd(source_path, output_path, start_sec, end_sec)
    else:
        cmd = _build_cpu_cmd(source_path, output_path, start_sec, end_sec)

    logger.info(
        "extract_clip: encoder=%s  start=%.3fs  end=%.3fs  out=%s",
        effective_encoder, start_sec, end_sec, output_path,
    )

    result = _run_ffmpeg(cmd)

    # NVENC failure — auto-retry with libx264
    if effective_encoder == "h264_nvenc" and _nvenc_failed(result):
        logger.warning(
            "extract_clip: NVENC failed (returncode=%d) — falling back to libx264.\n"
            "FFmpeg stderr: %s",
            result.returncode,
            result.stderr[-2000:],
        )
        cmd = _build_cpu_cmd(source_path, output_path, start_sec, end_sec)
        result = _run_ffmpeg(cmd)

    if result.returncode != 0:
        logger.error(
            "extract_clip: FFmpeg failed (returncode=%d).\nFFmpeg stderr:\n%s",
            result.returncode,
            result.stderr[-3000:],
        )
        return {
            "success": False,
            "output_path": output_path,
            "duration_ms": 0,
            "error": f"FFmpeg exited {result.returncode}: {result.stderr[-500:]}",
        }

    duration_ms = _get_clip_duration_ms(output_path)
    logger.info(
        "extract_clip: success — duration=%dms  path=%s",
        duration_ms, output_path,
    )
    return {
        "success": True,
        "output_path": output_path,
        "duration_ms": duration_ms,
        "error": None,
    }


def generate_clip_thumbnail(
    clip_path: str,
    thumb_path: str,
    offset_pct: float = 0.3,
) -> bool:
    """
    Extract a single JPEG frame from clip_path at offset_pct of its duration.
    Scales to 640x360. Returns True on success.
    """
    duration_ms = _get_clip_duration_ms(clip_path)
    if duration_ms <= 0:
        logger.warning(
            "generate_clip_thumbnail: cannot determine duration for %s — using 0s offset",
            clip_path,
        )
        offset_sec = 0.0
    else:
        offset_sec = _ms_to_sec(int(duration_ms * offset_pct))

    Path(thumb_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{offset_sec:.3f}",
        "-i", clip_path,
        "-vframes", "1",
        "-vf", "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "3",
        thumb_path,
    ]

    result = _run_ffmpeg(cmd)

    if result.returncode != 0:
        logger.error(
            "generate_clip_thumbnail: FFmpeg failed (returncode=%d).\nstderr:\n%s",
            result.returncode,
            result.stderr[-2000:],
        )
        return False

    logger.info("generate_clip_thumbnail: saved thumbnail %s", thumb_path)
    return True
