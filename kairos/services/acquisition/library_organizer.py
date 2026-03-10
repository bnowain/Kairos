"""
Library organizer — builds structured paths for downloaded media.

Library layout:
  media_library/{platform}/{channel_slug}/{year}/{video_id}.{ext}

Example:
  media_library/youtube/tedtalks/2024/dQw4w9WgXcQ.mp4
"""

import re
from datetime import datetime
from pathlib import Path


def slugify(text: str) -> str:
    """
    Convert a string to a safe directory name.
    Lowercases, replaces spaces with underscores, removes all non-alphanumeric
    characters except underscores and hyphens, and trims leading/trailing underscores.
    """
    text = text.lower().strip()
    text = re.sub(r"[\s]+", "_", text)                  # spaces → underscore
    text = re.sub(r"[^\w\-]", "", text)                 # remove special chars (keep _ and -)
    text = re.sub(r"_{2,}", "_", text)                  # collapse multiple underscores
    text = text.strip("_-")
    return text or "unknown"


def build_library_path(
    platform: str,
    channel: str | None,
    year: int | None,
    video_id: str | None,
    ext: str,
    base: Path,
) -> Path:
    """
    Build the full absolute path for a downloaded video file.

    Args:
        platform:  e.g. "youtube", "twitter", "tiktok"
        channel:   Channel or user name (will be slugified)
        year:      Publication year (falls back to current year)
        video_id:  Platform-specific video ID used as filename
        ext:       File extension without dot (e.g. "mp4", "webm")
        base:      MEDIA_LIBRARY_ROOT

    Returns:
        Absolute Path object. Parent directories are created.
    """
    platform_slug = slugify(platform or "unknown")
    channel_slug  = slugify(channel or "unknown")
    year_str      = str(year or datetime.utcnow().year)
    filename      = slugify(video_id or "video") + f".{ext.lstrip('.')}"

    target = base / platform_slug / channel_slug / year_str / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def relative_path(absolute: Path, base: Path) -> str:
    """Return path relative to base as a POSIX string (for DB storage)."""
    try:
        return absolute.relative_to(base).as_posix()
    except ValueError:
        # absolute is not under base — store full path
        return absolute.as_posix()
