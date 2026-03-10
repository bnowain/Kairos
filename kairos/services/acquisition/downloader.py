"""
Core video download service for Kairos.

Download strategy (in order):
  1. Syllego/MMI — try first if installed (handles YouTube, TikTok, Twitter, Facebook, etc.)
  2. yt-dlp subprocess — fallback when MMI is not installed or fails

After download, the file is moved to the library-organised path:
  media_library/{platform}/{channel_slug}/{year}/{video_id}.{ext}

Returns a dict with:
  file_path    — relative path in media_library (POSIX string)
  metadata     — dict with title, channel, duration, published_at, platform_video_id, platform, description
  caption_path — relative path to downloaded subtitle file, or None
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from kairos.services.acquisition.library_organizer import (
    build_library_path,
    relative_path,
    slugify,
)

logger = logging.getLogger(__name__)

# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform(url: str) -> str:
    """Infer the platform name from a URL."""
    url_l = url.lower()
    if "youtube.com" in url_l or "youtu.be" in url_l:
        return "youtube"
    if "twitter.com" in url_l or "x.com" in url_l:
        return "twitter"
    if "tiktok.com" in url_l:
        return "tiktok"
    if "instagram.com" in url_l:
        return "instagram"
    if "facebook.com" in url_l or "fb.watch" in url_l:
        return "facebook"
    if "rumble.com" in url_l:
        return "rumble"
    if "vimeo.com" in url_l:
        return "vimeo"
    return "other"


def _parse_published_at(info: dict) -> Optional[str]:
    """Extract ISO 8601 date from yt-dlp info dict."""
    # yt-dlp returns 'upload_date' as YYYYMMDD
    upload_date = info.get("upload_date") or info.get("release_date")
    if upload_date and len(upload_date) == 8:
        try:
            dt = datetime.strptime(upload_date, "%Y%m%d")
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

    timestamp = info.get("timestamp") or info.get("release_timestamp")
    if timestamp:
        try:
            return datetime.utcfromtimestamp(int(timestamp)).strftime("%Y-%m-%dT%H:%M:%S")
        except (ValueError, OSError):
            pass

    return None


def _metadata_from_info(info: dict, platform: str) -> dict:
    """Build a normalised metadata dict from a yt-dlp info dict."""
    return {
        "title":            info.get("title"),
        "channel":          info.get("channel") or info.get("uploader") or info.get("creator"),
        "description":      info.get("description"),
        "published_at":     _parse_published_at(info),
        "duration":         info.get("duration"),  # seconds (float)
        "platform_video_id": info.get("id"),
        "platform":         platform,
        "thumbnail":        info.get("thumbnail"),
    }


# ── Syllego / MMI strategy ────────────────────────────────────────────────────

_MMI_AVAILABLE: Optional[bool] = None

def _check_mmi() -> bool:
    global _MMI_AVAILABLE
    if _MMI_AVAILABLE is None:
        try:
            import mmi  # noqa: F401
            _MMI_AVAILABLE = True
        except ImportError:
            _MMI_AVAILABLE = False
            logger.info("Syllego/MMI not installed — will use yt-dlp fallback")
    return _MMI_AVAILABLE


def _download_with_mmi(url: str, tmp_dir: Path) -> Optional[dict]:
    """
    Attempt to download using Syllego/MMI.

    Returns dict with keys: file, metadata_dict (partial — no full info dict from MMI).
    Returns None if MMI fails or is unavailable.
    """
    if not _check_mmi():
        return None

    try:
        import mmi
        os.environ.setdefault("MMI_CALLER", "Kairos")
        result = mmi.ingest(url, output_dir=tmp_dir)

        if not result.success or not result.filename:
            logger.warning(
                "MMI failed for %s: %s — %s. Falling back to yt-dlp.",
                url, result.error_code, result.error_message,
            )
            return None

        file_path = Path(result.filename)
        if not file_path.exists():
            logger.warning("MMI reported success but file missing: %s", result.filename)
            return None

        logger.info("MMI success via %s: %s", result.worker_name, file_path.name)
        return {"file": file_path, "metadata": result.metadata or {}}

    except Exception as exc:
        logger.warning("MMI raised an exception: %s — falling back to yt-dlp", exc)
        return None


# ── yt-dlp strategy ───────────────────────────────────────────────────────────

def _yt_dlp_info(url: str) -> Optional[dict]:
    """Fetch video metadata without downloading using yt-dlp --dump-json."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
        "--no-playlist",
        url,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=60
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout.splitlines()[0])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError, FileNotFoundError):
        return None


def _download_with_ytdlp(url: str, tmp_dir: Path, quality: str) -> dict:
    """
    Download using yt-dlp subprocess to a temp directory.

    Returns dict: {file: Path, info: dict, caption_file: Path | None}
    Raises RuntimeError on failure.
    """
    # First fetch info so we know the final filename and metadata
    info = _yt_dlp_info(url) or {}

    output_template = str(tmp_dir / "%(id)s.%(ext)s")
    subtitle_flags = [
        "--write-subs",
        "--write-auto-subs",
        "--sub-lang", "en",
        "--convert-subs", "srt",
    ]

    cmd = [
        "yt-dlp",
        "--format", quality,
        "--no-warnings",
        "--no-playlist",
        "--output", output_template,
        "--merge-output-format", "mp4",
    ] + subtitle_flags + [url]

    logger.info("yt-dlp command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=1800
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"yt-dlp timed out after 30 minutes for URL: {url}")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    if result.returncode != 0:
        stderr_tail = result.stderr[-1000:] if result.stderr else "(no stderr)"
        raise RuntimeError(
            f"yt-dlp failed (exit {result.returncode}) for {url}:\n{stderr_tail}"
        )

    # Find the downloaded file
    video_file: Optional[Path] = None
    caption_file: Optional[Path] = None
    video_exts = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".m4v"}

    for f in tmp_dir.iterdir():
        if f.suffix.lower() in video_exts:
            video_file = f
        elif f.suffix.lower() in {".srt", ".vtt"}:
            caption_file = f

    if not video_file:
        raise RuntimeError(f"yt-dlp succeeded but no video file found in {tmp_dir}")

    return {"file": video_file, "info": info, "caption_file": caption_file}


# ── Public API ────────────────────────────────────────────────────────────────

def download_video(
    url: str,
    media_library_root: Path,
    quality: str = "bestvideo[height<=1080]+bestaudio/best",
) -> dict:
    """
    Download a video from `url` and place it in the media library.

    Strategy:
      1. Try Syllego/MMI (if installed)
      2. Fall back to yt-dlp subprocess

    Returns:
        {
          "file_path":    str  (relative POSIX path in media_library_root),
          "metadata":     dict (title, channel, duration, published_at, platform_video_id, platform, description),
          "caption_path": str | None (relative POSIX path or None),
        }

    Raises:
        RuntimeError on unrecoverable download failure.
    """
    platform = detect_platform(url)

    with tempfile.TemporaryDirectory(prefix="kairos_dl_") as tmp_str:
        tmp_dir = Path(tmp_str)

        # ── Strategy 1: Syllego/MMI ───────────────────────────────────────────
        mmi_result = _download_with_mmi(url, tmp_dir)

        if mmi_result:
            tmp_file: Path = mmi_result["file"]
            # MMI doesn't give us a full info dict — fetch it separately
            info = _yt_dlp_info(url) or {}
            metadata = _metadata_from_info(info, platform)
            # Fill in any gaps from MMI's own metadata dict
            mmi_meta = mmi_result.get("metadata") or {}
            for k, v in mmi_meta.items():
                if v and not metadata.get(k):
                    metadata[k] = v
            caption_file = None

        else:
            # ── Strategy 2: yt-dlp ───────────────────────────────────────────
            ytdlp_result = _download_with_ytdlp(url, tmp_dir, quality)
            tmp_file    = ytdlp_result["file"]
            info        = ytdlp_result.get("info") or {}
            metadata    = _metadata_from_info(info, platform)
            caption_file = ytdlp_result.get("caption_file")

        # ── Determine library destination path ────────────────────────────────
        channel       = metadata.get("channel") or "unknown"
        video_id      = metadata.get("platform_video_id")
        published_str = metadata.get("published_at") or ""
        try:
            year = int(published_str[:4]) if published_str else datetime.utcnow().year
        except ValueError:
            year = datetime.utcnow().year

        ext = tmp_file.suffix.lstrip(".")  # e.g. "mp4"

        dest_path = build_library_path(
            platform=platform,
            channel=channel,
            year=year,
            video_id=video_id or tmp_file.stem,
            ext=ext,
            base=media_library_root,
        )

        # Move video into library (overwrites if already exists)
        shutil.move(str(tmp_file), str(dest_path))
        logger.info("Video placed in library: %s", dest_path)

        # Move caption file if present
        caption_rel: Optional[str] = None
        if caption_file and caption_file.exists():
            cap_dest = dest_path.with_suffix(caption_file.suffix)
            shutil.move(str(caption_file), str(cap_dest))
            caption_rel = relative_path(cap_dest, media_library_root)
            logger.info("Caption placed at: %s", cap_dest)

        return {
            "file_path":    relative_path(dest_path, media_library_root),
            "metadata":     metadata,
            "caption_path": caption_rel,
        }
