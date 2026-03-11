"""
SQLAlchemy ORM models for Kairos.

All primary keys are TEXT UUIDs (str(uuid.uuid4())).
All datetime columns store ISO 8601 TEXT strings.
Schema changes must be additive (nullable with defaults only).
"""

from sqlalchemy import Column, Float, Integer, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Top-level research or production project container."""
    __tablename__ = "projects"

    project_id          = Column(Text, primary_key=True)
    project_name        = Column(Text, nullable=False)
    project_description = Column(Text, nullable=True)
    created_at          = Column(Text, nullable=False)
    updated_at          = Column(Text, nullable=False)


class AcquisitionSource(Base):
    """
    A monitored channel, playlist, user, or feed.
    Kairos polls enabled sources on their cron schedule and enqueues
    downloads for any new items found.
    """
    __tablename__ = "acquisition_sources"

    source_id        = Column(Text, primary_key=True)
    source_type      = Column(Text, nullable=False)
    # youtube_channel | youtube_playlist | tiktok_user | twitter_user
    # rss_podcast | local_folder
    source_url       = Column(Text, nullable=False, unique=True)
    source_name      = Column(Text, nullable=True)
    platform         = Column(Text, nullable=False)
    # youtube | twitter | tiktok | instagram | rss | local
    schedule_cron    = Column(Text, nullable=True)   # cron expression for polling
    last_polled_at   = Column(Text, nullable=True)
    enabled          = Column(Integer, nullable=False, default=1)
    download_quality = Column(Text, nullable=False,
                              default="bestvideo[height<=1080]+bestaudio/best")
    created_at       = Column(Text, nullable=False)


class MediaItem(Base):
    """
    A single source video in the Kairos library.
    Unique per platform + platform_video_id (or file path for local files).
    """
    __tablename__ = "media_items"

    item_id            = Column(Text, primary_key=True)
    source_id          = Column(Text, nullable=True)           # FK → acquisition_sources (nullable for ad-hoc downloads)
    platform           = Column(Text, nullable=False)          # youtube | twitter | tiktok | instagram | local | rss
    platform_video_id  = Column(Text, nullable=True)           # platform's native video ID (unique per platform)
    item_title         = Column(Text, nullable=True)
    item_channel       = Column(Text, nullable=True)
    item_description   = Column(Text, nullable=True)
    published_at       = Column(Text, nullable=True)           # ISO 8601
    duration_seconds   = Column(Float, nullable=True)
    original_url       = Column(Text, nullable=True)
    file_path          = Column(Text, nullable=True)           # relative path under media_library/
    audio_path         = Column(Text, nullable=True)           # relative path under media/audio/
    thumb_path         = Column(Text, nullable=True)           # relative path under media/thumbs/
    file_hash          = Column(Text, nullable=True)           # SHA-256 for dedup
    item_status        = Column(Text, nullable=False, default="queued")
    # queued | downloading | downloaded | ingesting | ready | error
    error_msg          = Column(Text, nullable=True)
    has_captions       = Column(Integer, nullable=False, default=0)
    caption_source     = Column(Text, nullable=True)           # online | whisper
    created_at         = Column(Text, nullable=False)
    updated_at         = Column(Text, nullable=False)


class TranscriptionJob(Base):
    """A Whisper transcription run for a MediaItem."""
    __tablename__ = "transcription_jobs"

    job_id        = Column(Text, primary_key=True)
    item_id       = Column(Text, nullable=False)               # FK → media_items
    whisper_model = Column(Text, nullable=True)
    language      = Column(Text, nullable=True)
    job_status    = Column(Text, nullable=False, default="queued")
    # queued | running | done | error
    error_msg     = Column(Text, nullable=True)
    started_at    = Column(Text, nullable=True)
    completed_at  = Column(Text, nullable=True)
    created_at    = Column(Text, nullable=False)


class TranscriptionSegment(Base):
    """
    A single timed text segment from a Whisper transcription.
    May include word-level timestamps and diarization speaker labels.
    """
    __tablename__ = "transcription_segments"

    segment_id      = Column(Text, primary_key=True)
    item_id         = Column(Text, nullable=False)             # FK → media_items
    job_id          = Column(Text, nullable=False)             # FK → transcription_jobs
    speaker_label   = Column(Text, nullable=True)             # SPEAKER_00, SPEAKER_01, etc.
    start_ms        = Column(Integer, nullable=False)
    end_ms          = Column(Integer, nullable=False)
    segment_text    = Column(Text, nullable=False)
    word_timestamps = Column(Text, nullable=True)             # JSON: [{"word":"...", "start_ms":0, "end_ms":500}]
    avg_logprob     = Column(Float, nullable=True)
    no_speech_prob  = Column(Float, nullable=True)
    created_at      = Column(Text, nullable=False)


class AnalysisScore(Base):
    """
    A scored signal for a MediaItem or TranscriptionSegment.
    Produced by LLM analysis tasks in Phase 2+.
    """
    __tablename__ = "analysis_scores"

    score_id      = Column(Text, primary_key=True)
    item_id       = Column(Text, nullable=False)               # FK → media_items
    segment_id    = Column(Text, nullable=True)                # FK → transcription_segments (nullable for item-level scores)
    score_type    = Column(Text, nullable=False)
    # virality | emotional | controversy | hook | qa | audience_reaction
    score_value   = Column(Float, nullable=False)              # 0.0–1.0
    score_reason  = Column(Text, nullable=True)
    scorer_model  = Column(Text, nullable=True)               # e.g. "llama3:8b"
    created_at    = Column(Text, nullable=False)


class Clip(Base):
    """
    A discrete video clip extracted from a MediaItem.
    Can be AI-generated (based on scores) or manually defined.
    """
    __tablename__ = "clips"

    clip_id         = Column(Text, primary_key=True)
    item_id         = Column(Text, nullable=False)             # FK → media_items
    clip_title      = Column(Text, nullable=True)
    start_ms        = Column(Integer, nullable=False)
    end_ms          = Column(Integer, nullable=False)
    duration_ms     = Column(Integer, nullable=False)
    clip_file_path  = Column(Text, nullable=True)              # relative path under media/clips/
    clip_thumb_path = Column(Text, nullable=True)              # relative path under media/thumbs/
    virality_score  = Column(Float, nullable=True)
    clip_status     = Column(Text, nullable=False, default="pending")
    # pending | extracting | ready | error
    clip_source     = Column(Text, nullable=False, default="ai")  # ai | manual
    speaker_label   = Column(Text, nullable=True)
    clip_transcript = Column(Text, nullable=True)
    error_msg       = Column(Text, nullable=True)
    created_at      = Column(Text, nullable=False)
    updated_at      = Column(Text, nullable=False)


class Timeline(Base):
    """
    A Story Builder timeline — an ordered sequence of clips assembled for export.
    """
    __tablename__ = "timelines"

    timeline_id        = Column(Text, primary_key=True)
    project_id         = Column(Text, nullable=True)           # FK → projects
    timeline_name      = Column(Text, nullable=False)
    story_template     = Column(Text, nullable=True)           # viral_reel | political_campaign | etc.
    aspect_ratio       = Column(Text, nullable=False, default="16:9")  # 16:9 | 9:16 | 1:1
    target_duration_ms = Column(Integer, nullable=True)
    timeline_status    = Column(Text, nullable=False, default="draft")
    # draft | ready | rendering | done | error
    created_at         = Column(Text, nullable=False)
    updated_at         = Column(Text, nullable=False)


class TimelineElement(Base):
    """An element (clip, transition, title card, overlay, audio track) in a Timeline."""
    __tablename__ = "timeline_elements"

    element_id     = Column(Text, primary_key=True)
    timeline_id    = Column(Text, nullable=False)              # FK → timelines
    element_type   = Column(Text, nullable=False)
    # clip | transition | title_card | overlay | audio_track
    position       = Column(Integer, nullable=False)           # order within timeline (0-indexed)
    start_ms       = Column(Integer, nullable=False)
    duration_ms    = Column(Integer, nullable=False)
    clip_id        = Column(Text, nullable=True)               # FK → clips (for clip elements)
    element_params = Column(Text, nullable=True)               # JSON: transition type, title text, overlay config, etc.
    created_at     = Column(Text, nullable=False)


class CaptionStyle(Base):
    """
    A named caption style preset for rendered videos.
    Stores font, color, animation, and ASS styling parameters.
    """
    __tablename__ = "caption_styles"

    style_id        = Column(Text, primary_key=True)
    style_name      = Column(Text, nullable=False, unique=True)
    platform_preset = Column(Text, nullable=True)              # tiktok | youtube | instagram
    font_name       = Column(Text, nullable=False, default="Arial")
    font_size       = Column(Integer, nullable=False, default=48)
    font_color      = Column(Text, nullable=False, default="#FFFFFF")
    outline_color   = Column(Text, nullable=False, default="#000000")
    outline_width   = Column(Integer, nullable=False, default=2)
    shadow          = Column(Integer, nullable=False, default=1)
    animation_type  = Column(Text, nullable=True)              # word_highlight | none
    position        = Column(Text, nullable=False, default="bottom")  # bottom | top | center
    style_params    = Column(Text, nullable=True)              # JSON for extra ASS styling
    created_at      = Column(Text, nullable=False)


class RenderJob(Base):
    """A render job that encodes a Timeline to a video file."""
    __tablename__ = "render_jobs"

    render_id     = Column(Text, primary_key=True)
    timeline_id   = Column(Text, nullable=False)               # FK → timelines
    render_quality = Column(Text, nullable=False, default="preview")  # preview | final
    output_path   = Column(Text, nullable=True)
    encoder       = Column(Text, nullable=True)                # h264_nvenc | libx264
    render_status = Column(Text, nullable=False, default="queued")
    # queued | running | done | error
    render_params = Column(Text, nullable=True)                # JSON: apply_captions, caption_style_id, reframe_aspect_ratio
    error_msg     = Column(Text, nullable=True)
    started_at    = Column(Text, nullable=True)
    completed_at  = Column(Text, nullable=True)
    created_at    = Column(Text, nullable=False)


class QuickJob(Base):
    """
    Single-touch orchestrated job: download → transcribe → analyze → story → render.
    Created by POST /api/jobs/quick; progress tracked by GET /api/jobs/{job_id}.
    """
    __tablename__ = "quick_jobs"

    job_id           = Column(Text, primary_key=True)
    urls             = Column(Text, nullable=False)           # JSON array of source URLs
    template_id      = Column(Text, nullable=True)            # story template
    caption_style_id = Column(Text, nullable=True)            # optional caption preset
    aspect_ratio     = Column(Text, nullable=False, default="9:16")  # 9:16 | 16:9 | 1:1
    job_status       = Column(Text, nullable=False, default="queued")
    # queued | downloading | transcribing | analyzing | generating | rendering | done | error
    stage_label      = Column(Text, nullable=True)            # human-readable stage description
    progress         = Column(Integer, nullable=False, default=0)  # 0–100
    item_ids         = Column(Text, nullable=True)            # JSON array of created item_ids
    timeline_id      = Column(Text, nullable=True)            # created timeline
    render_id        = Column(Text, nullable=True)            # created render job
    output_path      = Column(Text, nullable=True)            # final video file path
    error_msg        = Column(Text, nullable=True)
    created_at       = Column(Text, nullable=False)
    updated_at       = Column(Text, nullable=False)
