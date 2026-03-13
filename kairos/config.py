"""
Central configuration for Kairos.
All paths, environment variables, and hardware detection live here.
Directories are created at import time.
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Load .env if present ──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Base paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()

# Media library: organized source video storage (platform/channel/year/)
_media_root_env = os.environ.get("KAIROS_MEDIA_ROOT", "")
MEDIA_LIBRARY_ROOT = Path(_media_root_env).resolve() if _media_root_env else BASE_DIR / "media_library"

# Operational media dirs (audio, thumbs, clips, etc.)
MEDIA_DIR     = BASE_DIR / "media"
CLIPS_DIR     = MEDIA_DIR / "clips"
RENDERS_DIR   = MEDIA_DIR / "renders"
PREVIEWS_DIR  = MEDIA_DIR / "previews"
AUDIO_DIR     = MEDIA_DIR / "audio"
THUMBS_DIR    = MEDIA_DIR / "thumbs"

# Database paths
DATABASE_PATH   = BASE_DIR / "database" / "kairos.db"
DATABASE_URL    = f"sqlite:///{DATABASE_PATH}"
HUEY_GPU_DB     = BASE_DIR / "database" / "huey_gpu.db"
HUEY_LIGHT_DB   = BASE_DIR / "database" / "huey_light.db"

# Config and template dirs
CONFIG_DIR    = BASE_DIR / "config"
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR      = BASE_DIR / "logs"

# ── Network settings ──────────────────────────────────────────────────────────
KAIROS_PORT = int(os.environ.get("KAIROS_PORT", "8400"))

# ── LLM / Whisper settings (Phase 2+) ────────────────────────────────────────
LLM_PROVIDER    = os.environ.get("LLM_PROVIDER", "ollama")        # ollama | mission_control
OLLAMA_HOST     = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3")
MC_HOST         = os.environ.get("MC_HOST", "http://localhost:8860")
MC_MODEL_ID     = os.environ.get("MC_MODEL_ID", "")               # e.g. anthropic/claude-sonnet-4-6, leave empty for MC default routing
HF_TOKEN        = os.environ.get("HF_TOKEN", "")
WHISPER_MODEL   = os.environ.get("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE  = os.environ.get("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "float16")
PYANNOTE_MODEL  = os.environ.get("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")

# ── Hardware detection ────────────────────────────────────────────────────────

def _detect_cuda() -> bool:
    """Return True if a CUDA-capable GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        pass
    # Fallback: check nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, encoding="utf-8",
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except FileNotFoundError:
        return False


def _detect_nvenc() -> bool:
    """Return True if FFmpeg has h264_nvenc encoder available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, encoding="utf-8",
        )
        return "h264_nvenc" in result.stdout
    except FileNotFoundError:
        return False


CUDA_AVAILABLE  = _detect_cuda()
NVENC_AVAILABLE = _detect_nvenc()
VIDEO_ENCODER   = "h264_nvenc" if NVENC_AVAILABLE else "libx264"

if CUDA_AVAILABLE:
    logger.info("CUDA GPU detected — GPU tasks will use cuda device")
else:
    logger.info("No CUDA GPU detected — will use CPU for heavy tasks")

if NVENC_AVAILABLE:
    logger.info("h264_nvenc available — renders will use hardware encoding")
else:
    logger.info("h264_nvenc not available — renders will use libx264 (software)")

# ── Default download quality (yt-dlp format string) ──────────────────────────
DEFAULT_DOWNLOAD_QUALITY = "bestvideo[height<=1080]+bestaudio/best"

# ── Ensure all required directories exist at import time ─────────────────────
for _d in [
    DATABASE_PATH.parent,
    MEDIA_LIBRARY_ROOT,
    CLIPS_DIR,
    RENDERS_DIR,
    PREVIEWS_DIR,
    AUDIO_DIR,
    THUMBS_DIR,
    CONFIG_DIR,
    TEMPLATES_DIR,
    LOGS_DIR,
]:
    _d.mkdir(parents=True, exist_ok=True)
