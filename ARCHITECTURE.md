Now I have enough context to produce a thorough, production-grade architecture plan. Let me write it out.

---

# Kairos — Full Architecture Plan

Kairos is a fully local AI-powered video clipping, editing, and story assembly platform. It is a standalone project within the ecosystem with no Atlas spoke registration required. The design is informed by the patterns already proven in `civic_media` (faster-whisper integration, Huey dual-queue worker separation, SQLAlchemy + WAL SQLite, FastAPI routing conventions) and by the Syllego/MMI acquisition library already available in `Unified-Tools`.

---

## 1. Project Directory Structure

```
/mnt/e/0-Automated-Apps/Kairos/
│
├── kairos/                          # Python package root
│   ├── __init__.py
│   ├── config.py                    # All paths, env vars, model names
│   ├── database.py                  # SQLAlchemy engine, session, WAL pragmas
│   ├── models.py                    # All ORM table definitions
│   ├── schemas.py                   # Pydantic request/response models
│   ├── main.py                      # FastAPI app, lifespan, router registration
│   ├── worker.py                    # Huey SqliteHuey instances (gpu + light)
│   ├── tasks.py                     # All Huey task definitions
│   ├── paths.py                     # to_relative / to_absolute helpers
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── acquisition.py           # /api/acquisition/*
│   │   ├── library.py               # /api/library/*
│   │   ├── transcription.py         # /api/transcription/*
│   │   ├── analysis.py              # /api/analysis/*
│   │   ├── clips.py                 # /api/clips/*
│   │   ├── stories.py               # /api/stories/*
│   │   ├── timelines.py             # /api/timelines/*
│   │   ├── captions.py              # /api/captions/*
│   │   ├── render.py                # /api/render/*
│   │   └── system.py                # /api/health, /api/jobs, /api/config
│   │
│   └── services/
│       ├── __init__.py
│       │
│       ├── acquisition/
│       │   ├── __init__.py
│       │   ├── downloader.py        # yt-dlp orchestration, metadata extraction
│       │   ├── rss_poller.py        # Podcast RSS feed polling
│       │   ├── scheduler.py         # APScheduler jobs for monitored sources
│       │   ├── deduplicator.py      # Video ID hash dedup logic
│       │   └── library_organizer.py # Path builder: /media_library/{source}/{channel}/{year}/
│       │
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── pipeline.py          # Full ingest orchestration (download → register → audio → thumb)
│       │   ├── audio_extractor.py   # FFmpeg → mono 16kHz WAV (matches civic_media pattern)
│       │   └── thumbnailer.py       # FFmpeg seek + scale thumbnail
│       │
│       ├── transcription/
│       │   ├── __init__.py
│       │   ├── transcriber.py       # faster-whisper, word-level timestamps
│       │   ├── diarizer.py          # pyannote.audio 3.x speaker diarization
│       │   ├── aligner.py           # Merge word timestamps with speaker turns
│       │   └── exporter.py          # JSON / SRT / VTT output
│       │
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── llm_analyzer.py      # Ollama transcript analysis (highlight, virality)
│       │   ├── embedder.py          # sentence-transformers topic segmentation
│       │   ├── emotion_scorer.py    # Heuristic + LLM emotional intensity
│       │   ├── audio_events.py      # Librosa: laughter/applause energy detection
│       │   ├── controversy.py       # Rhetorical pattern detection
│       │   └── scorer.py            # Composite virality score aggregation
│       │
│       ├── clip_engine/
│       │   ├── __init__.py
│       │   ├── extractor.py         # FFmpeg NVENC clip extraction
│       │   ├── silence_remover.py   # FFmpeg silencedetect + re-splice
│       │   └── batch_clipper.py     # Batch clip generation orchestration
│       │
│       ├── story_builder/
│       │   ├── __init__.py
│       │   ├── template_loader.py   # Load/validate JSON story templates
│       │   ├── slot_assigner.py     # Assign clips to narrative slots
│       │   ├── clip_ranker.py       # Multi-signal ranking algorithm
│       │   ├── flow_enforcer.py     # Deduplication + pacing + narrative flow
│       │   ├── timeline_builder.py  # Assemble TimelineModel from ranked clips
│       │   └── mashup_engine.py     # Multi-source clip combination
│       │
│       ├── caption_engine/
│       │   ├── __init__.py
│       │   ├── generator.py         # Word-level caption generation from transcription
│       │   ├── styler.py            # Apply caption style presets
│       │   ├── burner.py            # FFmpeg drawtext/subtitles burn-in
│       │   └── exporter.py          # SRT / VTT / ASS export
│       │
│       ├── aspect_ratio/
│       │   ├── __init__.py
│       │   ├── detector.py          # MediaPipe face detection + tracking
│       │   ├── reframer.py          # Crop box calculator (16:9→9:16, etc.)
│       │   └── tracker.py           # Active speaker tracking over clip duration
│       │
│       └── renderer/
│           ├── __init__.py
│           ├── ffmpeg_builder.py    # Build FFmpeg command from TimelineModel
│           ├── preview_renderer.py  # Fast low-quality preview pass
│           ├── final_renderer.py    # High-quality final render (NVENC)
│           └── queue_manager.py    # Render job state machine
│
├── templates/                       # Story template JSON definitions
│   ├── viral_reel.json
│   ├── political_campaign.json
│   ├── debate_highlights.json
│   ├── commentary_mashup.json
│   ├── news_explainer.json
│   └── podcast_highlights.json
│
├── frontend/                        # React + TypeScript frontend (Vite)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                     # Typed API client wrappers
│       ├── components/
│       │   ├── Library/             # Media library browser
│       │   ├── Transcript/          # Segment viewer with word-level highlights
│       │   ├── ClipSelector/        # Visual clip selection with scores
│       │   ├── TimelineEditor/      # Drag-and-drop timeline with preview
│       │   ├── StoryBuilder/        # Template picker + slot assignment UI
│       │   ├── CaptionEditor/       # Style controls + real-time preview
│       │   └── RenderQueue/         # Job status, progress, download
│       ├── hooks/
│       └── pages/
│
├── media_library/                   # All downloaded source videos (gitignored)
│   └── {source}/{channel}/{year}/
│
├── media/
│   ├── clips/                       # Extracted clips
│   ├── renders/                     # Final rendered outputs
│   ├── previews/                    # Low-quality preview renders
│   ├── audio/                       # Extracted WAV files
│   └── thumbs/                      # Thumbnails
│
├── database/
│   ├── kairos.db                    # Primary SQLite WAL database
│   ├── huey_gpu.db                  # GPU task queue
│   └── huey_light.db               # Light task queue
│
├── config/
│   ├── .env                         # HF_TOKEN, OLLAMA_HOST, etc. (gitignored)
│   ├── settings.json                # User-editable app settings
│   └── vocab_hints.yml              # Whisper proper-noun hints (reuse civic_media pattern)
│
├── logs/
├── pyproject.toml
├── requirements.txt
└── CLAUDE.md
```

---

## 2. SQLite Schema

All tables use TEXT UUID primary keys (matching ecosystem convention), WAL mode, FK enforcement.

```sql
-- ── Core state ───────────────────────────────────────────────────────────────

CREATE TABLE projects (
    project_id          TEXT PRIMARY KEY,
    project_name        TEXT NOT NULL,
    project_description TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

-- ── Acquisition sources (monitored channels/feeds) ────────────────────────────

CREATE TABLE acquisition_sources (
    source_id           TEXT PRIMARY KEY,
    source_type         TEXT NOT NULL,  -- 'youtube_channel' | 'youtube_playlist' | 'tiktok_user'
                                        -- | 'twitter_user' | 'rss_podcast' | 'local_folder'
    source_url          TEXT NOT NULL UNIQUE,
    source_name         TEXT,
    platform            TEXT NOT NULL,  -- 'youtube' | 'twitter' | 'tiktok' | 'instagram'
                                        -- | 'rss' | 'local'
    schedule_cron       TEXT,           -- cron expression for auto-poll, NULL = manual only
    last_polled_at      TEXT,
    enabled             INTEGER NOT NULL DEFAULT 1,
    download_quality    TEXT NOT NULL DEFAULT 'bestvideo[height<=1080]+bestaudio/best',
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

-- ── Media items (source videos) ───────────────────────────────────────────────

CREATE TABLE media_items (
    item_id             TEXT PRIMARY KEY,
    source_id           TEXT REFERENCES acquisition_sources(source_id) ON DELETE SET NULL,
    project_id          TEXT REFERENCES projects(project_id) ON DELETE SET NULL,
    platform            TEXT NOT NULL,  -- 'youtube' | 'local' | etc.
    platform_video_id   TEXT,           -- yt-dlp id field, used for dedup
    item_title          TEXT,
    channel_name        TEXT,
    channel_id          TEXT,
    published_at        TEXT,           -- ISO 8601
    description         TEXT,
    page_url            TEXT,           -- human-browsable source URL (required per global rule §3)
    thumbnail_url       TEXT,
    thumbnail_path      TEXT,           -- local path to downloaded thumbnail
    duration_sec        REAL,
    file_path           TEXT,           -- absolute path in media_library
    file_size_bytes     INTEGER,
    video_hash          TEXT UNIQUE,    -- SHA-256 of first 10MB for local dedup
    captions_available  INTEGER NOT NULL DEFAULT 0,
    captions_source     TEXT,           -- 'auto' | 'manual' | 'whisper' | NULL
    ingest_status       TEXT NOT NULL DEFAULT 'queued',
                                        -- 'queued' | 'downloading' | 'downloaded' |
                                        -- 'extracting_audio' | 'thumbnailing' | 'ready' |
                                        -- 'failed'
    ingest_error        TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),

    UNIQUE(platform, platform_video_id)
);

CREATE INDEX ix_media_items_source ON media_items(source_id);
CREATE INDEX ix_media_items_ingest_status ON media_items(ingest_status);

-- ── Transcription ─────────────────────────────────────────────────────────────

CREATE TABLE transcription_jobs (
    job_id              TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES media_items(item_id) ON DELETE CASCADE,
    job_status          TEXT NOT NULL DEFAULT 'queued',
                                        -- 'queued' | 'running' | 'done' | 'failed'
    whisper_model       TEXT NOT NULL DEFAULT 'large-v3',
    language            TEXT,
    duration_sec        REAL,
    processing_sec      REAL,
    error_msg           TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    completed_at        TEXT,

    UNIQUE(item_id)
);

CREATE TABLE transcription_segments (
    segment_id          TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES media_items(item_id) ON DELETE CASCADE,
    segment_index       INTEGER NOT NULL,
    start_sec           REAL NOT NULL,
    end_sec             REAL NOT NULL,
    text                TEXT NOT NULL,
    speaker_label       TEXT,           -- 'SPEAKER_00' etc., NULL if no diarization
    avg_logprob         REAL,
    no_speech_prob      REAL,
    compression_ratio   REAL,
    words_json          TEXT,           -- JSON array of {word, start, end, probability}
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX ix_trans_seg_item ON transcription_segments(item_id);
CREATE INDEX ix_trans_seg_time ON transcription_segments(item_id, start_sec);

-- ── Analysis ──────────────────────────────────────────────────────────────────

CREATE TABLE analysis_scores (
    score_id            TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES media_items(item_id) ON DELETE CASCADE,
    segment_id          TEXT REFERENCES transcription_segments(segment_id) ON DELETE CASCADE,
    score_type          TEXT NOT NULL,  -- 'virality' | 'emotional_intensity' | 'controversy'
                                        -- | 'audience_reaction' | 'qa_detection' | 'clarity'
                                        -- | 'topic_relevance' | 'hook_strength'
    score_value         REAL NOT NULL,  -- normalized 0.0–1.0
    score_reason        TEXT,           -- LLM explanation or heuristic label
    scorer_model        TEXT,           -- 'llama3:8b' | 'librosa_energy' | 'heuristic' etc.
    scored_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX ix_analysis_scores_item ON analysis_scores(item_id);
CREATE INDEX ix_analysis_scores_seg ON analysis_scores(segment_id);

-- ── Clips ─────────────────────────────────────────────────────────────────────

CREATE TABLE clips (
    clip_id             TEXT PRIMARY KEY,
    item_id             TEXT NOT NULL REFERENCES media_items(item_id) ON DELETE CASCADE,
    clip_title          TEXT,
    start_sec           REAL NOT NULL,
    end_sec             REAL NOT NULL,
    duration_sec        REAL GENERATED ALWAYS AS (end_sec - start_sec) VIRTUAL,
    clip_file_path      TEXT,           -- absolute path to extracted clip MP4
    thumbnail_path      TEXT,
    virality_score      REAL,           -- cached composite from analysis_scores
    hook_strength       REAL,
    emotional_intensity REAL,
    controversy_score   REAL,
    clip_source         TEXT NOT NULL DEFAULT 'auto',  -- 'auto' | 'manual'
    clip_notes          TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX ix_clips_item ON clips(item_id);
CREATE INDEX ix_clips_virality ON clips(virality_score DESC);

-- ── Projects / Stories ────────────────────────────────────────────────────────

CREATE TABLE story_templates (
    template_id         TEXT PRIMARY KEY,
    template_name       TEXT NOT NULL UNIQUE,
    template_slug       TEXT NOT NULL UNIQUE,
    description         TEXT,
    template_json       TEXT NOT NULL,  -- full JSON template definition
    is_builtin          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE TABLE timelines (
    timeline_id         TEXT PRIMARY KEY,
    project_id          TEXT REFERENCES projects(project_id) ON DELETE SET NULL,
    template_id         TEXT REFERENCES story_templates(template_id) ON DELETE SET NULL,
    timeline_name       TEXT NOT NULL,
    timeline_status     TEXT NOT NULL DEFAULT 'draft',
                                        -- 'draft' | 'ready_to_render' | 'rendering' | 'done'
    target_aspect_ratio TEXT NOT NULL DEFAULT '16:9',  -- '16:9' | '9:16' | '1:1'
    target_duration_sec REAL,
    pacing_preset       TEXT NOT NULL DEFAULT 'measured',  -- 'fast' | 'measured' | 'dramatic'
    timeline_json       TEXT NOT NULL DEFAULT '{}',  -- full TimelineModel serialized
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE TABLE timeline_elements (
    element_id          TEXT PRIMARY KEY,
    timeline_id         TEXT NOT NULL REFERENCES timelines(timeline_id) ON DELETE CASCADE,
    element_order       INTEGER NOT NULL,
    element_type        TEXT NOT NULL,  -- 'clip' | 'title_card' | 'transition' | 'overlay'
                                        -- | 'audio_track' | 'caption_block' | 'silence_pad'
    clip_id             TEXT REFERENCES clips(clip_id) ON DELETE SET NULL,
    start_ms            INTEGER NOT NULL,
    duration_ms         INTEGER NOT NULL,
    narrative_slot      TEXT,           -- 'HOOK' | 'CONTEXT' | 'KEY_MOMENT' | 'REACTION'
                                        -- | 'CONCLUSION' | 'TRANSITION_BRIDGE'
    params_json         TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX ix_tl_elements_timeline ON timeline_elements(timeline_id, element_order);

-- ── Caption styles ────────────────────────────────────────────────────────────

CREATE TABLE caption_styles (
    style_id            TEXT PRIMARY KEY,
    style_name          TEXT NOT NULL UNIQUE,
    platform_preset     TEXT,           -- 'tiktok' | 'youtube' | 'instagram' | NULL
    font_family         TEXT NOT NULL DEFAULT 'Arial Bold',
    font_size_px        INTEGER NOT NULL DEFAULT 72,
    font_color          TEXT NOT NULL DEFAULT '#FFFFFF',
    outline_color       TEXT NOT NULL DEFAULT '#000000',
    outline_width_px    INTEGER NOT NULL DEFAULT 4,
    shadow_offset_px    INTEGER NOT NULL DEFAULT 2,
    shadow_color        TEXT NOT NULL DEFAULT '#000000',
    animation_type      TEXT NOT NULL DEFAULT 'word_highlight',
                                        -- 'none' | 'word_highlight' | 'pop_in' | 'fade'
    highlight_color     TEXT DEFAULT '#FFFF00',
    position            TEXT NOT NULL DEFAULT 'bottom',  -- 'top' | 'center' | 'bottom'
    max_chars_per_line  INTEGER NOT NULL DEFAULT 40,
    is_builtin          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

-- ── Render jobs ───────────────────────────────────────────────────────────────

CREATE TABLE render_jobs (
    render_id           TEXT PRIMARY KEY,
    timeline_id         TEXT NOT NULL REFERENCES timelines(timeline_id) ON DELETE CASCADE,
    render_type         TEXT NOT NULL DEFAULT 'preview',  -- 'preview' | 'final'
    render_status       TEXT NOT NULL DEFAULT 'queued',
                                        -- 'queued' | 'running' | 'done' | 'failed'
    output_path         TEXT,
    output_format       TEXT NOT NULL DEFAULT 'mp4',  -- 'mp4' | 'webm'
    video_codec         TEXT NOT NULL DEFAULT 'h264_nvenc',
    audio_codec         TEXT NOT NULL DEFAULT 'aac',
    bitrate_kbps        INTEGER,
    resolution          TEXT,           -- '1920x1080' | '1080x1920' etc.
    aspect_ratio        TEXT NOT NULL DEFAULT '16:9',
    caption_style_id    TEXT REFERENCES caption_styles(style_id),
    burn_captions       INTEGER NOT NULL DEFAULT 1,
    apply_face_tracking INTEGER NOT NULL DEFAULT 0,
    ffmpeg_cmd          TEXT,           -- logged ffmpeg command for reproducibility
    progress_pct        REAL,
    error_msg           TEXT,
    queued_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    started_at          TEXT,
    completed_at        TEXT
);
```

---

## 3. FastAPI Route Structure

```
GET  /api/health                        # system health + GPU status

# ── Acquisition ──────────────────────────────────────────────────────────────
GET    /api/acquisition/sources                # list all monitored sources
POST   /api/acquisition/sources                # add a new source (channel, feed, folder)
PATCH  /api/acquisition/sources/{source_id}    # update schedule, enable/disable
DELETE /api/acquisition/sources/{source_id}    # remove source
POST   /api/acquisition/download               # one-off download: {url, project_id?}
GET    /api/acquisition/queue                  # pending/active download jobs
POST   /api/acquisition/poll/{source_id}       # force-poll a specific source now

# ── Library ──────────────────────────────────────────────────────────────────
GET    /api/library/items                      # list media items (filter: status, platform, project)
GET    /api/library/items/{item_id}            # item detail + processing state
DELETE /api/library/items/{item_id}            # delete item + files
POST   /api/library/import                     # import from local path (file or folder)
GET    /api/library/items/{item_id}/thumbnail  # serve thumbnail image

# ── Transcription ────────────────────────────────────────────────────────────
POST   /api/transcription/run/{item_id}        # queue transcription job
GET    /api/transcription/status/{item_id}     # job status + progress
GET    /api/transcription/segments/{item_id}   # all segments with word-level data
PATCH  /api/transcription/segments/{seg_id}    # manually correct segment text
GET    /api/transcription/export/{item_id}     # download SRT / VTT / JSON (?format=)

# ── Analysis ─────────────────────────────────────────────────────────────────
POST   /api/analysis/run/{item_id}             # queue full analysis pipeline
GET    /api/analysis/status/{item_id}          # job status
GET    /api/analysis/scores/{item_id}          # all scored segments with signals
GET    /api/analysis/highlights/{item_id}      # ranked highlight list (?limit=, ?min_score=)

# ── Clips ────────────────────────────────────────────────────────────────────
POST   /api/clips                              # create clip from segment range or manual times
GET    /api/clips                              # list clips (?item_id=, ?min_score=, ?source=)
GET    /api/clips/{clip_id}                    # clip detail
PATCH  /api/clips/{clip_id}                    # update title, notes, time range
DELETE /api/clips/{clip_id}                    # delete clip + file
GET    /api/clips/{clip_id}/download           # serve clip file
GET    /api/clips/{clip_id}/thumbnail          # serve clip thumbnail
POST   /api/clips/{clip_id}/extract            # (re-)extract clip video file
POST   /api/clips/batch                        # batch create clips from analysis results

# ── Story Builder ────────────────────────────────────────────────────────────
GET    /api/stories/templates                  # list all story templates
GET    /api/stories/templates/{template_id}    # template detail + slot definitions
POST   /api/stories/generate                   # auto-generate timeline from template + clip pool
GET    /api/stories/{timeline_id}/preview      # get timeline preview data

# ── Timelines ────────────────────────────────────────────────────────────────
POST   /api/timelines                          # create a new timeline
GET    /api/timelines                          # list timelines (?project_id=)
GET    /api/timelines/{timeline_id}            # full timeline with elements
PUT    /api/timelines/{timeline_id}            # replace full timeline_json
PATCH  /api/timelines/{timeline_id}            # update metadata (name, pacing, target_aspect)
DELETE /api/timelines/{timeline_id}            # delete timeline + elements

POST   /api/timelines/{timeline_id}/elements           # add an element
PATCH  /api/timelines/{timeline_id}/elements/{el_id}   # update element (order, params)
DELETE /api/timelines/{timeline_id}/elements/{el_id}   # remove element
POST   /api/timelines/{timeline_id}/reorder            # reorder elements [{element_id, order}]

# ── Captions ────────────────────────────────────────────────────────────────
GET    /api/captions/styles                    # list caption styles
POST   /api/captions/styles                    # create custom style
PATCH  /api/captions/styles/{style_id}         # update style
POST   /api/captions/preview                   # render single caption style preview frame

# ── Render ───────────────────────────────────────────────────────────────────
POST   /api/render/preview/{timeline_id}       # queue preview render
POST   /api/render/final/{timeline_id}         # queue final render
GET    /api/render/jobs                        # list all render jobs (?timeline_id=, ?status=)
GET    /api/render/jobs/{render_id}            # job detail + progress
DELETE /api/render/jobs/{render_id}            # cancel + delete job
GET    /api/render/jobs/{render_id}/download   # serve rendered output file

# ── System ───────────────────────────────────────────────────────────────────
GET    /api/jobs                               # unified job queue status (all types)
GET    /api/config                             # current config (model, GPU, paths)
PATCH  /api/config                             # update runtime config
GET    /api/gpu                                # CUDA device status (nvidia-smi data)
```

---

## 4. Technology Stack

### Backend
| Component | Library | Version | Notes |
|---|---|---|---|
| Web framework | FastAPI | 0.115.x | async, type-annotated |
| ORM | SQLAlchemy | 2.x | with raw SQLite connect_args for WAL |
| DB driver | aiosqlite (read) + sqlite3 (write via huey) | stdlib/0.20.x | WAL allows concurrent reads |
| Task queue | huey[sqlite] | 2.5.x | dual-queue: gpu + light (proven in civic_media) |
| Transcription | faster-whisper | 1.1.x | CTranslate2 backend, CUDA float16 |
| Diarization | pyannote.audio | 3.3.x | requires HF_TOKEN |
| Audio preprocessing | ffmpeg (subprocess) | 7.x | HPF + loudnorm chain |
| LLM | ollama Python client | 0.4.x | points to local Ollama server |
| Embeddings | sentence-transformers | 3.x | `all-MiniLM-L6-v2` for speed, `bge-large-en-v1.5` for quality |
| Audio event detection | librosa | 0.11.x | energy + onset detection |
| Downloader | yt-dlp | 2025.x (latest) | platform acquisition |
| Scheduler | APScheduler | 3.10.x | SQLite job store, cron-triggered polls |
| Face detection | mediapipe | 0.10.x | CPU-viable for face bbox; fallback for tracking |
| Face tracking (optional) | insightface | 0.7.x | GPU-accelerated, better for dense scenes |
| Video processing | ffmpeg (NVENC) | 7.x via subprocess | all encode/decode ops |
| Server | uvicorn | 0.32.x | single worker; Huey handles concurrency |

### Frontend
| Component | Library | Notes |
|---|---|---|
| Framework | React 19 + TypeScript | |
| Build | Vite 6.x | dev server + HMR |
| UI components | shadcn/ui | consistent with Signal-Desk |
| Styling | TailwindCSS 3.x | |
| Timeline UI | `react-use-gesture` + custom canvas | for drag-and-drop timeline |
| Video player | `react-player` (wraps HTML5 video) | preview playback with seek |
| State | Zustand 5.x | lightweight, no Redux overhead |
| Data fetching | TanStack Query 5.x | cache + background refresh |
| Charts | Recharts | score visualization |

---

## 5. Data Flow Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ACQUISITION LAYER                                     │
│                                                                                 │
│  yt-dlp / RSS / Local  ──►  acquisition_sources (SQLite)                       │
│  APScheduler polls     ──►  huey_light: download_task                          │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ file saved to media_library/
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INGEST LAYER                                          │
│                                                                                 │
│  huey_light: ingest_task                                                        │
│    1. Register media_items row (status=downloading→downloaded)                  │
│    2. Extract metadata (yt-dlp info.json)                                       │
│    3. ffmpeg → 16kHz mono WAV  (audio_extractor.py)                            │
│    4. ffmpeg seek → thumbnail  (thumbnailer.py)                                 │
│    5. Update status=ready → trigger transcription                               │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ enqueue transcription_task
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          TRANSCRIPTION LAYER                                    │
│                                                                                 │
│  huey_gpu: transcription_task                                                   │
│    1. faster-whisper large-v3 → segments + word timestamps (GPU float16)       │
│    2. pyannote.audio 3.x → speaker turn timeline (GPU)                         │
│    3. aligner.py → merge words + speaker labels                                 │
│    4. Write transcription_segments to SQLite                                    │
│    5. Export SRT/VTT/JSON to disk                                               │
│    6. Update transcription_jobs status=done → trigger analysis                  │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ enqueue analysis_task
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ANALYSIS LAYER                                        │
│                                                                                 │
│  huey_gpu: analysis_task  (GPU for embeddings; CPU for heuristics)             │
│    1. LLM Analyzer (Ollama) → per-segment highlight_score + reason             │
│    2. sentence-transformers → topic segments + embedding similarity             │
│    3. Librosa energy → laughter/applause event timestamps                       │
│    4. Emotion/controversy heuristics                                            │
│    5. scorer.py → composite virality_score per segment (0.0–1.0)               │
│    6. Write analysis_scores to SQLite                                           │
│    7. Auto-create clip rows for segments above threshold                        │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ clips created in DB (files pending)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CLIP ENGINE                                          │
│                                                                                 │
│  huey_light: extract_clip_task (per-clip, batched)                             │
│    1. ffmpeg -ss {start} -to {end} -c:v h264_nvenc -c:a aac                   │
│    2. Silence removal pass (silencedetect + concat demuxer)                    │
│    3. Thumbnail from midpoint frame                                             │
│    4. Update clips.clip_file_path, status=ready                                │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ clips available in library
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        STORY BUILDER ENGINE (SBE)                               │
│                                                                                 │
│  On-demand (user or API-triggered)                                              │
│    1. Load template → slot definitions                                          │
│    2. clip_ranker.py → multi-signal ranking                                     │
│    3. slot_assigner.py → fit ranked clips to narrative slots                    │
│    4. flow_enforcer.py → dedup, pacing, transition selection                    │
│    5. timeline_builder.py → TimelineModel JSON                                  │
│    6. Write timelines + timeline_elements to SQLite                              │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │ timeline ready for editing or render
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RENDER ENGINE                                         │
│                                                                                 │
│  huey_gpu: render_task                                                          │
│    1. ffmpeg_builder.py → build filter_complex from TimelineModel              │
│    2. Caption burn-in (ASS subtitles or drawtext filter)                       │
│    3. Aspect ratio / reframe (crop + scale, optional face tracking)            │
│    4. Preview: libx264 fast preset, 720p, CRF 28                               │
│    5. Final: h264_nvenc (or hevc_nvenc), target bitrate, full resolution       │
│    6. Update render_jobs: progress_pct → status=done                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Story Builder Timeline Data Structure (Full JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "KairosTimeline",
  "description": "Complete serializable timeline model for a Kairos story assembly",
  "type": "object",
  "required": ["timeline_id", "version", "metadata", "elements"],
  "properties": {
    "timeline_id": { "type": "string" },
    "version": { "type": "string", "const": "1.0" },
    "metadata": {
      "type": "object",
      "required": ["timeline_name", "template_slug", "target_aspect_ratio", "pacing_preset"],
      "properties": {
        "timeline_name":       { "type": "string" },
        "template_slug":       { "type": "string" },
        "target_aspect_ratio": { "type": "string", "enum": ["16:9", "9:16", "1:1"] },
        "target_duration_sec": { "type": ["number", "null"] },
        "pacing_preset":       { "type": "string", "enum": ["fast", "measured", "dramatic"] },
        "caption_style_id":    { "type": ["string", "null"] },
        "created_at":          { "type": "string", "format": "date-time" },
        "updated_at":          { "type": "string", "format": "date-time" }
      }
    },
    "elements": {
      "type": "array",
      "description": "Ordered list of timeline elements",
      "items": {
        "type": "object",
        "required": ["element_id", "element_type", "start_ms", "duration_ms"],
        "properties": {
          "element_id":    { "type": "string" },
          "element_type":  {
            "type": "string",
            "enum": ["clip", "title_card", "transition", "overlay", "audio_track",
                     "caption_block", "silence_pad"]
          },
          "start_ms":      { "type": "integer", "minimum": 0 },
          "duration_ms":   { "type": "integer", "minimum": 0 },
          "narrative_slot": {
            "type": ["string", "null"],
            "enum": ["HOOK", "CONTEXT", "KEY_MOMENT", "REACTION",
                     "CONTRADICTION", "EVIDENCE", "CONCLUSION",
                     "TRANSITION_BRIDGE", null]
          },
          "element_order": { "type": "integer" },
          "params": {
            "type": "object",
            "description": "Type-specific parameters",
            "oneOf": [
              {
                "title": "ClipParams",
                "required": ["clip_id", "source_start_sec", "source_end_sec"],
                "properties": {
                  "clip_id":          { "type": "string" },
                  "source_start_sec": { "type": "number" },
                  "source_end_sec":   { "type": "number" },
                  "speed_factor":     { "type": "number", "default": 1.0 },
                  "volume_gain_db":   { "type": "number", "default": 0.0 },
                  "reframe":          {
                    "type": ["object", "null"],
                    "properties": {
                      "crop_x":  { "type": "integer" },
                      "crop_y":  { "type": "integer" },
                      "crop_w":  { "type": "integer" },
                      "crop_h":  { "type": "integer" },
                      "use_face_tracking": { "type": "boolean", "default": false }
                    }
                  },
                  "silence_removal": { "type": "boolean", "default": false }
                }
              },
              {
                "title": "TitleCardParams",
                "required": ["title_text"],
                "properties": {
                  "title_text":        { "type": "string" },
                  "subtitle_text":     { "type": ["string", "null"] },
                  "background_color":  { "type": "string", "default": "#000000" },
                  "text_color":        { "type": "string", "default": "#FFFFFF" },
                  "font_size_px":      { "type": "integer", "default": 80 },
                  "animation":         { "type": "string", "enum": ["fade", "slide", "none"],
                                         "default": "fade" }
                }
              },
              {
                "title": "TransitionParams",
                "required": ["transition_type"],
                "properties": {
                  "transition_type": {
                    "type": "string",
                    "enum": ["crossfade", "fade_to_black", "wipe_left", "wipe_right",
                             "push_left", "push_right", "cut"]
                  },
                  "overlap_ms": { "type": "integer", "default": 500 }
                }
              },
              {
                "title": "OverlayParams",
                "required": ["overlay_text"],
                "properties": {
                  "overlay_text":   { "type": "string" },
                  "position_x_pct": { "type": "number", "default": 0.05 },
                  "position_y_pct": { "type": "number", "default": 0.85 },
                  "font_size_px":   { "type": "integer", "default": 48 },
                  "text_color":     { "type": "string", "default": "#FFFFFF" },
                  "background":     { "type": "boolean", "default": true }
                }
              },
              {
                "title": "AudioTrackParams",
                "required": ["audio_file_path"],
                "properties": {
                  "audio_file_path": { "type": "string" },
                  "volume_pct":      { "type": "number", "default": 0.15 },
                  "fade_in_ms":      { "type": "integer", "default": 1000 },
                  "fade_out_ms":     { "type": "integer", "default": 2000 }
                }
              },
              {
                "title": "CaptionBlockParams",
                "required": ["caption_style_id", "srt_content"],
                "properties": {
                  "caption_style_id": { "type": "string" },
                  "srt_content":      { "type": "string" },
                  "word_highlight":   { "type": "boolean", "default": true }
                }
              }
            ]
          }
        }
      }
    }
  }
}
```

---

## 7. Clip Selection Algorithm (SBE Step-by-Step)

The Story Builder Engine clip selection operates as a multi-pass ranked assignment algorithm. It is deliberately deterministic given the same inputs — no randomness, making outputs auditable and reproducible.

### Pass 1: Pool Construction
1. Accept a `clip_pool`: a list of `clip_id` values the user has designated as eligible (or all clips for the item/project if not specified).
2. For each clip, fetch its `analysis_scores` from SQLite. Compute a **composite score** using a weighted formula controlled by the template:
   ```
   composite = (
       w_virality       * virality_score +
       w_hook           * hook_strength +
       w_emotion        * emotional_intensity +
       w_controversy    * controversy_score +
       w_reaction       * audience_reaction_score +
       w_clarity        * clarity_score +
       w_topic          * topic_relevance_score
   )
   ```
   Weights are defined in the story template JSON (see Section 8). Sum of weights = 1.0.
3. Sort pool descending by `composite`.
4. Apply hard filters:
   - Remove clips shorter than `template.min_clip_sec` (default: 5s).
   - Remove clips longer than `template.max_clip_sec` (default: 90s).
   - Remove clips with `composite < template.min_composite_threshold` (default: 0.35).

### Pass 2: Slot Matching
1. Load template's `slot_definitions` — an ordered list of narrative slots (e.g., `[HOOK, CONTEXT, KEY_MOMENT, KEY_MOMENT, KEY_MOMENT, REACTION, CONCLUSION]`). Each slot has:
   - `slot_type`: one of the narrative roles
   - `required`: bool
   - `min_score_override`: optional per-slot minimum
   - `preferred_signals`: which scores to weight most for this slot (e.g., HOOK prefers `hook_strength` and `emotional_intensity`)
2. For each slot, compute a **slot-specific re-rank** of the remaining pool using the slot's `preferred_signals`.
3. Greedily assign the top-ranked available clip to each required slot.
4. Mark that clip as used.
5. Continue through optional slots, skipping if the pool is exhausted.

### Pass 3: Deduplication and Overlap Prevention
1. For any clip assigned to a slot, check all other assigned clips for **content overlap**: if two clips share the same `item_id` and their time ranges overlap by more than `overlap_tolerance_sec` (default: 2s), keep the higher-composite clip and find the next best for the other slot.
2. Check for **semantic duplication**: if two clips have embeddings with cosine similarity > 0.85, they are near-duplicates. Remove the lower-composite one from the final assignment and fill from remaining pool.

### Pass 4: Narrative Flow Enforcement
1. Apply **pacing control** based on `pacing_preset`:
   - `fast`: transition clips to max 25s each (trim `source_end_sec` if needed), insert `cut` transitions.
   - `measured`: keep full clip duration, use `crossfade` (500ms) between clips.
   - `dramatic`: allow clips up to 120s, insert `fade_to_black` (1s) between major slots.
2. Insert transition `timeline_elements` between each clip pair using the selected transition type.
3. Prepend HOOK with a 250ms `silence_pad` if it is a cold open (no title card).
4. If template defines an intro slot and a title card template, prepend a `title_card` element using the video's title.
5. If template defines a conclusion slot, append a `fade_to_black` transition followed by an optional `title_card` outro.

### Pass 5: Timeline Assembly
1. Walk the ordered slot assignments and build `timeline_elements` with sequential `start_ms` values.
2. Account for transition overlap: a 500ms crossfade means the next clip starts 500ms before the current clip ends.
3. Write the assembled `TimelineModel` JSON to `timelines.timeline_json` and individual rows to `timeline_elements`.
4. Return the timeline ID.

---

## 8. Story Template Framework

Templates are JSON files in `kairos/templates/`. They are loaded at startup and seeded into `story_templates`. Users can clone and extend them; `is_builtin=1` templates are read-only.

### Template Schema (JSON)

```json
{
  "template_id": "viral_reel",
  "template_name": "Viral Reel",
  "description": "Strongest moments first, fast cuts, optimized for short-form platforms.",
  "target_duration_sec": 60,
  "pacing_preset": "fast",
  "default_aspect_ratio": "9:16",
  "min_clip_sec": 5,
  "max_clip_sec": 25,
  "min_composite_threshold": 0.45,

  "score_weights": {
    "virality":       0.35,
    "hook_strength":  0.25,
    "emotion":        0.20,
    "controversy":    0.10,
    "audience_react": 0.05,
    "clarity":        0.05,
    "topic_rel":      0.00
  },

  "slot_definitions": [
    {
      "slot_type": "HOOK",
      "required": true,
      "preferred_signals": ["hook_strength", "emotional_intensity"],
      "min_score_override": 0.6,
      "max_duration_sec": 10,
      "description": "Must grab attention in the first 3 seconds"
    },
    {
      "slot_type": "KEY_MOMENT",
      "required": true,
      "preferred_signals": ["virality", "emotional_intensity"],
      "count": 3,
      "description": "Top 3 highlight moments"
    },
    {
      "slot_type": "REACTION",
      "required": false,
      "preferred_signals": ["audience_reaction_score"],
      "description": "Audience response if available"
    },
    {
      "slot_type": "CONCLUSION",
      "required": false,
      "preferred_signals": ["clarity", "hook_strength"],
      "description": "Punchy close"
    }
  ],

  "transition_rules": {
    "between_slots": "cut",
    "hook_to_first_key": "cut",
    "final_to_conclusion": "fade_to_black"
  },

  "intro": {
    "enabled": false
  },

  "outro": {
    "enabled": true,
    "title_text_template": "{channel_name}",
    "duration_sec": 2
  }
}
```

The `political_campaign` template would flip `score_weights` to emphasize `clarity` and `topic_relevance` with `controversial=0.30`, define slots as `[HOOK, CLAIM, EVIDENCE, EVIDENCE, CONTRADICTION, RESOLUTION, CLOSE]`, and use `measured` pacing. Templates are self-describing and extend naturally by adding slot types; the `slot_assigner.py` treats unknown slot types as generic KEY_MOMENT.

---

## 9. SupoClip Reuse vs Replace Analysis

| SupoClip Component | Verdict | Kairos Approach |
|---|---|---|
| **PostgreSQL + Redis + Docker** | Replace entirely | SQLite WAL + Huey SqliteHuey. No external services. This is the biggest structural win. |
| **AssemblyAI transcription** | Replace | faster-whisper + pyannote. Local, GPU-accelerated, word-level. Matches or beats quality for English civic media. |
| **LLM routing (OpenAI/Gemini/Ollama)** | Partial reuse concept | Keep Ollama as the local LLM, but build Kairos-specific prompt chains. The multi-provider router is unnecessary without external APIs. |
| **Virality scoring concept** | Reuse concept, rebuild impl | SupoClip's scoring is a single LLM prompt. Kairos builds multi-signal composite (audio events + embeddings + LLM + heuristics). |
| **Clip extraction (FFmpeg)** | Reuse approach | Same FFmpeg subprocess pattern, but add NVENC encode path and silence removal. |
| **Basic clip generation** | Reuse concept | Kairos extends this significantly with batch generation, story templates, and ordering. |
| **FastAPI + TypeScript frontend pattern** | Reuse pattern | Same architecture. Kairos adopts FastAPI backend + Vite React frontend (consistent with Mission Control). |
| **Pluggable platform architecture** | Inspect for ideas | SupoClip's worker architecture is Docker-based. Huey + SQLite is a proven local-first replacement. |
| **Missing: mashup/multi-source** | Net new | No SupoClip equivalent. |
| **Missing: SBE / story templates** | Net new | SupoClip has no narrative assembly concept. |
| **Missing: caption styling** | Net new | SupoClip has no caption UI. |
| **Missing: face tracking / reframe** | Net new | SupoClip has no aspect ratio intelligence. |
| **Missing: GPU-native pipeline** | Net new | SupoClip uses CPU paths throughout. |

**Summary**: SupoClip provides useful architectural validation that FastAPI + background workers + LLM scoring is the right shape. Kairos reuses zero of its actual code (wrong database, external APIs, no GPU path), but its conceptual model — download → transcribe → score → clip — is sound and Kairos extends it with five new subsystems.

---

## 10. Phase-by-Phase Roadmap

### Phase 1: Foundation (Low complexity)
**Goal**: Running service with media acquisition, ingest, and a browsable library.

**Components:**
- `kairos/config.py`, `kairos/database.py`, `kairos/models.py` (all tables DDL)
- `kairos/worker.py` (huey_gpu + huey_light instances, priority control)
- `kairos/services/acquisition/downloader.py` (yt-dlp, metadata extraction, library organizer)
- `kairos/services/ingest/pipeline.py` (register → audio extract → thumbnail)
- `kairos/services/ingest/audio_extractor.py` (FFmpeg → 16kHz WAV — copy from civic_media, adapt)
- `kairos/routers/acquisition.py`, `kairos/routers/library.py`, `kairos/routers/system.py`
- React frontend: Library page (list, search, filter by status/platform), item detail page

**Dependencies**: yt-dlp, ffmpeg (PATH), huey, SQLAlchemy, FastAPI, uvicorn

**Testing strategy**: Integration test: provide a YouTube URL, assert file lands in `media_library/`, metadata written to SQLite, thumbnail generated. Test dedup: download same URL twice, assert single row. Ingest pipeline state machine: assert each status transition is persisted.

---

### Phase 2: Transcription + Segment Viewer (High complexity — GPU required)
**Goal**: Word-level transcripts with speaker diarization, browsable in UI.

**Components:**
- `kairos/services/transcription/transcriber.py` (faster-whisper, copy VAD settings from civic_media, adapt)
- `kairos/services/transcription/diarizer.py` (pyannote 3.x, copy from civic_media)
- `kairos/services/transcription/aligner.py` (word → speaker label merge — net new)
- `kairos/services/transcription/exporter.py` (SRT/VTT/JSON output)
- `kairos/routers/transcription.py`
- React frontend: Transcript viewer with word-level highlighting, speaker color coding, export buttons

**Dependencies**: faster-whisper 1.1.x, pyannote.audio 3.3.x, HF_TOKEN in .env, CUDA drivers

**Testing strategy**: Transcribe a known test clip (30s speech with known text). Assert segment count > 0, word timestamps present, no hallucination artifacts (compression ratio < 2.4). Diarization: two-speaker test clip, assert two distinct speaker labels. Alignment: assert every word maps to exactly one speaker segment.

---

### Phase 3: AI Analysis + Clip Scoring (High complexity)
**Goal**: Auto-generate scored highlight candidates; user can browse and curate.

**Components:**
- `kairos/services/analysis/llm_analyzer.py` (Ollama, per-segment prompt with virality + hook scoring)
- `kairos/services/analysis/embedder.py` (sentence-transformers, topic segment clustering)
- `kairos/services/analysis/audio_events.py` (librosa onset + energy: laughter/applause detection)
- `kairos/services/analysis/emotion_scorer.py` (heuristic punctuation/capitalization + LLM fallback)
- `kairos/services/analysis/scorer.py` (composite aggregation)
- `kairos/routers/analysis.py`
- React frontend: Scored segment list with signal breakdown, color-coded score bars, "Create Clip" action per row

**Dependencies**: ollama Python client, sentence-transformers, librosa, Ollama server running locally

**Testing strategy**: Run on a 10-minute civic meeting recording with known highlights (pre-verified manually). Assert top 3 scored segments match known highlights. LLM scorer: mock Ollama response, assert score parsing is robust to JSON malformation. Composite scorer: unit-test weight sum = 1.0 invariant.

---

### Phase 4: Clip Engine + Manual Editing (Medium complexity)
**Goal**: Clips are extracted to disk; user can refine boundaries and create manual clips.

**Components:**
- `kairos/services/clip_engine/extractor.py` (FFmpeg NVENC, with CPU fallback detection)
- `kairos/services/clip_engine/silence_remover.py` (silencedetect + concat demuxer)
- `kairos/services/clip_engine/batch_clipper.py`
- `kairos/routers/clips.py`
- React frontend: Clip library with video preview player, boundary adjustment UI (scrubber with waveform), bulk select + batch extract

**Dependencies**: FFmpeg with NVENC (detected at startup via `ffmpeg -encoders | grep nvenc`), CPU fallback to libx264

**Testing strategy**: Extract a 10s clip from a known video. Assert output file exists, duration matches within 0.1s. Silence removal: clip with known silence gaps, assert output is shorter. NVENC: detect at test time and skip if not available (mark as GPU-only test). Batch: 10 clips extracted concurrently via Huey, assert all succeed.

---

### Phase 5: Story Builder Engine + Timeline Editor (Very High complexity)
**Goal**: Template-driven automatic story assembly + user editing of the timeline.

**Components:**
- `kairos/services/story_builder/template_loader.py`
- `kairos/services/story_builder/clip_ranker.py`
- `kairos/services/story_builder/slot_assigner.py`
- `kairos/services/story_builder/flow_enforcer.py`
- `kairos/services/story_builder/timeline_builder.py`
- `kairos/services/story_builder/mashup_engine.py` (multi-source)
- All 6 template JSON files
- `kairos/routers/stories.py`, `kairos/routers/timelines.py`
- React frontend: Template picker, clip pool selector, auto-generated timeline view, drag-and-drop element reordering, slot assignment visualization, pacing controls

**Dependencies**: All Phase 1–4 components. sentence-transformers (for semantic dedup in Pass 3).

**Testing strategy**: Generate a timeline from a 30-clip pool using the `viral_reel` template. Assert: HOOK slot is filled, composite score of HOOK clip is > 0.6, no two clips overlap, total duration is within 20% of target. Semantic dedup: inject two near-identical clips, assert only one appears in output. Mashup: two source videos + mashup template, assert clips from both sources are present.

---

### Phase 6: Rendering Pipeline + Caption + Reframe (Very High complexity)
**Goal**: Full render-to-output with captions, aspect ratio conversion, and face tracking.

**Components:**
- `kairos/services/renderer/ffmpeg_builder.py` (filter_complex construction from TimelineModel)
- `kairos/services/renderer/preview_renderer.py`
- `kairos/services/renderer/final_renderer.py`
- `kairos/services/caption_engine/` (all files)
- `kairos/services/aspect_ratio/` (all files — MediaPipe face detect, reframer, tracker)
- `kairos/routers/render.py`, `kairos/routers/captions.py`
- React frontend: Render queue dashboard, caption style editor with live preview frame, aspect ratio picker with face detection preview, download buttons

**Dependencies**: MediaPipe 0.10.x, InsightFace 0.7.x (optional GPU path), FFmpeg complex filter knowledge (this is the hardest FFmpeg work in the project — `filter_complex` for crossfades, concat, and subtitle burn-in simultaneously).

**Testing strategy**: Render a 3-clip timeline to MP4. Assert output file plays (ffprobe duration check). Caption burn-in: render with known SRT, assert subtitle text visible via frame extraction (ffmpeg seek + OCR or pixel check). Reframe: 16:9 source → 9:16 output, assert output resolution is 1080x1920. Face detection: clip with known face, assert crop box intersects face bbox from MediaPipe. NVENC render: duration < 2x real time on GPU.

---

## 11. GPU Acceleration Map

| Operation | CUDA Usage | Library / Mechanism | CPU Fallback |
|---|---|---|---|
| Audio extraction | No (I/O bound) | FFmpeg (CPU, mono WAV) | N/A — always CPU |
| Whisper transcription | Yes — primary | faster-whisper, CTranslate2 CUDA float16 | `device="cpu"` in config |
| Speaker diarization | Yes — primary | pyannote.audio `.to(cuda)` | `.to(cpu)` — 4–8x slower |
| Sentence embeddings (analysis) | Yes — beneficial | sentence-transformers, torch CUDA | `device="cpu"`, ~3x slower |
| Librosa audio events | No | NumPy/CPU only | N/A — always CPU |
| LLM analysis (Ollama) | Yes — via Ollama | Ollama server manages GPU layers | Ollama CPU mode |
| Clip extraction (FFmpeg) | Yes — NVENC encode | `h264_nvenc` or `hevc_nvenc` | `libx264` CPU fallback |
| Silence detection | No | FFmpeg `silencedetect` filter (CPU) | N/A |
| Face detection (MediaPipe) | No (MediaPipe 0.10 CPU-only on Linux) | MediaPipe CPU delegate | N/A |
| Face tracking (InsightFace) | Yes — optional | InsightFace ONNX CUDA provider | ONNX CPU provider |
| Transition filter_complex | No (FFmpeg mixes on CPU) | FFmpeg `xfade` filter | N/A |
| Caption burn-in | No | FFmpeg `subtitles` filter (CPU) | N/A |
| Preview render (libx264) | No | FFmpeg CPU encode | N/A — this is the fallback |
| Final render (NVENC) | Yes — primary | FFmpeg `-c:v h264_nvenc` | `-c:v libx264 -preset slow` |

**CUDA detection at startup** (`kairos/config.py`):
```python
import subprocess
_nvenc_available = "h264_nvenc" in subprocess.run(
    ["ffmpeg", "-encoders"], capture_output=True, text=True
).stdout

import torch
_cuda_available = torch.cuda.is_available()

WHISPER_DEVICE  = "cuda" if _cuda_available else "cpu"
WHISPER_COMPUTE = "float16" if _cuda_available else "int8"
VIDEO_ENCODER   = "h264_nvenc" if _nvenc_available else "libx264"
```

All GPU-heavy Huey tasks (transcription, diarization, embeddings, final render) go to `huey_gpu` (1 worker thread). All I/O-bound tasks (download, clip extraction, preview render) go to `huey_light` (2 worker threads). This prevents GPU contention while allowing concurrent download + clip work.

---

### Critical Files for Implementation

- `/mnt/e/0-Automated-Apps/civic_media/app/services/transcriber.py` — Whisper VAD config, hallucination filtering, and GPU settings to copy verbatim into `kairos/services/transcription/transcriber.py`; this is the most mature faster-whisper integration in the ecosystem
- `/mnt/e/0-Automated-Apps/civic_media/app/worker.py` — Dual SqliteHuey queue pattern (gpu vs light), orphan recovery, and priority-setting to replicate exactly in `kairos/worker.py`
- `/mnt/e/0-Automated-Apps/civic_media/app/database.py` — WAL pragma setup, `validate_schema_columns` auto-migration pattern, and `get_db` dependency to replicate in `kairos/database.py`
- `/mnt/e/0-Automated-Apps/civic_media/app/routers/clips.py` — FFmpeg clip extraction, thumbnail generation, and file-serving patterns to adapt in `kairos/routers/clips.py` and `kairos/services/clip_engine/extractor.py`
- `/mnt/e/0-Automated-Apps/Unified-Tools/Syllego/AGENT_SPEC.md` — `mmi.ingest(url)` API for `kairos/services/acquisition/downloader.py`; Syllego already handles YouTube/Twitter/TikTok/Instagram routing and should be the first acquisition strategy tried before writing custom yt-dlp wrappers
