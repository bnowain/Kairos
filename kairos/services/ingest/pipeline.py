"""
Ingest pipeline for Kairos.

Orchestrates all post-download processing for a MediaItem:
  1. Extract audio WAV (FFmpeg — speech-optimised preprocessing)
  2. Generate thumbnail JPEG (FFmpeg)
  3. Compute SHA-256 file hash
  4. Return paths and hash to the caller (tasks.py updates the DB)

All paths returned are relative POSIX strings for DB storage:
  audio_path  — relative to project_root/media/audio/
  thumb_path  — relative to project_root/media/thumbs/
"""

import logging
import time
from pathlib import Path
from typing import Optional

from kairos.config import AUDIO_DIR, BASE_DIR, MEDIA_LIBRARY_ROOT, THUMBS_DIR
from kairos.services.acquisition.deduplicator import compute_file_hash
from kairos.services.ingest.audio_extractor import extract_audio
from kairos.services.ingest.thumbnailer import generate_thumbnail

logger = logging.getLogger(__name__)


def _to_absolute_video(file_path: str) -> Optional[Path]:
    """
    Resolve a stored file_path to an absolute Path.

    file_path may be:
      - A relative POSIX path (relative to MEDIA_LIBRARY_ROOT)
      - An absolute path
    """
    p = Path(file_path)
    if p.is_absolute():
        return p if p.exists() else None
    # Try relative to media_library_root
    candidate = MEDIA_LIBRARY_ROOT / p
    if candidate.exists():
        return candidate
    # Try relative to project root as fallback
    candidate2 = BASE_DIR / p
    if candidate2.exists():
        return candidate2
    return None


def run_ingest_pipeline(item_id: str, file_path: str) -> dict:
    """
    Run the full ingest pipeline for a downloaded video file.

    Args:
        item_id:   Kairos MediaItem UUID (used as filename stem for audio/thumbs).
        file_path: Stored relative (or absolute) path to the video file.

    Returns:
        {
          "audio_path":  str | None — relative POSIX path in media/audio/
          "thumb_path":  str | None — relative POSIX path in media/thumbs/
          "file_hash":   str        — SHA-256 hex digest of the video file
        }

    Raises:
        FileNotFoundError: If the video file cannot be located.
        RuntimeError:      If audio extraction fails (thumbnail failure is non-fatal).
    """
    t_start = time.perf_counter()

    # ── Resolve video file path ───────────────────────────────────────────────
    abs_video = _to_absolute_video(file_path)
    if abs_video is None:
        raise FileNotFoundError(
            f"Cannot locate video file for item {item_id}: {file_path}"
        )

    logger.info("Ingest pipeline starting for item %s — %s", item_id, abs_video.name)

    results: dict = {
        "audio_path": None,
        "thumb_path": None,
        "file_hash":  None,
    }

    # ── Step 1: Extract audio ─────────────────────────────────────────────────
    audio_out = AUDIO_DIR / f"{item_id}.wav"
    try:
        duration = extract_audio(
            video_path=str(abs_video),
            output_path=str(audio_out),
        )
        # Store path relative to media/ directory
        results["audio_path"] = f"audio/{item_id}.wav"
        logger.info("Audio extracted: %.1fs for item %s", duration, item_id)
    except Exception as exc:
        # Audio extraction failure is fatal — transcription cannot proceed without it
        raise RuntimeError(f"Audio extraction failed for item {item_id}: {exc}") from exc

    # ── Step 2: Generate thumbnail ────────────────────────────────────────────
    thumb_out = THUMBS_DIR / f"{item_id}.jpg"
    try:
        ok = generate_thumbnail(
            video_path=str(abs_video),
            output_path=str(thumb_out),
        )
        if ok:
            results["thumb_path"] = f"thumbs/{item_id}.jpg"
        else:
            logger.warning("Thumbnail generation failed for item %s (non-fatal)", item_id)
    except Exception as exc:
        # Thumbnail failure is non-fatal
        logger.warning("Thumbnail exception for item %s (non-fatal): %s", item_id, exc)

    # ── Step 3: Compute file hash ─────────────────────────────────────────────
    try:
        results["file_hash"] = compute_file_hash(abs_video)
        logger.info("File hash computed for item %s: %s...", item_id, results["file_hash"][:12])
    except Exception as exc:
        # Hash failure is non-fatal — dedup won't work but ingest can continue
        logger.warning("File hash failed for item %s (non-fatal): %s", item_id, exc)

    elapsed = time.perf_counter() - t_start
    logger.info("Ingest pipeline complete for item %s in %.1fs", item_id, elapsed)

    return results
