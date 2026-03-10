"""
Timeline CRUD + element editing API — Phase 5.

GET    /api/timelines
GET    /api/timelines/{timeline_id}
PATCH  /api/timelines/{timeline_id}
DELETE /api/timelines/{timeline_id}
GET    /api/timelines/{timeline_id}/elements
POST   /api/timelines/{timeline_id}/elements
PATCH  /api/timelines/{timeline_id}/elements/{element_id}
DELETE /api/timelines/{timeline_id}/elements/{element_id}
POST   /api/timelines/{timeline_id}/reorder
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.schemas import TimelineElementCreate, TimelineElementOut, TimelineOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timelines", tags=["timelines"])


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ── Timeline CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[TimelineOut])
def list_timelines(
    project_id: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    limit:      int            = Query(20, ge=1, le=200),
    offset:     int            = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List timelines with optional project_id and status filters."""
    from kairos.models import Timeline, TimelineElement

    query = db.query(Timeline)
    if project_id:
        query = query.filter(Timeline.project_id == project_id)
    if status:
        query = query.filter(Timeline.timeline_status == status)

    rows = (
        query.order_by(Timeline.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for tl in rows:
        elem_rows = (
            db.query(TimelineElement)
            .filter(TimelineElement.timeline_id == tl.timeline_id)
            .all()
        )
        clip_count = sum(1 for e in elem_rows if e.element_type == "clip")
        results.append(_timeline_to_out(tl, elem_rows, clip_count))
    return results


@router.get("/{timeline_id}", response_model=TimelineOut)
def get_timeline(timeline_id: str, db: Session = Depends(get_db)):
    """Return full timeline with all elements."""
    from kairos.services.story_builder.timeline_builder import get_timeline_with_elements
    data = get_timeline_with_elements(db, timeline_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")
    return _dict_to_timeline_out(data)


@router.patch("/{timeline_id}", response_model=TimelineOut)
def update_timeline(
    timeline_id: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """Update timeline name, aspect_ratio, or story_template."""
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    allowed = {"timeline_name", "aspect_ratio", "story_template"}
    for key, val in body.items():
        if key in allowed:
            setattr(tl, key, val)

    tl.updated_at = _now()
    db.commit()
    db.refresh(tl)

    elem_rows = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .order_by(TimelineElement.position)
        .all()
    )
    clip_count = sum(1 for e in elem_rows if e.element_type == "clip")
    return _timeline_to_out(tl, elem_rows, clip_count)


@router.delete("/{timeline_id}")
def delete_timeline(timeline_id: str, db: Session = Depends(get_db)):
    """Delete timeline and all its elements."""
    from kairos.services.story_builder.timeline_builder import delete_timeline as _delete
    deleted = _delete(db, timeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")
    return {"deleted": True}


# ── Element operations ────────────────────────────────────────────────────────

@router.get("/{timeline_id}/elements", response_model=list[TimelineElementOut])
def list_elements(timeline_id: str, db: Session = Depends(get_db)):
    """List all TimelineElements for a timeline, ordered by position."""
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    rows = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .order_by(TimelineElement.position)
        .all()
    )
    return [_element_to_out(r) for r in rows]


@router.post("/{timeline_id}/elements", response_model=TimelineElementOut, status_code=201)
def add_element(
    timeline_id: str,
    body: TimelineElementCreate,
    db: Session = Depends(get_db),
):
    """
    Add a new element at the requested position.
    All elements at >= position are shifted up by 1.
    """
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    # Shift existing elements at >= insert position
    rows_to_shift = (
        db.query(TimelineElement)
        .filter(
            TimelineElement.timeline_id == timeline_id,
            TimelineElement.position >= body.position,
        )
        .all()
    )
    for row in rows_to_shift:
        row.position += 1

    new_elem = TimelineElement(
        element_id     = str(uuid.uuid4()),
        timeline_id    = timeline_id,
        element_type   = body.element_type,
        position       = body.position,
        start_ms       = _compute_start_ms(db, timeline_id, body.position),
        duration_ms    = body.duration_ms,
        clip_id        = body.clip_id,
        element_params = body.element_params,
        created_at     = _now(),
    )
    db.add(new_elem)

    # Update timeline updated_at
    tl.updated_at = _now()
    db.commit()
    db.refresh(new_elem)

    # Recompute start_ms for all elements after this insertion
    _recompute_start_ms(db, timeline_id)
    db.commit()
    db.refresh(new_elem)

    return _element_to_out(new_elem)


@router.patch("/{timeline_id}/elements/{element_id}", response_model=TimelineElementOut)
def update_element(
    timeline_id: str,
    element_id:  str,
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Update element_params and/or position.
    If position changes, shift other elements accordingly.
    """
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    elem = (
        db.query(TimelineElement)
        .filter(
            TimelineElement.timeline_id == timeline_id,
            TimelineElement.element_id  == element_id,
        )
        .first()
    )
    if not elem:
        raise HTTPException(
            status_code=404,
            detail=f"Element '{element_id}' not found in timeline '{timeline_id}'",
        )

    old_position = elem.position

    if "element_params" in body:
        elem.element_params = body["element_params"]

    if "duration_ms" in body:
        elem.duration_ms = int(body["duration_ms"])

    if "position" in body:
        new_position = int(body["position"])
        if new_position != old_position:
            # Shift elements between old and new positions
            all_elements = (
                db.query(TimelineElement)
                .filter(
                    TimelineElement.timeline_id == timeline_id,
                    TimelineElement.element_id != element_id,
                )
                .order_by(TimelineElement.position)
                .all()
            )
            if new_position > old_position:
                for e in all_elements:
                    if old_position < e.position <= new_position:
                        e.position -= 1
            else:
                for e in all_elements:
                    if new_position <= e.position < old_position:
                        e.position += 1
            elem.position = new_position

    tl.updated_at = _now()
    db.commit()

    _recompute_start_ms(db, timeline_id)
    db.commit()
    db.refresh(elem)

    return _element_to_out(elem)


@router.delete("/{timeline_id}/elements/{element_id}")
def delete_element(
    timeline_id: str,
    element_id:  str,
    db: Session = Depends(get_db),
):
    """Remove an element and reorder remaining positions."""
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    elem = (
        db.query(TimelineElement)
        .filter(
            TimelineElement.timeline_id == timeline_id,
            TimelineElement.element_id  == element_id,
        )
        .first()
    )
    if not elem:
        raise HTTPException(
            status_code=404,
            detail=f"Element '{element_id}' not found in timeline '{timeline_id}'",
        )

    removed_position = elem.position
    db.delete(elem)

    # Shift down all elements after the removed position
    later_elements = (
        db.query(TimelineElement)
        .filter(
            TimelineElement.timeline_id == timeline_id,
            TimelineElement.position > removed_position,
        )
        .all()
    )
    for e in later_elements:
        e.position -= 1

    tl.updated_at = _now()
    db.commit()

    _recompute_start_ms(db, timeline_id)
    db.commit()

    return {"deleted": True}


@router.post("/{timeline_id}/reorder", response_model=list[TimelineElementOut])
def reorder_elements(
    timeline_id: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Bulk reorder all elements.
    Body: {"element_ids": [ordered list of element_ids]}
    """
    from kairos.models import Timeline, TimelineElement

    tl = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail=f"Timeline '{timeline_id}' not found")

    element_ids: list[str] = body.get("element_ids", [])
    if not element_ids:
        raise HTTPException(status_code=422, detail="element_ids must not be empty")

    # Load all elements for this timeline
    elem_map: dict[str, object] = {
        e.element_id: e
        for e in db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .all()
    }

    # Validate all supplied IDs exist in this timeline
    for eid in element_ids:
        if eid not in elem_map:
            raise HTTPException(
                status_code=422,
                detail=f"element_id '{eid}' not found in timeline '{timeline_id}'",
            )

    # Assign new positions
    for new_pos, eid in enumerate(element_ids):
        elem_map[eid].position = new_pos

    tl.updated_at = _now()
    db.commit()

    _recompute_start_ms(db, timeline_id)
    db.commit()

    rows = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .order_by(TimelineElement.position)
        .all()
    )
    return [_element_to_out(r) for r in rows]


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_start_ms(db, timeline_id: str, position: int) -> int:
    """Compute the start_ms for an element inserted at a given position."""
    from kairos.models import TimelineElement
    earlier = (
        db.query(TimelineElement)
        .filter(
            TimelineElement.timeline_id == timeline_id,
            TimelineElement.position < position,
        )
        .order_by(TimelineElement.position)
        .all()
    )
    return sum(e.duration_ms or 0 for e in earlier)


def _recompute_start_ms(db, timeline_id: str) -> None:
    """Recompute cumulative start_ms for every element in order."""
    from kairos.models import TimelineElement
    rows = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .order_by(TimelineElement.position)
        .all()
    )
    cumulative = 0
    for row in rows:
        row.start_ms = cumulative
        cumulative += row.duration_ms or 0


def _element_to_out(row) -> TimelineElementOut:
    return TimelineElementOut(
        element_id     = row.element_id,
        timeline_id    = row.timeline_id,
        element_type   = row.element_type,
        position       = row.position,
        start_ms       = row.start_ms,
        duration_ms    = row.duration_ms,
        clip_id        = row.clip_id,
        element_params = row.element_params,
        created_at     = row.created_at,
    )


def _timeline_to_out(tl, elem_rows, clip_count: int) -> TimelineOut:
    elements = [_element_to_out(e) for e in sorted(elem_rows, key=lambda e: e.position)]
    return TimelineOut(
        timeline_id        = tl.timeline_id,
        project_id         = tl.project_id,
        timeline_name      = tl.timeline_name,
        story_template     = tl.story_template,
        aspect_ratio       = tl.aspect_ratio,
        target_duration_ms = tl.target_duration_ms,
        timeline_status    = tl.timeline_status,
        element_count      = len(elements),
        clip_count         = clip_count,
        elements           = elements,
        created_at         = tl.created_at,
        updated_at         = tl.updated_at,
    )


def _dict_to_timeline_out(d: dict) -> TimelineOut:
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
