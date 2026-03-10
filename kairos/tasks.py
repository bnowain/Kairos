"""
Huey task definitions for Kairos Phase 1.

Phase 1 tasks (acquisition + ingest only):
  download_task  — runs in huey_light — calls downloader service, updates item status
  ingest_task    — runs in huey_light — extracts audio, generates thumbnail, updates status

GPU tasks (Phase 2+) will be added to huey_gpu.
"""

import logging
from datetime import datetime

from kairos.worker import huey_gpu, huey_light  # noqa: F401 (huey_gpu imported for future use)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


@huey_light.task()
def download_task(url: str, item_id: str, source_id: str | None = None):
    """
    Download a video from a URL.

    Updates the MediaItem's status at each stage:
      queued → downloading → downloaded (then enqueues ingest_task)
      or → error on failure.
    """
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from kairos.services.acquisition.downloader import download_video
    from kairos.config import MEDIA_LIBRARY_ROOT

    db = SessionLocal()
    try:
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item:
            logger.error("download_task: item_id %s not found", item_id)
            return

        # Mark as downloading
        item.item_status = "downloading"
        item.updated_at = _now()
        db.commit()

        logger.info("download_task: starting download for item %s — %s", item_id, url)

        try:
            result = download_video(url=url, media_library_root=MEDIA_LIBRARY_ROOT)
        except Exception as exc:
            logger.exception("download_task: download_video raised for %s", url)
            item.item_status = "error"
            item.error_msg = str(exc)[:1000]
            item.updated_at = _now()
            db.commit()
            return

        # Populate item with download results
        meta = result.get("metadata", {})
        item.file_path        = result.get("file_path")
        item.item_title       = meta.get("title") or item.item_title
        item.item_channel     = meta.get("channel") or meta.get("uploader") or item.item_channel
        item.item_description = meta.get("description") or item.item_description
        item.published_at     = meta.get("published_at") or item.published_at
        item.duration_seconds = meta.get("duration") or item.duration_seconds
        item.platform_video_id = meta.get("platform_video_id") or item.platform_video_id
        item.platform         = meta.get("platform") or item.platform
        item.has_captions     = 1 if result.get("caption_path") else 0
        item.caption_source   = "online" if result.get("caption_path") else None
        item.item_status      = "downloaded"
        item.updated_at       = _now()
        db.commit()

        logger.info("download_task: completed for item %s — file: %s", item_id, item.file_path)

        # Enqueue ingest pipeline
        ingest_task(item_id)

    except Exception as exc:
        logger.exception("download_task: unexpected error for item %s", item_id)
        try:
            item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
            if item:
                item.item_status = "error"
                item.error_msg = str(exc)[:1000]
                item.updated_at = _now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@huey_gpu.task()
def transcribe_task(item_id: str):
    """
    GPU transcription + diarization + alignment pipeline.

    Stages:
      1. Load item, verify audio_path exists
      2. Create/update TranscriptionJob → status="running"
      3. Transcribe with faster-whisper
      4. Diarize with pyannote (graceful fallback if HF_TOKEN missing)
      5. Align words to speaker turns
      6. Delete any existing segments for this item
      7. Batch-insert TranscriptionSegments
      8. Export SRT + VTT + JSON to media/exports/{item_id}/
      9. Update job → status="done"
      10. Update item.caption_source if it was None
    """
    import json
    import uuid

    from kairos.database import SessionLocal
    from kairos.models import MediaItem, TranscriptionJob, TranscriptionSegment
    from kairos.config import BASE_DIR
    from kairos.services.transcription import transcriber, diarizer, aligner, exporter

    db = SessionLocal()
    job = None
    try:
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item:
            logger.error("transcribe_task: item_id %s not found", item_id)
            return

        if not item.audio_path:
            logger.error("transcribe_task: item %s has no audio_path", item_id)
            return

        audio_path = str(BASE_DIR / item.audio_path)

        # Find or create the TranscriptionJob for this run
        job = (
            db.query(TranscriptionJob)
            .filter(
                TranscriptionJob.item_id == item_id,
                TranscriptionJob.job_status.in_(["queued", "running"]),
            )
            .order_by(TranscriptionJob.created_at.desc())
            .first()
        )

        if job is None:
            # Task was enqueued without a prior API call (e.g. direct invocation)
            from kairos.config import WHISPER_MODEL
            job = TranscriptionJob(
                job_id        = str(uuid.uuid4()),
                item_id       = item_id,
                whisper_model = WHISPER_MODEL,
                language      = "en",
                job_status    = "queued",
                created_at    = _now(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

        job.job_status  = "running"
        job.started_at  = _now()
        db.commit()

        logger.info("transcribe_task: starting for item %s (job %s)", item_id, job.job_id)

        # ── Step 3: Transcribe ─────────────────────────────────────────────────
        whisper_segments = transcriber.transcribe(audio_path)
        logger.info(
            "transcribe_task: got %d whisper segments for item %s",
            len(whisper_segments), item_id,
        )

        # ── Step 4: Diarize (graceful fallback) ───────────────────────────────
        diarization_turns: list[dict] = []
        try:
            diarization_turns = diarizer.diarize(audio_path)
            logger.info(
                "transcribe_task: got %d diarization turns for item %s",
                len(diarization_turns), item_id,
            )
        except EnvironmentError as exc:
            logger.warning(
                "transcribe_task: diarization skipped (HF_TOKEN missing) — %s", exc
            )
        except Exception as exc:
            logger.warning(
                "transcribe_task: diarization failed (non-fatal) — %s", exc
            )

        # ── Step 5: Align ──────────────────────────────────────────────────────
        aligned = aligner.align(whisper_segments, diarization_turns)
        logger.info(
            "transcribe_task: %d aligned segments for item %s",
            len(aligned), item_id,
        )

        # ── Step 6: Delete existing segments for this item ────────────────────
        deleted = (
            db.query(TranscriptionSegment)
            .filter(TranscriptionSegment.item_id == item_id)
            .delete(synchronize_session=False)
        )
        if deleted:
            logger.info(
                "transcribe_task: deleted %d existing segments for item %s",
                deleted, item_id,
            )
        db.commit()

        # ── Step 7: Batch-insert new segments ─────────────────────────────────
        now_ts = _now()
        segment_rows = []
        for seg in aligned:
            words = seg.get("words", [])
            segment_rows.append(TranscriptionSegment(
                segment_id      = str(uuid.uuid4()),
                item_id         = item_id,
                job_id          = job.job_id,
                speaker_label   = seg.get("speaker"),
                start_ms        = int(seg["start"] * 1000),
                end_ms          = int(seg["end"]   * 1000),
                segment_text    = seg.get("text", ""),
                word_timestamps = json.dumps(words),
                avg_logprob     = seg.get("avg_logprob"),
                no_speech_prob  = seg.get("no_speech_prob"),
                created_at      = now_ts,
            ))

        db.bulk_save_objects(segment_rows)
        db.commit()
        logger.info(
            "transcribe_task: inserted %d segments for item %s",
            len(segment_rows), item_id,
        )

        # ── Step 8: Export SRT + VTT + JSON ───────────────────────────────────
        export_dir = BASE_DIR / "media" / "exports" / item_id
        export_dir.mkdir(parents=True, exist_ok=True)

        exporter.export_srt( aligned, str(export_dir / "transcript.srt"))
        exporter.export_vtt( aligned, str(export_dir / "transcript.vtt"))
        exporter.export_json(aligned, str(export_dir / "transcript.json"))

        # ── Step 9: Update job → done ──────────────────────────────────────────
        job.job_status   = "done"
        job.completed_at = _now()
        db.commit()

        # ── Step 10: Update item caption_source if it was None ─────────────────
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if item and item.caption_source is None:
            item.caption_source = "whisper"
            item.has_captions   = 1
            item.updated_at     = _now()
            db.commit()

        logger.info(
            "transcribe_task: completed for item %s — %d segments",
            item_id, len(segment_rows),
        )

    except Exception as exc:
        logger.exception("transcribe_task: unexpected error for item %s", item_id)
        try:
            if job is not None:
                job.job_status = "error"
                job.error_msg  = str(exc)[:1000]
                job.completed_at = _now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@huey_light.task()
def ingest_task(item_id: str):
    """
    Run the ingest pipeline for a downloaded MediaItem.

    Stages:
      downloaded → ingesting → ready
      or → error on failure.

    The pipeline:
      1. Extract audio WAV (FFmpeg)
      2. Generate thumbnail (FFmpeg)
      3. Compute SHA-256 file hash
      4. Update item record with all paths and set status = ready
    """
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from kairos.services.ingest.pipeline import run_ingest_pipeline

    db = SessionLocal()
    try:
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item:
            logger.error("ingest_task: item_id %s not found", item_id)
            return

        if not item.file_path:
            logger.error("ingest_task: item %s has no file_path — cannot ingest", item_id)
            item.item_status = "error"
            item.error_msg = "No file_path — download may have failed silently"
            item.updated_at = _now()
            db.commit()
            return

        item.item_status = "ingesting"
        item.updated_at = _now()
        db.commit()

        logger.info("ingest_task: starting pipeline for item %s", item_id)

        try:
            ingest_result = run_ingest_pipeline(item_id=item_id, file_path=item.file_path)
        except Exception as exc:
            logger.exception("ingest_task: pipeline raised for item %s", item_id)
            item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
            if item:
                item.item_status = "error"
                item.error_msg = str(exc)[:1000]
                item.updated_at = _now()
                db.commit()
            return

        # Update item with ingest results
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if item:
            item.audio_path    = ingest_result.get("audio_path")
            item.thumb_path    = ingest_result.get("thumb_path")
            item.file_hash     = ingest_result.get("file_hash")
            item.item_status   = "ready"
            item.updated_at    = _now()
            db.commit()

        logger.info("ingest_task: completed for item %s — status=ready", item_id)

    except Exception as exc:
        logger.exception("ingest_task: unexpected error for item %s", item_id)
        try:
            item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
            if item:
                item.item_status = "error"
                item.error_msg = str(exc)[:1000]
                item.updated_at = _now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
