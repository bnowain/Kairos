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


# ── Analysis (Phase 3) ────────────────────────────────────────────────────────

class AnalysisScoreOut(BaseModel):
    score_id:     str
    item_id:      str
    segment_id:   Optional[str] = None
    score_type:   str
    score_value:  float
    score_reason: Optional[str] = None
    scorer_model: Optional[str] = None
    created_at:   str

    model_config = {"from_attributes": True}


class HighlightSegmentOut(BaseModel):
    """A scored segment ready for clip creation."""
    segment_id:               str
    item_id:                  str
    speaker_label:            Optional[str] = None
    start_ms:                 int
    end_ms:                   int
    segment_text:             str
    composite_virality_score: float
    llm_virality_score:       Optional[float] = None
    hook_score:               Optional[float] = None
    emotional_score:          Optional[float] = None
    controversy_score:        Optional[float] = None
    highlight_reason:         Optional[str] = None
    is_hook_candidate:        bool = False
    clip_id:                  Optional[str] = None   # set if clip already created


class ClipCreate(BaseModel):
    item_id: str
    start_ms: int
    end_ms: int
    clip_title: Optional[str] = None
    remove_silence: bool = False


class ClipUpdate(BaseModel):
    clip_title: Optional[str] = None


class ClipOut(BaseModel):
    clip_id:         str
    item_id:         str
    clip_title:      Optional[str] = None
    start_ms:        int
    end_ms:          int
    duration_ms:     int
    clip_file_path:  Optional[str] = None
    clip_thumb_path: Optional[str] = None
    virality_score:  Optional[float] = None
    clip_status:     str
    clip_source:     str
    speaker_label:   Optional[str] = None
    clip_transcript: Optional[str] = None
    error_msg:       Optional[str] = None
    created_at:      str
    updated_at:      str

    model_config = {"from_attributes": True}


# ── Story Builder / Timelines (Phase 5) ───────────────────────────────────────

class TimelineElementOut(BaseModel):
    element_id:     str
    timeline_id:    str
    element_type:   str
    position:       int
    start_ms:       int
    duration_ms:    int
    clip_id:        Optional[str] = None
    element_params: Optional[str] = None   # JSON string
    created_at:     str

    model_config = {"from_attributes": True}


class TimelineOut(BaseModel):
    timeline_id:        str
    project_id:         Optional[str] = None
    timeline_name:      str
    story_template:     Optional[str] = None
    aspect_ratio:       str
    target_duration_ms: Optional[int] = None
    timeline_status:    str
    element_count:      int = 0
    clip_count:         int = 0
    elements:           list[TimelineElementOut] = []
    created_at:         str
    updated_at:         str

    model_config = {"from_attributes": True}


class TimelineElementCreate(BaseModel):
    element_type:   str              # clip | transition | title_card | overlay
    position:       int
    duration_ms:    int
    clip_id:        Optional[str] = None
    element_params: Optional[str] = None  # JSON string


class StoryGenerateRequest(BaseModel):
    item_ids:     list[str]
    template_id:  str
    name:         str
    aspect_ratio: str = "16:9"
    pacing:       Optional[str] = None
    min_score:    float = 0.5
    project_id:   Optional[str] = None


# ── Render (Phase 6) ──────────────────────────────────────────────────────────

class RenderRequest(BaseModel):
    timeline_id: str
    quality: str = "preview"                          # preview | final
    apply_captions: bool = True
    caption_style_id: Optional[str] = None
    reframe_aspect_ratio: Optional[str] = None        # None | "9:16" | "1:1" | "16:9"


class RenderJobOut(BaseModel):
    render_id: str
    timeline_id: str
    render_quality: str
    output_path: Optional[str] = None
    encoder: Optional[str] = None
    render_status: str
    render_params: Optional[str] = None               # JSON string
    error_msg: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


# ── Captions (Phase 6) ────────────────────────────────────────────────────────

class CaptionStyleCreate(BaseModel):
    style_name: str
    platform_preset: Optional[str] = None
    font_name: str = "Arial"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow: int = 1
    animation_type: Optional[str] = None
    position: str = "bottom"
    style_params: Optional[str] = None


class CaptionStyleOut(BaseModel):
    style_id: str
    style_name: str
    platform_preset: Optional[str] = None
    font_name: str
    font_size: int
    font_color: str
    outline_color: str
    outline_width: int
    shadow: int
    animation_type: Optional[str] = None
    position: str
    style_params: Optional[str] = None
    created_at: str


# ── Smart Query (SQ-1) ───────────────────────────────────────────────────────

class SmartQueryIn(BaseModel):
    query_text: str = Field(..., description="Natural language search query")
    query_source: str = Field("kairos", description="kairos | civic_media | mixed")
    intent_profile_id: Optional[str] = None
    filters: Optional[dict] = None
    scorer_models: list[str] = Field(default=["default"], description="Provider names or 'default'")
    project_id: Optional[str] = None
    max_candidates: int = Field(100, ge=1, le=500)


class SmartQueryOut(BaseModel):
    query_id: str
    query_text: str
    query_source: str
    query_status: str
    query_progress: int = 0
    query_stage_label: Optional[str] = None
    intent_profile_id: Optional[str] = None
    scorer_models: Optional[list[str]] = None
    query_result_count: int = 0
    query_error_msg: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class QueryCandidateOut(BaseModel):
    candidate_id: str
    query_id: str
    candidate_origin: str
    candidate_item_id: Optional[str] = None
    candidate_segment_id: Optional[str] = None
    candidate_speaker: Optional[str] = None
    candidate_text: str
    candidate_start_ms: Optional[int] = None
    candidate_end_ms: Optional[int] = None
    candidate_video_title: Optional[str] = None
    candidate_video_date: Optional[str] = None
    candidate_source_url: Optional[str] = None
    intent_relevance_score: Optional[float] = None
    intent_score_reason: Optional[str] = None
    intent_scorer_model: Optional[str] = None
    candidate_user_rating: Optional[int] = None
    candidate_rating_note: Optional[str] = None
    imported_as_clip_id: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class CandidateRatingIn(BaseModel):
    rating: int = Field(..., description="1 (thumbs up) or -1 (thumbs down)")
    note: Optional[str] = None
    save_as_example: bool = True


class IntentProfileIn(BaseModel):
    intent_name: str
    intent_description: Optional[str] = None
    intent_system_prompt: Optional[str] = None


class IntentProfileOut(BaseModel):
    intent_profile_id: str
    intent_name: str
    intent_description: Optional[str] = None
    intent_system_prompt: Optional[str] = None
    intent_example_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class IntentExampleOut(BaseModel):
    example_id: str
    intent_profile_id: str
    candidate_id: Optional[str] = None
    example_text: str
    example_context: Optional[str] = None
    example_rating: int
    example_note: Optional[str] = None
    example_scorer_model: Optional[str] = None
    example_original_score: Optional[float] = None
    created_at: str

    model_config = {"from_attributes": True}


# ── Quick Jobs (Mobile M1) ────────────────────────────────────────────────────

class QuickJobIn(BaseModel):
    urls: list[str] = Field(..., min_length=1, description="One or more source video URLs")
    template_id: str = Field(..., description="Story template ID (e.g. viral_reel)")
    caption_style_id: Optional[str] = None
    aspect_ratio: str = Field("9:16", description="Output aspect ratio: 9:16 | 16:9 | 1:1")


class QuickJobOut(BaseModel):
    job_id: str
    urls: list[str] = []
    template_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    job_status: str
    stage_label: Optional[str] = None
    progress: int
    item_ids: Optional[list[str]] = None
    timeline_id: Optional[str] = None
    render_id: Optional[str] = None
    output_path: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
