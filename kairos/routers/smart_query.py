"""
Smart Query API — SQ-1.

POST /api/smart-query                           — submit a new smart query
GET  /api/smart-query                           — list recent queries
GET  /api/smart-query/{query_id}                — get query status
GET  /api/smart-query/{query_id}/results        — paginated scored results
POST /api/smart-query/candidates/{id}/rate      — rate a result
POST /api/smart-query/candidates/{id}/import    — import as Kairos clip

GET  /api/intent-profiles                       — list intent profiles
POST /api/intent-profiles                       — create intent profile
GET  /api/intent-profiles/{id}                  — get profile detail
PATCH /api/intent-profiles/{id}                 — update profile
GET  /api/intent-profiles/{id}/examples         — list examples
DELETE /api/intent-profiles/{id}/examples/{eid} — remove example
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.models import (
    SmartQuery, QueryCandidate, IntentProfile, IntentExample,
    Clip, TranscriptionSegment,
)
from kairos.schemas import (
    SmartQueryIn, SmartQueryOut, QueryCandidateOut,
    CandidateRatingIn, IntentProfileIn, IntentProfileOut, IntentExampleOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["smart-query"])


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _query_to_out(q: SmartQuery) -> SmartQueryOut:
    return SmartQueryOut(
        query_id=q.query_id,
        query_text=q.query_text,
        query_source=q.query_source,
        query_status=q.query_status,
        query_progress=q.query_progress or 0,
        query_stage_label=q.query_stage_label,
        intent_profile_id=q.intent_profile_id,
        scorer_models=json.loads(q.scorer_models) if q.scorer_models else None,
        query_result_count=q.query_result_count or 0,
        query_error_msg=q.query_error_msg,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


# ── Smart Query endpoints ────────────────────────────────────────────────────

@router.post("/api/smart-query", response_model=SmartQueryOut, status_code=202)
def create_smart_query(req: SmartQueryIn, db: Session = Depends(get_db)):
    """Submit a new Smart Query for background scoring."""
    if req.query_source not in ("kairos", "civic_media", "mixed"):
        raise HTTPException(status_code=422, detail="query_source must be kairos, civic_media, or mixed")

    now = _now()
    q = SmartQuery(
        query_id=str(uuid.uuid4()),
        query_text=req.query_text,
        query_source=req.query_source,
        intent_profile_id=req.intent_profile_id,
        query_filters=json.dumps(req.filters) if req.filters else None,
        scorer_models=json.dumps(req.scorer_models),
        project_id=req.project_id,
        query_status="pending",
        query_stage_label="Queued",
        query_progress=0,
        created_at=now,
        updated_at=now,
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    from kairos.services.smart_query.orchestrator import start_smart_query
    start_smart_query(q.query_id)

    logger.info("SmartQuery %s created: %s", q.query_id, req.query_text[:80])
    return _query_to_out(q)


@router.get("/api/smart-query", response_model=list[SmartQueryOut])
def list_smart_queries(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent smart queries, newest first."""
    queries = (
        db.query(SmartQuery)
        .order_by(SmartQuery.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_query_to_out(q) for q in queries]


@router.get("/api/smart-query/{query_id}", response_model=SmartQueryOut)
def get_smart_query(query_id: str, db: Session = Depends(get_db)):
    """Get smart query status."""
    q = db.query(SmartQuery).filter(SmartQuery.query_id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail=f"SmartQuery {query_id!r} not found")
    return _query_to_out(q)


@router.get("/api/smart-query/{query_id}/results", response_model=list[QueryCandidateOut])
def get_smart_query_results(
    query_id: str,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get scored results for a smart query, sorted by relevance."""
    q = db.query(SmartQuery).filter(SmartQuery.query_id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail=f"SmartQuery {query_id!r} not found")

    candidates = (
        db.query(QueryCandidate)
        .filter(
            QueryCandidate.query_id == query_id,
            QueryCandidate.intent_relevance_score >= min_score,
        )
        .order_by(QueryCandidate.intent_relevance_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return candidates


# ── Candidate feedback endpoints ─────────────────────────────────────────────

@router.post("/api/smart-query/candidates/{candidate_id}/rate", response_model=QueryCandidateOut)
def rate_candidate(candidate_id: str, req: CandidateRatingIn, db: Session = Depends(get_db)):
    """Rate a query candidate (thumbs up/down)."""
    if req.rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating must be 1 or -1")

    cand = db.query(QueryCandidate).filter(QueryCandidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id!r} not found")

    cand.candidate_user_rating = req.rating
    cand.candidate_rating_note = req.note

    # Auto-save as intent example if requested and query has an intent profile
    if req.save_as_example:
        query = db.query(SmartQuery).filter(SmartQuery.query_id == cand.query_id).first()
        if query and query.intent_profile_id:
            context = json.dumps({
                "speaker": cand.candidate_speaker,
                "video_title": cand.candidate_video_title,
                "date": cand.candidate_video_date,
            })
            example = IntentExample(
                example_id=str(uuid.uuid4()),
                intent_profile_id=query.intent_profile_id,
                candidate_id=candidate_id,
                example_text=cand.candidate_text,
                example_context=context,
                example_rating=req.rating,
                example_note=req.note,
                example_scorer_model=cand.intent_scorer_model,
                example_original_score=cand.intent_relevance_score,
                created_at=_now(),
            )
            db.add(example)

            # Update example count
            profile = db.query(IntentProfile).filter(
                IntentProfile.intent_profile_id == query.intent_profile_id
            ).first()
            if profile:
                count = db.query(IntentExample).filter(
                    IntentExample.intent_profile_id == query.intent_profile_id
                ).count()
                profile.intent_example_count = count + 1
                profile.updated_at = _now()

    db.commit()
    return cand


@router.post("/api/smart-query/candidates/{candidate_id}/import")
def import_candidate_as_clip(candidate_id: str, db: Session = Depends(get_db)):
    """Import a scored candidate as a Kairos clip."""
    cand = db.query(QueryCandidate).filter(QueryCandidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id!r} not found")

    if cand.imported_as_clip_id:
        return {"clip_id": cand.imported_as_clip_id, "already_imported": True}

    if cand.candidate_origin != "kairos" or not cand.candidate_item_id:
        raise HTTPException(
            status_code=422,
            detail="Import only supported for Kairos-origin candidates with item_id",
        )

    if cand.candidate_start_ms is None or cand.candidate_end_ms is None:
        raise HTTPException(status_code=422, detail="Candidate missing start/end timestamps")

    now = _now()
    clip = Clip(
        clip_id=str(uuid.uuid4()),
        item_id=cand.candidate_item_id,
        clip_title=cand.candidate_text[:80] if cand.candidate_text else None,
        start_ms=cand.candidate_start_ms,
        end_ms=cand.candidate_end_ms,
        duration_ms=cand.candidate_end_ms - cand.candidate_start_ms,
        virality_score=cand.intent_relevance_score,
        clip_status="pending",
        clip_source="smart_query",
        speaker_label=cand.candidate_speaker,
        clip_transcript=cand.candidate_text,
        query_candidate_id=cand.candidate_id,
        created_at=now,
        updated_at=now,
    )
    db.add(clip)
    cand.imported_as_clip_id = clip.clip_id
    db.commit()

    return {"clip_id": clip.clip_id, "already_imported": False}


# ── Intent Profile endpoints ─────────────────────────────────────────────────

@router.get("/api/intent-profiles", response_model=list[IntentProfileOut])
def list_intent_profiles(db: Session = Depends(get_db)):
    """List all intent profiles."""
    profiles = (
        db.query(IntentProfile)
        .order_by(IntentProfile.created_at.desc())
        .all()
    )
    return profiles


@router.post("/api/intent-profiles", response_model=IntentProfileOut, status_code=201)
def create_intent_profile(req: IntentProfileIn, db: Session = Depends(get_db)):
    """Create a new intent profile."""
    existing = db.query(IntentProfile).filter(IntentProfile.intent_name == req.intent_name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Intent profile {req.intent_name!r} already exists")

    now = _now()
    profile = IntentProfile(
        intent_profile_id=str(uuid.uuid4()),
        intent_name=req.intent_name,
        intent_description=req.intent_description,
        intent_system_prompt=req.intent_system_prompt,
        intent_example_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/api/intent-profiles/{profile_id}", response_model=IntentProfileOut)
def get_intent_profile(profile_id: str, db: Session = Depends(get_db)):
    """Get intent profile detail."""
    profile = db.query(IntentProfile).filter(IntentProfile.intent_profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"IntentProfile {profile_id!r} not found")
    return profile


@router.patch("/api/intent-profiles/{profile_id}", response_model=IntentProfileOut)
def update_intent_profile(profile_id: str, req: IntentProfileIn, db: Session = Depends(get_db)):
    """Update an intent profile."""
    profile = db.query(IntentProfile).filter(IntentProfile.intent_profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"IntentProfile {profile_id!r} not found")

    if req.intent_name:
        profile.intent_name = req.intent_name
    if req.intent_description is not None:
        profile.intent_description = req.intent_description
    if req.intent_system_prompt is not None:
        profile.intent_system_prompt = req.intent_system_prompt
    profile.updated_at = _now()
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/api/intent-profiles/{profile_id}/examples", response_model=list[IntentExampleOut])
def list_intent_examples(
    profile_id: str,
    rating: int = Query(None, description="Filter by rating: 1 or -1"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List examples for an intent profile."""
    query = db.query(IntentExample).filter(IntentExample.intent_profile_id == profile_id)
    if rating is not None:
        query = query.filter(IntentExample.example_rating == rating)
    examples = query.order_by(IntentExample.created_at.desc()).limit(limit).all()
    return examples


@router.delete("/api/intent-profiles/{profile_id}/examples/{example_id}")
def delete_intent_example(profile_id: str, example_id: str, db: Session = Depends(get_db)):
    """Remove an example from an intent profile."""
    example = db.query(IntentExample).filter(
        IntentExample.example_id == example_id,
        IntentExample.intent_profile_id == profile_id,
    ).first()
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")

    db.delete(example)

    # Update count
    profile = db.query(IntentProfile).filter(IntentProfile.intent_profile_id == profile_id).first()
    if profile:
        count = db.query(IntentExample).filter(
            IntentExample.intent_profile_id == profile_id
        ).count()
        profile.intent_example_count = max(0, count - 1)
        profile.updated_at = _now()

    db.commit()
    return {"deleted": True}
