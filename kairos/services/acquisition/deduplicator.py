"""
Deduplication utilities for the Kairos media library.

Two dedup strategies:
  1. platform_video_id — fast: check if we already have this video ID per platform
  2. file_hash (SHA-256) — slow: used after download to catch re-uploaded content
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks for hashing large files


def is_duplicate(db, platform: str, platform_video_id: str | None) -> Optional[object]:
    """
    Check whether a video already exists in the library by platform + video ID.

    Returns the existing MediaItem ORM object if found, None otherwise.
    Always returns None when platform_video_id is None or empty (can't dedup).
    """
    if not platform_video_id:
        return None

    from kairos.models import MediaItem

    existing = (
        db.query(MediaItem)
        .filter(
            MediaItem.platform == platform,
            MediaItem.platform_video_id == platform_video_id,
        )
        .first()
    )
    return existing


def compute_file_hash(file_path: str | Path) -> str:
    """
    Compute SHA-256 hash of a file in chunks.

    Uses 8 MB chunks to handle large video files without loading them entirely
    into memory. Returns hex digest string.
    """
    sha256 = hashlib.sha256()
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Cannot hash missing file: {file_path}")

    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)

    digest = sha256.hexdigest()
    logger.debug("SHA-256 of %s: %s", path.name, digest)
    return digest


def find_by_hash(db, file_hash: str) -> Optional[object]:
    """
    Check whether a video with the given file hash already exists.

    Returns the existing MediaItem ORM object if found, None otherwise.
    Useful as a second-pass dedup check after download (catches re-uploads).
    """
    from kairos.models import MediaItem

    return (
        db.query(MediaItem)
        .filter(MediaItem.file_hash == file_hash)
        .first()
    )
