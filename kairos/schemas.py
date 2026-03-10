"""
Pydantic v2 request/response schemas for Kairos API endpoints.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Health / System ───────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    version: str
    cuda_available: bool
    nvenc_available: bool


class ConfigOut(BaseModel):
    port: int
    media_library_root: str
    database_path: str
    ollama_host: str
    whisper_model: str
    whisper_device: str
    whisper_compute: str
    video_encoder: str
    cuda_available: bool
    nvenc_available: bool


class JobStatusOut(BaseModel):
    job_type: str          # "render" | "transcription"
    job_id: str
    item_id: Optional[str] = None
    timeline_id: Optional[str] = None
    job_status: str
    error_msg: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


# ── Acquisition Sources ───────────────────────────────────────────────────────

class AcquisitionSourceCreate(BaseModel):
    source_type: str = Field(
        ...,
        description="youtube_channel | youtube_playlist | tiktok_user | twitter_user | rss_podcast | local_folder",
    )
    source_url: str
    source_name: Optional[str] = None
    platform: str = Field(
        ...,
        description="youtube | twitter | tiktok | instagram | rss | local",
    )
    schedule_cron: Optional[str] = None
    enabled: int = 1
    download_quality: str = "bestvideo[height<=1080]+bestaudio/best"


class AcquisitionSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    schedule_cron: Optional[str] = None
    enabled: Optional[int] = None
    download_quality: Optional[str] = None


class AcquisitionSourceOut(BaseModel):
    source_id: str
    source_type: str
    source_url: str
    source_name: Optional[str]
    platform: str
    schedule_cron: Optional[str]
    last_polled_at: Optional[str]
    enabled: int
    download_quality: str
    created_at: str

    model_config = {"from_attributes": True}


# ── Download ──────────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str = Field(..., description="URL of the video to download")
    source_id: Optional[str] = Field(
        None,
        description="Optional acquisition_sources.source_id to associate this download with",
    )
    download_quality: Optional[str] = Field(
        None,
        description="yt-dlp format string — overrides source default if provided",
    )


class DownloadResponse(BaseModel):
    item_id: str
    status: str
    message: str


# ── Library / Media Items ─────────────────────────────────────────────────────

class MediaItemOut(BaseModel):
    item_id: str
    source_id: Optional[str]
    platform: str
    platform_video_id: Optional[str]
    item_title: Optional[str]
    item_channel: Optional[str]
    item_description: Optional[str]
    published_at: Optional[str]
    duration_seconds: Optional[float]
    original_url: Optional[str]
    file_path: Optional[str]
    audio_path: Optional[str]
    thumb_path: Optional[str]
    file_hash: Optional[str]
    item_status: str
    error_msg: Optional[str]
    has_captions: int
    caption_source: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MediaItemDetail(MediaItemOut):
    """Extended detail view — includes transcription job status."""
    transcription_job_status: Optional[str] = None
    transcription_job_id: Optional[str] = None
    segment_count: int = 0
    clip_count: int = 0


# ── Transcription ─────────────────────────────────────────────────────────────

class TranscriptionJobOut(BaseModel):
    job_id:        str
    item_id:       str
    whisper_model: Optional[str] = None
    language:      Optional[str] = None
    job_status:    str
    error_msg:     Optional[str] = None
    started_at:    Optional[str] = None
    completed_at:  Optional[str] = None
    created_at:    str
    segment_count: int = 0

    model_config = {"from_attributes": True}


class TranscriptionSegmentOut(BaseModel):
    segment_id:      str
    item_id:         str
    speaker_label:   Optional[str] = None
    start_ms:        int
    end_ms:          int
    segment_text:    str
    word_timestamps: Optional[str] = None   # JSON string: list of word dicts
    avg_logprob:     Optional[float] = None
    no_speech_prob:  Optional[float] = None

    model_config = {"from_attributes": True}
