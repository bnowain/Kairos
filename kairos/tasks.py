"""
Huey task definitions for Kairos.

Phase 1 tasks (acquisition + ingest):
  download_task  — runs in huey_light — calls downloader service, updates item status
  ingest_task    — runs in huey_light — extracts audio, generates thumbnail, updates status

Phase 2 tasks (GPU):
  transcribe_task — runs in huey_gpu — Whisper + diarization + alignment

Phase 3 tasks (GPU):
  analysis_task   — runs in huey_gpu — LLM + embedder + audio events + scoring
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


@huey_gpu.task()
def analysis_task(item_id: str):
    """
    Full analysis pipeline for one MediaItem (Phase 3).

    Pipeline:
    1.  Load all TranscriptionSegments for item (must have segments)
    2.  Run heuristic scorers (emotion + controversy) — fast, no GPU
    3.  Run embedder for topic segmentation (GPU if available)
    4.  Load audio_path and run audio_events detection (librosa, CPU)
    5.  Run LLM analyzer via Ollama (batched)
    6.  Run scorer.compute_composite_scores()
    7.  Write AnalysisScore rows to DB (one per segment per score_type)
    8.  Auto-create Clip rows for segments above AUTO_CLIP_THRESHOLD
    9.  Log summary: N segments scored, M clips auto-created
    """
    import json
    import uuid as _uuid

    from kairos.database import SessionLocal
    from kairos.models import AnalysisScore, Clip, MediaItem, TranscriptionSegment
    from kairos.config import BASE_DIR
    from kairos.services.analysis import (
        audio_events,
        controversy,
        embedder,
        emotion_scorer,
        llm_analyzer,
        scorer,
    )
    from kairos.services.analysis.scorer import AUTO_CLIP_THRESHOLD

    db = SessionLocal()
    try:
        # ── Step 1: Load item + segments ──────────────────────────────────────
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item:
            logger.error("analysis_task: item_id %s not found", item_id)
            return

        raw_segments = (
            db.query(TranscriptionSegment)
            .filter(TranscriptionSegment.item_id == item_id)
            .order_by(TranscriptionSegment.start_ms)
            .all()
        )
        if not raw_segments:
            logger.error("analysis_task: item %s has no transcription segments", item_id)
            return

        # Convert ORM rows to dicts for the analysis pipeline
        segments = [
            {
                "segment_id":   s.segment_id,
                "item_id":      s.item_id,
                "speaker_label": s.speaker_label,
                "start_ms":     s.start_ms,
                "end_ms":       s.end_ms,
                "segment_text": s.segment_text,
            }
            for s in raw_segments
        ]
        logger.info("analysis_task: loaded %d segments for item %s", len(segments), item_id)

        # ── Step 2: Heuristic scorers (fast, CPU, no deps) ────────────────────
        segments = emotion_scorer.score_emotion(segments)
        segments = controversy.score_controversy(segments)
        logger.info("analysis_task: heuristic scoring complete for item %s", item_id)

        # ── Step 3: Embedder (GPU if available) ───────────────────────────────
        try:
            segments = embedder.score_topic_coherence(segments)
            logger.info("analysis_task: topic coherence scoring complete for item %s", item_id)
        except Exception as exc:
            logger.warning(
                "analysis_task: embedder failed (%s) — defaulting topic_coherence to 0.5", exc
            )
            for seg in segments:
                seg.setdefault("topic_coherence_score", 0.5)

        # ── Step 4: Audio events (librosa, CPU) ───────────────────────────────
        reaction_events: list[dict] = []
        if item.audio_path:
            audio_path_abs = str(BASE_DIR / item.audio_path)
            try:
                reaction_events = audio_events.detect_reactions(audio_path_abs)
                segments = audio_events.score_segments_by_reactions(segments, reaction_events)
                logger.info(
                    "analysis_task: audio events: %d reactions for item %s",
                    len(reaction_events), item_id,
                )
            except Exception as exc:
                logger.warning(
                    "analysis_task: audio_events failed (%s) — defaulting audience_reaction to 0.0",
                    exc,
                )
                for seg in segments:
                    seg.setdefault("audience_reaction_score", 0.0)
        else:
            logger.warning(
                "analysis_task: item %s has no audio_path — skipping audio event detection",
                item_id,
            )
            for seg in segments:
                seg.setdefault("audience_reaction_score", 0.0)

        # ── Step 5: LLM analysis via Ollama ───────────────────────────────────
        llm_scores: list[dict] = []
        try:
            llm_scores = llm_analyzer.analyze_segments(
                segments, item_title=item.item_title or ""
            )
            logger.info("analysis_task: LLM scoring complete for item %s", item_id)
        except Exception as exc:
            logger.warning(
                "analysis_task: LLM analyzer failed (%s) — using default scores", exc
            )
            llm_scores = [
                {
                    "segment_id":        seg["segment_id"],
                    "virality_score":    0.0,
                    "hook_score":        0.0,
                    "emotional_score":   0.0,
                    "controversy_score": 0.0,
                    "highlight_reason":  "",
                    "is_hook_candidate": False,
                }
                for seg in segments
            ]

        # ── Step 6: Composite score aggregation ───────────────────────────────
        scored_segments = scorer.compute_composite_scores(
            segments=segments,
            llm_scores=llm_scores,
            reaction_scores=[],   # already embedded in segment dicts
            emotion_scores=[],    # already embedded in segment dicts
            controversy_scores=[], # already embedded in segment dicts
            embedding_scores=[],  # already embedded in segment dicts
        )
        logger.info(
            "analysis_task: composite scoring complete — %d segments for item %s",
            len(scored_segments), item_id,
        )

        # ── Step 7: Write AnalysisScore rows to DB ────────────────────────────
        # Delete any existing scores for this item first (re-analysis support)
        db.query(AnalysisScore).filter(AnalysisScore.item_id == item_id).delete(
            synchronize_session=False
        )
        db.commit()

        now_ts = _now()
        from kairos.config import OLLAMA_MODEL

        score_rows = []

        # Build segment_id → llm_score map
        llm_map = {s.get("segment_id", ""): s for s in llm_scores}

        for seg in scored_segments:
            seg_id = seg["segment_id"]
            llm = llm_map.get(seg_id, {})

            # virality (LLM)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "virality",
                score_value  = float(llm.get("virality_score", 0.0)),
                score_reason = llm.get("highlight_reason", ""),
                scorer_model = OLLAMA_MODEL,
                created_at   = now_ts,
            ))

            # hook (LLM)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "hook",
                score_value  = float(llm.get("hook_score", 0.0)),
                score_reason = None,
                scorer_model = OLLAMA_MODEL,
                created_at   = now_ts,
            ))

            # emotional (LLM)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "emotional",
                score_value  = float(llm.get("emotional_score", 0.0)),
                score_reason = None,
                scorer_model = OLLAMA_MODEL,
                created_at   = now_ts,
            ))

            # controversy (LLM)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "controversy",
                score_value  = float(llm.get("controversy_score", 0.0)),
                score_reason = None,
                scorer_model = OLLAMA_MODEL,
                created_at   = now_ts,
            ))

            # audience_reaction (audio events)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "audience_reaction",
                score_value  = float(seg.get("audience_reaction_score", 0.0)),
                score_reason = None,
                scorer_model = "librosa",
                created_at   = now_ts,
            ))

            # topic_coherence (embedder)
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "topic_coherence",
                score_value  = float(seg.get("topic_coherence_score", 0.5)),
                score_reason = None,
                scorer_model = "all-MiniLM-L6-v2",
                created_at   = now_ts,
            ))

            # composite
            score_rows.append(AnalysisScore(
                score_id     = str(_uuid.uuid4()),
                item_id      = item_id,
                segment_id   = seg_id,
                score_type   = "composite",
                score_value  = float(seg["composite_virality_score"]),
                score_reason = llm.get("highlight_reason", ""),
                scorer_model = "kairos-scorer-v1",
                created_at   = now_ts,
            ))

        db.bulk_save_objects(score_rows)
        db.commit()
        logger.info(
            "analysis_task: inserted %d score rows for item %s",
            len(score_rows), item_id,
        )

        # ── Step 8: Auto-create Clip rows for segments above threshold ─────────
        clip_candidates = [
            seg for seg in scored_segments if seg.get("is_auto_clip_candidate")
        ]

        clip_rows = []
        for seg in clip_candidates:
            duration_ms = max(0, seg["end_ms"] - seg["start_ms"])
            clip_rows.append(Clip(
                clip_id        = str(_uuid.uuid4()),
                item_id        = item_id,
                clip_title     = None,
                start_ms       = seg["start_ms"],
                end_ms         = seg["end_ms"],
                duration_ms    = duration_ms,
                clip_file_path = None,
                clip_thumb_path= None,
                virality_score = seg["composite_virality_score"],
                clip_status    = "pending",
                clip_source    = "ai",
                speaker_label  = seg.get("speaker_label"),
                clip_transcript= seg.get("segment_text", ""),
                error_msg      = None,
                created_at     = now_ts,
                updated_at     = now_ts,
            ))

        if clip_rows:
            db.bulk_save_objects(clip_rows)
            db.commit()

        logger.info(
            "analysis_task: completed for item %s — %d segments scored, %d clips auto-created",
            item_id, len(scored_segments), len(clip_rows),
        )

        # ── Step 9: Enqueue extraction for auto-created clips (Phase 4) ──────
        if clip_rows:
            from kairos.tasks import extract_clip_task as _extract_clip_task
            for clip_row in clip_rows:
                _extract_clip_task(clip_row.clip_id)
            logger.info(
                "analysis_task: enqueued extract_clip_task for %d auto-created clip(s)",
                len(clip_rows),
            )

    except Exception as exc:
        logger.exception("analysis_task: unexpected error for item %s", item_id)
    finally:
        db.close()


# ── Phase 4: Clip extraction tasks ────────────────────────────────────────────

@huey_light.task()
def extract_clip_task(clip_id: str, remove_silence: bool = False):
    """
    Extract a single clip to disk.

    Pipeline:
    1. Load Clip from DB, verify item exists and has file_path
    2. Set clip_status = "extracting"
    3. Build output path: media/clips/{item_id}/{clip_id}.mp4
    4. Call extractor.extract_clip(source_path, output_path, start_ms, end_ms)
    5. If remove_silence=True: call silence_remover.remove_silence(output, silenced_output)
    6. Generate thumbnail at media/thumbs/clips/{clip_id}.jpg
    7. Update clip: clip_file_path, clip_thumb_path, clip_status="ready", duration_ms
    8. On error: clip_status="error", error_msg=str(exc)
    """
    from kairos.database import SessionLocal
    from kairos.models import Clip, MediaItem
    from kairos.config import BASE_DIR
    from kairos.services.clip_engine import extractor, silence_remover

    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
        if not clip:
            logger.error("extract_clip_task: clip_id %s not found", clip_id)
            return

        item = db.query(MediaItem).filter(MediaItem.item_id == clip.item_id).first()
        if not item:
            logger.error(
                "extract_clip_task: MediaItem %s not found for clip %s",
                clip.item_id, clip_id,
            )
            clip.clip_status = "error"
            clip.error_msg   = f"MediaItem {clip.item_id} not found"
            clip.updated_at  = _now()
            db.commit()
            return

        if not item.file_path:
            logger.error(
                "extract_clip_task: MediaItem %s has no file_path (clip %s)",
                item.item_id, clip_id,
            )
            clip.clip_status = "error"
            clip.error_msg   = "MediaItem has no file_path"
            clip.updated_at  = _now()
            db.commit()
            return

        # Mark as extracting
        clip.clip_status = "extracting"
        clip.updated_at  = _now()
        db.commit()

        source_path = str(BASE_DIR / item.file_path)

        # Output: media/clips/{item_id}/{clip_id}.mp4  (relative to BASE_DIR)
        rel_clip_path   = f"media/clips/{item.item_id}/{clip_id}.mp4"
        abs_clip_path   = str(BASE_DIR / rel_clip_path)

        logger.info(
            "extract_clip_task: extracting clip %s  [%dms – %dms]  source=%s",
            clip_id, clip.start_ms, clip.end_ms, source_path,
        )

        extract_result = extractor.extract_clip(
            source_path=source_path,
            output_path=abs_clip_path,
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
        )

        if not extract_result["success"]:
            raise RuntimeError(extract_result["error"] or "extract_clip returned failure")

        final_clip_path     = abs_clip_path
        final_rel_clip_path = rel_clip_path

        # Silence removal (optional)
        if remove_silence:
            silenced_rel  = f"media/clips/{item.item_id}/{clip_id}_silenced.mp4"
            silenced_abs  = str(BASE_DIR / silenced_rel)
            sr_result     = silence_remover.remove_silence(
                input_path=abs_clip_path,
                output_path=silenced_abs,
            )
            if sr_result["success"] and sr_result["silence_removed_ms"] > 0:
                # Replace the original clip with the silence-removed version
                try:
                    import os
                    os.replace(silenced_abs, abs_clip_path)
                    logger.info(
                        "extract_clip_task: silence removal saved %dms for clip %s",
                        sr_result["silence_removed_ms"], clip_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "extract_clip_task: could not replace clip with silenced version: %s", exc
                    )
            else:
                # Clean up unused silenced file if it was created
                try:
                    from pathlib import Path as _Path
                    _Path(silenced_abs).unlink(missing_ok=True)
                except Exception:
                    pass

        # Refresh actual duration from disk
        from kairos.services.clip_engine.extractor import _get_clip_duration_ms
        duration_ms = _get_clip_duration_ms(final_clip_path)
        if duration_ms <= 0:
            duration_ms = clip.end_ms - clip.start_ms

        # Thumbnail: media/thumbs/clips/{clip_id}.jpg  (relative to BASE_DIR)
        rel_thumb_path = f"media/thumbs/clips/{clip_id}.jpg"
        abs_thumb_path = str(BASE_DIR / rel_thumb_path)

        thumb_ok = extractor.generate_clip_thumbnail(
            clip_path=final_clip_path,
            thumb_path=abs_thumb_path,
        )

        # Persist results
        clip.clip_file_path  = final_rel_clip_path
        clip.clip_thumb_path = rel_thumb_path if thumb_ok else None
        clip.duration_ms     = duration_ms
        clip.clip_status     = "ready"
        clip.error_msg       = None
        clip.updated_at      = _now()
        db.commit()

        logger.info(
            "extract_clip_task: completed for clip %s — duration=%dms  thumb=%s",
            clip_id, duration_ms, "yes" if thumb_ok else "no",
        )

    except Exception as exc:
        logger.exception("extract_clip_task: unexpected error for clip %s", clip_id)
        try:
            clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
            if clip:
                clip.clip_status = "error"
                clip.error_msg   = str(exc)[:1000]
                clip.updated_at  = _now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@huey_light.task()
def batch_extract_task(item_id: str = None):
    """
    Enqueue extract_clip_task for all pending clips.
    If item_id is provided, only for that item.
    """
    from kairos.database import SessionLocal
    from kairos.services.clip_engine.batch_clipper import enqueue_pending_clips

    db = SessionLocal()
    try:
        count = enqueue_pending_clips(db, item_id=item_id)
        logger.info(
            "batch_extract_task: enqueued %d clip extraction task(s)%s",
            count,
            f" for item {item_id}" if item_id else "",
        )
    except Exception as exc:
        logger.exception("batch_extract_task: unexpected error")
    finally:
        db.close()


# ── Phase 5: Story Builder tasks ───────────────────────────────────────────────

@huey_light.task()
def build_story_task(
    item_ids: list,
    template_id: str,
    name: str,
    aspect_ratio: str = "16:9",
    pacing: str = None,
    min_score: float = 0.5,
    project_id: str = None,
):
    """
    Async story builder task — same pipeline as POST /api/stories/generate
    but for large clip pools that might be slow to assemble.
    Returns timeline_id when done.
    """
    from kairos.database import SessionLocal
    from kairos.services.story_builder import (
        clip_ranker, slot_assigner, flow_enforcer, timeline_builder
    )
    from kairos.services.story_builder.template_loader import load_template

    db = SessionLocal()
    try:
        logger.info(
            "build_story_task: building story '%s' from %d item(s), template='%s'",
            name, len(item_ids), template_id,
        )

        # Load template
        template = load_template(template_id)

        # Load all ready clips with scores
        clips = clip_ranker.load_clips_with_scores(db, item_ids=item_ids)
        logger.info("build_story_task: loaded %d ready clips", len(clips))

        # Filter by min_score
        if min_score > 0:
            clips = [
                c for c in clips
                if (c.get("scores", {}).get("composite", 0.0) or 0.0) >= min_score
                or (c.get("virality_score", 0.0) or 0.0) >= min_score
            ]
            logger.info(
                "build_story_task: %d clips pass min_score=%.2f", len(clips), min_score
            )

        # Assign slots
        assignment = slot_assigner.assign_slots(
            template=template,
            clips=clips,
            pacing_override=pacing,
        )

        # Enforce flow
        elements = flow_enforcer.enforce_flow(
            slot_assignments=assignment["slot_assignments"],
            template=template,
            pacing=pacing,
        )

        # Build and persist timeline
        result = timeline_builder.build_timeline(
            db=db,
            name=name,
            template_id=template_id,
            elements=elements,
            aspect_ratio=aspect_ratio,
            project_id=project_id,
        )

        logger.info(
            "build_story_task: created timeline %s — %d elements, %dms",
            result["timeline_id"],
            result["element_count"],
            result["target_duration_ms"] or 0,
        )
        return result["timeline_id"]

    except Exception as exc:
        logger.exception("build_story_task: unexpected error for story '%s'", name)
        raise
    finally:
        db.close()


# ── Phase 6: Render task ───────────────────────────────────────────────────────

@huey_gpu.task()
def render_task(render_id: str):
    """
    Full render pipeline for one RenderJob.

    Steps:
    1. Load RenderJob + Timeline + TimelineElements from DB
    2. Build clip_file_map: {clip_id: abs_path} — skip missing files with warning
    3. If apply_captions: generate ASS file
    4. If reframe_aspect_ratio: compute crop_params per clip via aspect_ratio services
    5. Call preview_renderer or final_renderer based on quality
    6. Update RenderJob via queue_manager (complete or fail)
    7. Update Timeline.timeline_status = 'done'

    Render output path: media/renders/{timeline_id}/{render_id}_{quality}.mp4
    """
    import json as _json

    from kairos.database import SessionLocal
    from kairos.models import Clip, RenderJob, Timeline, TimelineElement
    from kairos.config import BASE_DIR
    from kairos.services.renderer.queue_manager import (
        start_render_job, complete_render_job, fail_render_job,
    )

    db = SessionLocal()
    try:
        # ── Step 1: Load job + timeline + elements ────────────────────────────
        job = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
        if not job:
            logger.error("render_task: render_id %s not found", render_id)
            return

        timeline = db.query(Timeline).filter(Timeline.timeline_id == job.timeline_id).first()
        if not timeline:
            logger.error("render_task: timeline %s not found for render %s", job.timeline_id, render_id)
            fail_render_job(db, render_id, f"Timeline {job.timeline_id} not found")
            return

        start_render_job(db, render_id)

        # Parse render_params JSON
        render_params: dict = {}
        if job.render_params:
            try:
                render_params = _json.loads(job.render_params)
            except Exception:
                logger.warning("render_task: could not parse render_params for %s", render_id)

        apply_captions = render_params.get("apply_captions", True)
        caption_style_id = render_params.get("caption_style_id")
        reframe_aspect_ratio = render_params.get("reframe_aspect_ratio")

        # Load timeline elements ordered by position
        elements = (
            db.query(TimelineElement)
            .filter(TimelineElement.timeline_id == job.timeline_id)
            .order_by(TimelineElement.position)
            .all()
        )
        elements_dicts = [
            {
                "element_id": e.element_id,
                "element_type": e.element_type,
                "position": e.position,
                "start_ms": e.start_ms,
                "duration_ms": e.duration_ms,
                "clip_id": e.clip_id,
                "element_params": e.element_params,
            }
            for e in elements
        ]

        # ── Step 2: Build clip_file_map ───────────────────────────────────────
        clip_ids = [e["clip_id"] for e in elements_dicts if e.get("clip_id")]
        clips = db.query(Clip).filter(Clip.clip_id.in_(clip_ids)).all() if clip_ids else []

        clip_file_map: dict[str, str] = {}
        for clip in clips:
            if clip.clip_file_path:
                abs_path = str(BASE_DIR / clip.clip_file_path)
                from pathlib import Path as _Path
                if _Path(abs_path).exists():
                    clip_file_map[clip.clip_id] = abs_path
                else:
                    logger.warning(
                        "render_task: clip file missing for clip_id=%s path=%s",
                        clip.clip_id, abs_path,
                    )
            else:
                logger.warning("render_task: clip_id=%s has no clip_file_path", clip.clip_id)

        if not clip_file_map:
            fail_render_job(db, render_id, "No clip files found — all clips missing from disk")
            return

        # ── Step 3: Generate captions (optional) ─────────────────────────────
        caption_ass_path: str = None
        if apply_captions:
            try:
                from kairos.models import CaptionStyle
                from kairos.services.caption_engine.generator import generate_timeline_captions
                from kairos.services.caption_engine.styler import get_default_style, write_ass_file
                from kairos.services.aspect_ratio.reframer import RESOLUTIONS

                style_dict = get_default_style()
                if caption_style_id:
                    style_obj = db.query(CaptionStyle).filter(
                        CaptionStyle.style_id == caption_style_id
                    ).first()
                    if style_obj:
                        style_dict = {
                            "font_name": style_obj.font_name,
                            "font_size": style_obj.font_size,
                            "font_color": style_obj.font_color,
                            "outline_color": style_obj.outline_color,
                            "outline_width": style_obj.outline_width,
                            "shadow": style_obj.shadow,
                            "animation_type": style_obj.animation_type,
                            "position": style_obj.position,
                        }

                captions = generate_timeline_captions(
                    db=db,
                    timeline_elements=elements_dicts,
                    clip_file_map=clip_file_map,
                    style=style_dict,
                )

                if captions:
                    captions_dir = BASE_DIR / "media" / "captions"
                    captions_dir.mkdir(parents=True, exist_ok=True)
                    ass_file = str(captions_dir / f"{render_id}.ass")
                    resolution = RESOLUTIONS.get(timeline.aspect_ratio or "16:9", (1920, 1080))
                    write_ass_file(captions, style_dict, ass_file, resolution=resolution)
                    caption_ass_path = ass_file
                    logger.info("render_task: generated %d caption cues — %s", len(captions), ass_file)
                else:
                    logger.info("render_task: no captions generated (no transcription segments)")

            except Exception as exc:
                logger.warning("render_task: caption generation failed (non-fatal) — %s", exc)
                caption_ass_path = None

        # ── Step 4: Compute crop_params per clip (optional) ──────────────────
        crop_params: dict = None
        if reframe_aspect_ratio:
            try:
                from kairos.services.aspect_ratio.tracker import compute_tracking_crop, get_median_crop

                crop_params = {}
                for clip in clips:
                    if clip.clip_id not in clip_file_map:
                        continue
                    clip_path = clip_file_map[clip.clip_id]
                    tracking = compute_tracking_crop(
                        clip_path=clip_path,
                        target_ratio=reframe_aspect_ratio,
                    )
                    median_crop = get_median_crop(tracking)
                    crop_params[clip.clip_id] = median_crop
                    logger.debug(
                        "render_task: crop for clip %s → %s", clip.clip_id, median_crop
                    )
                logger.info("render_task: computed crop_params for %d clips", len(crop_params))
            except Exception as exc:
                logger.warning("render_task: crop_params computation failed (non-fatal) — %s", exc)
                crop_params = None

        # ── Step 5: Render ────────────────────────────────────────────────────
        aspect_ratio = timeline.aspect_ratio or "16:9"
        output_dir = BASE_DIR / "media" / "renders" / job.timeline_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{render_id}_{job.render_quality}.mp4")

        if job.render_quality == "preview":
            from kairos.services.renderer.preview_renderer import render_preview
            result = render_preview(
                timeline_elements=elements_dicts,
                clip_file_map=clip_file_map,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                caption_ass_path=caption_ass_path,
            )
        else:
            from kairos.services.renderer.final_renderer import render_final
            result = render_final(
                timeline_elements=elements_dicts,
                clip_file_map=clip_file_map,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                caption_ass_path=caption_ass_path,
                crop_params=crop_params,
            )

        # ── Step 6: Update RenderJob ──────────────────────────────────────────
        if result["success"]:
            encoder_used = result.get("encoder_used", "libx264")
            if job.render_quality == "preview":
                encoder_used = "libx264"
            complete_render_job(db, render_id, output_path, encoder_used)
            logger.info(
                "render_task: completed render %s — %s encoder=%s duration=%dms",
                render_id, output_path, encoder_used, result.get("duration_ms", 0),
            )
        else:
            error_msg = result.get("error", "Unknown render error")
            fail_render_job(db, render_id, error_msg)
            logger.error("render_task: render %s failed — %s", render_id, error_msg)
            return

        # ── Step 7: Update Timeline status ────────────────────────────────────
        tl = db.query(Timeline).filter(Timeline.timeline_id == job.timeline_id).first()
        if tl:
            tl.timeline_status = "done"
            tl.updated_at = _now()
            db.commit()

    except Exception as exc:
        logger.exception("render_task: unexpected error for render %s", render_id)
        try:
            fail_render_job(db, render_id, str(exc)[:1000])
        except Exception:
            pass
    finally:
        db.close()
