"""
Smart Query orchestrator — background thread that fetches candidates and scores them.

Stage flow:
  pending   → thread starts
  fetching  → data_fetcher queries Kairos DB (or Atlas for civic_media in SQ-4)
  scoring   → intent_scorer batches segments through LLM provider
  done      → all candidates scored and stored
  error     → any unhandled exception
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _set_stage(db: Session, query, status: str, label: str, progress: int) -> None:
    query.query_status = status
    query.query_stage_label = label
    query.query_progress = progress
    query.updated_at = _now()
    db.commit()
    logger.info("SmartQuery %s → %s (%d%%)", query.query_id, status, progress)


def _fail(db: Session, query, msg: str) -> None:
    query.query_status = "error"
    query.query_error_msg = msg[:2000]
    query.updated_at = _now()
    db.commit()
    logger.error("SmartQuery %s failed: %s", query.query_id, msg)


def run_smart_query(query_id: str) -> None:
    """Background thread entry point for a Smart Query."""
    from kairos.database import SessionLocal
    from kairos.models import (
        SmartQuery, QueryCandidate, IntentProfile, IntentExample, ModelScoringRun,
    )
    from kairos.services.smart_query.data_fetcher import fetch_kairos_candidates
    from kairos.services.smart_query.intent_scorer import (
        build_scoring_prompt, parse_intent_scores, get_batch_size, build_few_shot_section,
    )
    from kairos.services.llm_providers import get_provider, get_model_id

    db = SessionLocal()
    try:
        query = db.query(SmartQuery).filter(SmartQuery.query_id == query_id).first()
        if not query:
            logger.error("run_smart_query: query_id %s not found", query_id)
            return

        query_text = query.query_text
        filters = json.loads(query.query_filters) if query.query_filters else {}
        intent_profile_id = query.intent_profile_id
        scorer_model_names = json.loads(query.scorer_models) if query.scorer_models else ["default"]

        # Resolve "default" to the configured provider
        if scorer_model_names == ["default"]:
            scorer_model_names = [None]  # None = use default from config

        # Load custom system prompt from intent profile if available
        custom_prompt = None
        if intent_profile_id:
            profile = db.query(IntentProfile).filter(
                IntentProfile.intent_profile_id == intent_profile_id
            ).first()
            if profile and profile.intent_system_prompt:
                custom_prompt = profile.intent_system_prompt

        # ── Stage 1: Fetch candidates ────────────────────────────────────────
        _set_stage(db, query, "fetching", "Searching library…", 10)

        if query.query_source == "kairos":
            raw_candidates = fetch_kairos_candidates(
                db=db,
                filters=filters,
                max_candidates=100,
            )
        else:
            _fail(db, query, f"Source '{query.query_source}' not yet supported (SQ-4)")
            return

        if not raw_candidates:
            _fail(db, query, "No matching segments found for the given filters")
            return

        # Store candidates in DB
        candidate_rows = []
        for cand in raw_candidates:
            row = QueryCandidate(
                candidate_id=str(uuid.uuid4()),
                query_id=query_id,
                candidate_origin=cand["candidate_origin"],
                candidate_item_id=cand.get("candidate_item_id"),
                candidate_segment_id=cand.get("candidate_segment_id"),
                candidate_speaker=cand.get("candidate_speaker"),
                candidate_text=cand["candidate_text"],
                candidate_start_ms=cand.get("candidate_start_ms"),
                candidate_end_ms=cand.get("candidate_end_ms"),
                candidate_video_title=cand.get("candidate_video_title"),
                candidate_video_date=cand.get("candidate_video_date"),
                candidate_source_url=cand.get("candidate_source_url"),
                created_at=_now(),
            )
            db.add(row)
            candidate_rows.append(row)

        db.commit()
        logger.info("SmartQuery %s: stored %d candidates", query_id, len(candidate_rows))

        # ── Stage 2: Score with each model ───────────────────────────────────
        _set_stage(db, query, "scoring", "Scoring segments…", 30)

        has_examples = bool(
            intent_profile_id
            and db.query(IntentExample)
            .filter(IntentExample.intent_profile_id == intent_profile_id)
            .first()
        )
        batch_size = get_batch_size(has_examples)

        for model_name in scorer_model_names:
            try:
                call_fn, provider_name = get_provider(model_name)
            except Exception as exc:
                logger.warning("SmartQuery %s: provider %s failed: %s", query_id, model_name, exc)
                continue

            model_id = get_model_id(model_name)

            # For ollama, check import availability
            if provider_name == "ollama":
                try:
                    import ollama  # noqa: F401
                except ImportError:
                    logger.warning("SmartQuery %s: ollama not installed, skipping", query_id)
                    continue

            # Create scoring run record
            run = ModelScoringRun(
                run_id=str(uuid.uuid4()),
                query_id=query_id,
                run_model_id=model_id,
                run_provider=provider_name,
                run_status="running",
                created_at=_now(),
            )
            db.add(run)
            db.commit()

            t0 = time.monotonic()
            scored_count = 0

            # Score in batches
            for batch_start in range(0, len(candidate_rows), batch_size):
                batch = candidate_rows[batch_start : batch_start + batch_size]
                batch_dicts = [
                    {
                        "candidate_speaker": r.candidate_speaker,
                        "candidate_text": r.candidate_text,
                        "candidate_video_title": r.candidate_video_title,
                        "candidate_video_date": r.candidate_video_date,
                        "candidate_start_ms": r.candidate_start_ms,
                        "candidate_end_ms": r.candidate_end_ms,
                    }
                    for r in batch
                ]

                prompt = build_scoring_prompt(
                    query_text=query_text,
                    batch=batch_dicts,
                    intent_profile_id=intent_profile_id,
                    db=db,
                    custom_system_prompt=custom_prompt,
                )

                try:
                    raw_text = call_fn(prompt)
                    scores = parse_intent_scores(raw_text, len(batch))
                except Exception as exc:
                    logger.warning(
                        "SmartQuery %s: scoring error batch %d (%s): %s",
                        query_id, batch_start, provider_name, exc,
                    )
                    scores = [
                        {"intent_relevance_score": 0.5, "intent_score_reason": ""}
                        for _ in batch
                    ]

                for row, score_data in zip(batch, scores):
                    row.intent_relevance_score = score_data["intent_relevance_score"]
                    row.intent_score_reason = score_data["intent_score_reason"]
                    row.intent_scorer_model = model_id
                    scored_count += 1

                db.commit()

                # Update progress
                pct = 30 + int(60 * (batch_start + len(batch)) / len(candidate_rows))
                _set_stage(db, query, "scoring", f"Scoring… {scored_count}/{len(candidate_rows)}", min(pct, 90))

            duration_ms = int((time.monotonic() - t0) * 1000)
            run.run_status = "done"
            run.run_candidates_scored = scored_count
            run.run_duration_ms = duration_ms
            db.commit()

            logger.info(
                "SmartQuery %s: model %s scored %d candidates in %dms",
                query_id, model_id, scored_count, duration_ms,
            )

        # ── Done ─────────────────────────────────────────────────────────────
        query.query_result_count = len(candidate_rows)
        query.query_status = "done"
        query.query_stage_label = "Complete"
        query.query_progress = 100
        query.updated_at = _now()
        db.commit()
        logger.info("SmartQuery %s complete — %d results", query_id, len(candidate_rows))

    except Exception as exc:
        logger.exception("run_smart_query %s raised unexpectedly", query_id)
        try:
            query = db.query(SmartQuery).filter(SmartQuery.query_id == query_id).first()
            if query:
                _fail(db, query, f"Unexpected error: {exc}")
        except Exception:
            pass
    finally:
        db.close()


def start_smart_query(query_id: str) -> None:
    """Launch the Smart Query orchestrator in a daemon thread."""
    t = threading.Thread(
        target=run_smart_query,
        args=(query_id,),
        daemon=True,
        name=f"sq-{query_id[:8]}",
    )
    t.start()
    logger.info("SmartQuery %s started on thread %s", query_id, t.name)
