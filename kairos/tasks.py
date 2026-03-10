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

        # ── Step 9: Note for Phase 4 ──────────────────────────────────────────
        if clip_rows:
            logger.info(
                "analysis_task: clip extraction task will be added in Phase 4 (%d clips pending)",
                len(clip_rows),
            )

    except Exception as exc:
        logger.exception("analysis_task: unexpected error for item %s", item_id)
    finally:
        db.close()
