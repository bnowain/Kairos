# Kairos — CLAUDE.md

Agent instructions for this project.

## Project Overview

Kairos is a **fully local AI-powered video clipping and story assembly platform**.
It is a **standalone project** — not an Atlas spoke, no health endpoint registration.

## Tech Stack

- Python 3.11+
- FastAPI 0.115.x — REST API
- SQLAlchemy 2.x with SQLite WAL (`database/kairos.db`)
- Huey[sqlite] — dual-queue task workers (`huey_gpu.db`, `huey_light.db`)
- yt-dlp — video acquisition fallback
- Syllego/MMI — primary acquisition library (see `Unified-Tools/Syllego/AGENT_SPEC.md`)
- APScheduler 3.10.x — scheduled source polling
- FFmpeg — audio extraction, thumbnail generation, rendering

## Port

**8400** — claimed in `E:/0-Automated-Apps/CLAUDE.md` port registry.

## Key Paths

| Path | Purpose |
|------|---------|
| `kairos/` | Python package root |
| `kairos/config.py` | All env vars, paths, GPU detection |
| `kairos/models.py` | All SQLAlchemy ORM models |
| `kairos/tasks.py` | All Huey task definitions |
| `kairos/routers/` | FastAPI route handlers |
| `kairos/services/acquisition/` | Downloader, deduplicator, library organizer |
| `kairos/services/ingest/` | Audio extractor, thumbnailer, ingest pipeline |
| `kairos/services/transcription/` | faster-whisper, pyannote diarization, alignment |
| `kairos/services/analysis/` | LLM analyzer, emotion/controversy/audio scoring |
| `kairos/services/clip_engine/` | FFmpeg NVENC extraction, silence removal, batch |
| `kairos/services/story_builder/` | Template loading, slot assignment, clip ranking, timeline assembly |
| `kairos/services/caption_engine/` | Word-level captions, styling, burn-in, SRT/VTT/ASS export |
| `kairos/services/aspect_ratio/` | MediaPipe face detection, reframing, tracking |
| `kairos/services/renderer/` | FFmpeg builder, preview/final rendering, queue |
| `kairos/services/smart_query/` | Intent scoring, data fetching, orchestration |
| `frontend/` | React + Vite + TypeScript SPA |
| `database/kairos.db` | Main SQLite database |
| `database/huey_gpu.db` | GPU task queue |
| `database/huey_light.db` | I/O task queue |
| `media_library/` | Downloaded source videos (organized by platform/channel/year) |
| `media/audio/` | Extracted WAV files |
| `media/thumbs/` | Extracted thumbnail JPGs |
| `media/clips/` | Cut clips |
| `media/renders/` | Final render outputs |
| `templates/` | Story template JSON files |

## How to Run

```bash
# Install dependencies
pip install -e .

# Copy and configure env
cp .env.example .env

# Start API server
python start.py
# or directly:
uvicorn kairos.main:app --host 0.0.0.0 --port 8400 --reload

# Start workers (separate terminals)
huey_consumer kairos.worker.huey_gpu  -w 1 -k thread
huey_consumer kairos.worker.huey_light -w 2 -k thread
```

## Development Rules

1. All datetimes: `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")`
2. All UUIDs: `str(uuid.uuid4())`
3. All file opens: `encoding="utf-8"`
4. All subprocess calls: `capture_output=True, text=True, encoding="utf-8"`
5. SQLite WAL pragmas on every connection (enforced in `database.py`)
6. Syllego import in try/except — always fall back to yt-dlp if not installed
7. Schema changes: add nullable columns only (additive-only rule)
8. This is standalone — do NOT add Atlas registration or health endpoint polling

## Phase Status

- **Phase 1** (done): Acquisition + ingest pipeline. Download videos, organize library,
  extract audio, generate thumbnails.
- **Phase 2** (done): Whisper transcription + diarization + segment analysis.
- **Phase 3** (done): Clip extraction + Story Builder + Timeline rendering.

All three phases are fully implemented — backend services, API routers, and frontend UI.

### Frontend Milestones (all complete)

- **M1**: Library browser, item detail page, upload, Quick Job
- **M2**: Camera roll upload, mobile card layout, responsive ItemPage
- **M3**: Job history, download/share, retry, cancel + Mission Control LLM routing
- **M4**: Synced video player, clip builder, enhanced clip library
- **M5**: Story Builder UI, drag-and-drop timeline, clip preview, caption editor, render progress
- **M6**: Source management page, create clip from highlight, clip sorting + bulk delete, mobile nav reorganization

## Architecture Reference

See `ARCHITECTURE.md` for the full system design and all planned tables/APIs.
