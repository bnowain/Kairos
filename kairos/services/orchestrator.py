"""
QuickJob orchestrator — background threading.Thread that chains the full pipeline.

Stage flow:
  queued       → thread starts
  downloading  → download_task enqueued for each URL; waits for all items to reach 'ready'
  transcribing → TranscriptionJob created + transcribe_task enqueued per item;
                 waits for all jobs to reach 'done'
  analyzing    → analysis_task enqueued per item; waits for analysis_scores to appear;
                 then generates AI clips for each item
  generating   → story_builder services called synchronously; timeline created
  rendering    → create_render_job + render_task enqueued; waits for render 'done'
  done         → output_path set
  error        → any unhandled exception

Polling interval: 5 s.  Stage timeout: 30 min.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 5        # seconds between DB polls
_STAGE_TIMEOUT = 1800     # 30 minutes per stage


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _set_stage(db, job, status: str, label: str, progress: int) -> None:
    job.job_status  = status
    job.stage_label = label
    job.progress    = progress
    job.updated_at  = _now()
    db.commit()
    logger.info("QuickJob %s → %s (%d%%)", job.job_id, status, progress)


def _fail(db, job, msg: str) -> None:
    job.job_status = "error"
    job.error_msg  = msg[:2000]
    job.updated_at = _now()
    db.commit()
    logger.error("QuickJob %s failed: %s", job.job_id, msg)


def _poll_until(condition_fn, timeout: int = _STAGE_TIMEOUT) -> bool:
    """Poll condition_fn() every _POLL_INTERVAL seconds until True or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition_fn():
            return True
        time.sleep(_POLL_INTERVAL)
    return False


# ── Stage helpers ─────────────────────────────────────────────────────────────

def _run_downloading(db, job, item_ids: list[str]) -> bool:
    """Wait until all items reach item_status='ready'."""
    from kairos.models import MediaItem

    def all_ready() -> bool:
        db.expire_all()
        items = db.query(MediaItem).filter(MediaItem.item_id.in_(item_ids)).all()
        statuses = {i.item_status for i in items}
        if "error" in statuses:
            return True  # let caller detect the error items
        return all(i.item_status == "ready" for i in items)

    ok = _poll_until(all_ready)
    if not ok:
        return False

    # Check for errored items
    from kairos.models import MediaItem
    items = db.query(MediaItem).filter(MediaItem.item_id.in_(item_ids)).all()
    error_items = [i for i in items if i.item_status == "error"]
    if error_items:
        msgs = "; ".join(f"{i.item_id}: {i.error_msg}" for i in error_items)
        _fail(db, job, f"Download failed for {len(error_items)} item(s): {msgs}")
        return False

    return True


def _run_transcribing(db, job, item_ids: list[str]) -> Optional[list[str]]:
    """
    Create TranscriptionJob rows + enqueue transcribe_task for each item.
    Returns list of job_ids, or None on fatal error.
    """
    from kairos.models import MediaItem, TranscriptionJob
    from kairos.tasks import transcribe_task

    tj_ids: list[str] = []
    for item_id in item_ids:
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item or not item.audio_path:
            _fail(db, job, f"Item {item_id} has no audio_path — ingest may have failed")
            return None

        # Skip if a job already exists (idempotent)
        existing = (
            db.query(TranscriptionJob)
            .filter(
                TranscriptionJob.item_id == item_id,
                TranscriptionJob.job_status.in_(["queued", "running", "done"]),
            )
            .first()
        )
        if existing:
            tj_ids.append(existing.job_id)
            continue

        tj_id = str(uuid.uuid4())
        tj = TranscriptionJob(
            job_id        = tj_id,
            item_id       = item_id,
            job_status    = "queued",
            created_at    = _now(),
        )
        db.add(tj)
        db.commit()

        try:
            transcribe_task(item_id, tj_id)
        except Exception as exc:
            _fail(db, job, f"Failed to enqueue transcribe_task for {item_id}: {exc}")
            return None

        tj_ids.append(tj_id)

    return tj_ids


def _wait_transcribing(db, job, tj_ids: list[str]) -> bool:
    from kairos.models import TranscriptionJob

    def all_done() -> bool:
        db.expire_all()
        jobs = db.query(TranscriptionJob).filter(TranscriptionJob.job_id.in_(tj_ids)).all()
        if any(j.job_status == "error" for j in jobs):
            return True
        return all(j.job_status == "done" for j in jobs)

    ok = _poll_until(all_done)
    if not ok:
        return False

    from kairos.models import TranscriptionJob
    jobs = db.query(TranscriptionJob).filter(TranscriptionJob.job_id.in_(tj_ids)).all()
    errored = [j for j in jobs if j.job_status == "error"]
    if errored:
        msgs = "; ".join(f"{j.item_id}: {j.error_msg}" for j in errored)
        _fail(db, job, f"Transcription failed: {msgs}")
        return False
    return True


def _run_analyzing(db, job, item_ids: list[str]) -> bool:
    """Enqueue analysis_task for each item, wait for scores to appear."""
    from kairos.models import AnalysisScore, TranscriptionSegment
    from kairos.tasks import analysis_task

    for item_id in item_ids:
        seg_count = (
            db.query(TranscriptionSegment)
            .filter(TranscriptionSegment.item_id == item_id)
            .count()
        )
        if seg_count == 0:
            logger.warning("QuickJob %s: item %s has no segments, skipping analysis", job.job_id, item_id)
            continue
        try:
            analysis_task(item_id)
        except Exception as exc:
            logger.warning("QuickJob %s: failed to enqueue analysis for %s: %s", job.job_id, item_id, exc)

    def has_scores() -> bool:
        db.expire_all()
        for item_id in item_ids:
            count = db.query(AnalysisScore).filter(AnalysisScore.item_id == item_id).count()
            if count > 0:
                return True
        return False

    # Wait for at least one item to have scores (analysis may be slow)
    _poll_until(has_scores, timeout=_STAGE_TIMEOUT)
    return True  # non-fatal if no scores — story builder will work with existing clips


def _generate_clips(db, item_ids: list[str]) -> None:
    """Generate AI clips for items that have scores but no ai clips yet."""
    from kairos.models import AnalysisScore, Clip, TranscriptionSegment
    import uuid as _uuid

    AUTO_CLIP_THRESHOLD = 0.6

    for item_id in item_ids:
        existing_clips = (
            db.query(Clip)
            .filter(Clip.item_id == item_id, Clip.clip_source == "ai")
            .count()
        )
        if existing_clips > 0:
            continue

        # Get top composite scores
        composite_scores = (
            db.query(AnalysisScore)
            .filter(
                AnalysisScore.item_id == item_id,
                AnalysisScore.score_type == "composite",
                AnalysisScore.score_value >= AUTO_CLIP_THRESHOLD,
            )
            .order_by(AnalysisScore.score_value.desc())
            .limit(20)
            .all()
        )

        for score in composite_scores:
            if not score.segment_id:
                continue
            seg = db.query(TranscriptionSegment).filter(
                TranscriptionSegment.segment_id == score.segment_id
            ).first()
            if not seg:
                continue

            clip = Clip(
                clip_id       = str(_uuid.uuid4()),
                item_id       = item_id,
                clip_title    = (seg.segment_text[:80] if seg.segment_text else None),
                start_ms      = seg.start_ms,
                end_ms        = seg.end_ms,
                duration_ms   = seg.end_ms - seg.start_ms,
                virality_score = score.score_value,
                clip_status   = "pending",
                clip_source   = "ai",
                speaker_label = seg.speaker_label,
                clip_transcript = seg.segment_text,
                created_at    = _now(),
                updated_at    = _now(),
            )
            db.add(clip)

        try:
            db.commit()
        except Exception as exc:
            logger.warning("_generate_clips: commit failed for %s: %s", item_id, exc)
            db.rollback()


def _run_generating(db, job, item_ids: list[str], template_id: str, aspect_ratio: str) -> Optional[str]:
    """
    Build a timeline via story_builder services.
    Returns timeline_id or None on error.
    """
    from kairos.models import Clip
    from kairos.services.story_builder import (
        clip_ranker, slot_assigner, flow_enforcer, timeline_builder, mashup_engine
    )
    from kairos.services.story_builder.template_loader import load_template

    # Verify at least one ready clip exists
    ready_clip = (
        db.query(Clip)
        .filter(Clip.item_id.in_(item_ids), Clip.clip_status.in_(["ready", "pending"]))
        .first()
    )
    if not ready_clip:
        _fail(db, job, "No clips found after analysis — cannot generate story")
        return None

    try:
        template = load_template(template_id)
    except FileNotFoundError:
        _fail(db, job, f"Template '{template_id}' not found")
        return None

    try:
        if len(item_ids) > 1:
            timeline_dict = mashup_engine.build_mashup(
                db=db,
                name="Quick Job",
                item_ids=item_ids,
                template_id=template_id,
                aspect_ratio=aspect_ratio,
            )
        else:
            clips = clip_ranker.load_clips_with_scores(db, item_ids=item_ids)
            assignment = slot_assigner.assign_slots(template=template, clips=clips)
            elements = flow_enforcer.enforce_flow(
                slot_assignments=assignment["slot_assignments"],
                template=template,
                pacing=None,
            )
            timeline_dict = timeline_builder.build_timeline(
                db=db,
                name="Quick Job",
                template_id=template_id,
                elements=elements,
                aspect_ratio=aspect_ratio,
            )
    except Exception as exc:
        _fail(db, job, f"Story generation failed: {exc}")
        return None

    return timeline_dict.get("timeline_id")


def _run_rendering(db, job, timeline_id: str, caption_style_id: Optional[str], aspect_ratio: str) -> Optional[str]:
    """
    Create a RenderJob + enqueue render_task.
    Returns render_id or None on error.
    """
    import json as _json
    from kairos.services.renderer.queue_manager import create_render_job

    render_params = _json.dumps({
        "apply_captions": caption_style_id is not None,
        "caption_style_id": caption_style_id,
        "reframe_aspect_ratio": aspect_ratio,
    })

    try:
        rjob = create_render_job(
            db=db,
            timeline_id=timeline_id,
            quality="final",
            render_params=render_params,
        )
    except Exception as exc:
        _fail(db, job, f"Failed to create render job: {exc}")
        return None

    try:
        from kairos.tasks import render_task
        render_task(rjob.render_id)
    except Exception as exc:
        rjob.render_status = "error"
        rjob.error_msg = str(exc)
        db.commit()
        _fail(db, job, f"Failed to enqueue render_task: {exc}")
        return None

    return rjob.render_id


def _wait_rendering(db, job, render_id: str) -> bool:
    from kairos.models import RenderJob

    def is_done() -> bool:
        db.expire_all()
        rjob = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
        return rjob is not None and rjob.render_status in ("done", "error")

    ok = _poll_until(is_done)
    if not ok:
        return False

    from kairos.models import RenderJob
    rjob = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
    if rjob and rjob.render_status == "error":
        _fail(db, job, f"Render failed: {rjob.error_msg}")
        return False
    return True


# ── Main orchestrator thread ───────────────────────────────────────────────────

def run_quick_job(job_id: str) -> None:
    """
    Background thread entry point.  Loads the QuickJob, runs all pipeline
    stages in sequence, and updates job_status + progress at each step.
    """
    from kairos.database import SessionLocal
    from kairos.models import MediaItem, QuickJob
    from kairos.tasks import download_task

    db = SessionLocal()
    try:
        job = db.query(QuickJob).filter(QuickJob.job_id == job_id).first()
        if not job:
            logger.error("run_quick_job: job_id %s not found", job_id)
            return

        urls: list[str] = json.loads(job.urls)
        template_id: str = job.template_id or "viral_reel"
        caption_style_id: Optional[str] = job.caption_style_id
        aspect_ratio: str = job.aspect_ratio

        # ── Stage 1: Download ─────────────────────────────────────────────────
        _set_stage(db, job, "downloading", f"Downloading {len(urls)} video(s)…", 5)

        item_ids: list[str] = []
        for url in urls:
            item_id = str(uuid.uuid4())
            now = _now()
            item = MediaItem(
                item_id    = item_id,
                platform   = "unknown",
                item_status = "queued",
                original_url = url,
                created_at = now,
                updated_at = now,
            )
            db.add(item)
            db.commit()

            try:
                download_task(url, item_id)
            except Exception as exc:
                _fail(db, job, f"Failed to enqueue download for {url}: {exc}")
                return

            item_ids.append(item_id)

        job.item_ids = json.dumps(item_ids)
        job.updated_at = _now()
        db.commit()

        if not _run_downloading(db, job, item_ids):
            return

        # ── Stage 2: Transcribe ───────────────────────────────────────────────
        _set_stage(db, job, "transcribing", "Transcribing audio…", 25)

        tj_ids = _run_transcribing(db, job, item_ids)
        if tj_ids is None:
            return

        if not _wait_transcribing(db, job, tj_ids):
            return

        # ── Stage 3: Analyze ──────────────────────────────────────────────────
        _set_stage(db, job, "analyzing", "Analyzing content…", 50)
        _run_analyzing(db, job, item_ids)

        _set_stage(db, job, "analyzing", "Generating clip candidates…", 60)
        _generate_clips(db, item_ids)

        # ── Stage 4: Generate story ───────────────────────────────────────────
        _set_stage(db, job, "generating", "Building story timeline…", 70)
        timeline_id = _run_generating(db, job, item_ids, template_id, aspect_ratio)
        if timeline_id is None:
            return

        job.timeline_id = timeline_id
        job.updated_at  = _now()
        db.commit()

        # ── Stage 5: Render ───────────────────────────────────────────────────
        _set_stage(db, job, "rendering", "Rendering video…", 80)
        render_id = _run_rendering(db, job, timeline_id, caption_style_id, aspect_ratio)
        if render_id is None:
            return

        job.render_id  = render_id
        job.updated_at = _now()
        db.commit()

        if not _wait_rendering(db, job, render_id):
            return

        # ── Done ──────────────────────────────────────────────────────────────
        from kairos.models import RenderJob
        rjob = db.query(RenderJob).filter(RenderJob.render_id == render_id).first()
        output_path = rjob.output_path if rjob else None

        job.job_status  = "done"
        job.stage_label = "Complete"
        job.progress    = 100
        job.output_path = output_path
        job.updated_at  = _now()
        db.commit()
        logger.info("QuickJob %s complete — output: %s", job_id, output_path)

    except Exception as exc:
        logger.exception("run_quick_job %s raised unexpectedly", job_id)
        try:
            job = db.query(QuickJob).filter(QuickJob.job_id == job_id).first()
            if job:
                _fail(db, job, f"Unexpected error: {exc}")
        except Exception:
            pass
    finally:
        db.close()


def start_quick_job(job_id: str) -> None:
    """Launch the orchestrator in a daemon thread."""
    t = threading.Thread(target=run_quick_job, args=(job_id,), daemon=True, name=f"quick-{job_id[:8]}")
    t.start()
    logger.info("QuickJob %s started on thread %s", job_id, t.name)
