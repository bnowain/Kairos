"""
Story generation API — Phase 5.

POST /api/stories/generate       — build a timeline from clips + a template
GET  /api/stories/templates      — list available story templates
GET  /api/stories/templates/{id} — full template with slots
POST /api/stories/templates/validate — validate a raw template JSON
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.schemas import StoryGenerateRequest, TimelineOut, TimelineElementOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.post("/generate", response_model=TimelineOut, status_code=201)
def generate_story(req: StoryGenerateRequest, db: Session = Depends(get_db)):
    """
    Build a timeline synchronously from clips + template.

    - Single item_id  → single-source story
    - Multiple item_ids → mashup via mashup_engine

    Validates that all item_ids exist and have at least one ready clip.
    Runs the full pipeline in the request handler and returns the result.
    """
    from kairos.models import Clip, MediaItem
    from kairos.services.story_builder import (
        clip_ranker, slot_assigner, flow_enforcer, timeline_builder, mashup_engine
    )
    from kairos.services.story_builder.template_loader import load_template

    # Validate item_ids
    if not req.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")

    for item_id in req.item_ids:
        item = db.query(MediaItem).filter(MediaItem.item_id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=404, detail=f"MediaItem '{item_id}' not found"
            )

    # Confirm at least one ready clip exists across all item_ids
    ready_clip = (
        db.query(Clip)
        .filter(Clip.item_id.in_(req.item_ids), Clip.clip_status == "ready")
        .first()
    )
    if not ready_clip:
        raise HTTPException(
            status_code=422,
            detail="No ready clips found for the supplied item_ids. "
                   "Run analysis + clip extraction first.",
        )

    # Validate template exists
    try:
        load_template(req.template_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Template '{req.template_id}' not found"
        )

    # Build timeline
    if len(req.item_ids) > 1:
        # Multi-source mashup
        timeline_dict = mashup_engine.build_mashup(
            db=db,
            name=req.name,
            item_ids=req.item_ids,
            template_id=req.template_id,
            aspect_ratio=req.aspect_ratio,
            min_score=req.min_score,
            project_id=req.project_id,
        )
    else:
        # Single-source story — same pipeline as mashup but for one item
        template = load_template(req.template_id)
        clips = clip_ranker.load_clips_with_scores(db, item_ids=req.item_ids)

        if req.min_score > 0:
            clips = [
                c for c in clips
                if (c.get("scores", {}).get("composite", 0.0) or 0.0) >= req.min_score
                or (c.get("virality_score", 0.0) or 0.0) >= req.min_score
            ]

        assignment = slot_assigner.assign_slots(
            template=template,
            clips=clips,
            pacing_override=req.pacing,
        )
        elements = flow_enforcer.enforce_flow(
            slot_assignments=assignment["slot_assignments"],
            template=template,
            pacing=req.pacing,
        )
        timeline_dict = timeline_builder.build_timeline(
            db=db,
            name=req.name,
            template_id=req.template_id,
            elements=elements,
            aspect_ratio=req.aspect_ratio,
            project_id=req.project_id,
        )

    return _dict_to_timeline_out(timeline_dict)


@router.get("/templates")
def list_templates():
    """Return metadata for all available story templates."""
    from kairos.services.story_builder.template_loader import list_templates as _list
    return _list()


@router.get("/templates/{template_id}")
def get_template(template_id: str):
    """Return full template including all slot definitions."""
    from kairos.services.story_builder.template_loader import load_template
    try:
        return load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@router.post("/templates/validate")
def validate_template(template: dict):
    """Validate a raw template JSON body."""
    from kairos.services.story_builder.template_loader import validate_template as _validate
    errors = _validate(template)
    return {"valid": len(errors) == 0, "errors": errors}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dict_to_timeline_out(d: dict) -> TimelineOut:
    """Convert a timeline dict (from timeline_builder) to a TimelineOut schema."""
    elements = [
        TimelineElementOut(
            element_id     = e["element_id"],
            timeline_id    = e["timeline_id"],
            element_type   = e["element_type"],
            position       = e["position"],
            start_ms       = e["start_ms"],
            duration_ms    = e["duration_ms"],
            clip_id        = e.get("clip_id"),
            element_params = e.get("element_params"),
            created_at     = e["created_at"],
        )
        for e in d.get("elements", [])
    ]
    return TimelineOut(
        timeline_id        = d["timeline_id"],
        project_id         = d.get("project_id"),
        timeline_name      = d["timeline_name"],
        story_template     = d.get("story_template"),
        aspect_ratio       = d["aspect_ratio"],
        target_duration_ms = d.get("target_duration_ms"),
        timeline_status    = d["timeline_status"],
        element_count      = d.get("element_count", len(elements)),
        clip_count         = d.get("clip_count", 0),
        elements           = elements,
        created_at         = d["created_at"],
        updated_at         = d["updated_at"],
    )
