"""
Assemble a Timeline + TimelineElement rows in the database from flow_enforcer output.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def build_timeline(
    db,
    name: str,
    template_id: str,
    elements: list[dict],
    aspect_ratio: str = "16:9",
    project_id: Optional[str] = None,
) -> dict:
    """
    Persist a Timeline and its TimelineElement rows to the DB.

    Steps:
    1. Create Timeline row (status='ready')
    2. For each element: compute cumulative start_ms, create TimelineElement row
    3. Update timeline.target_duration_ms = total duration
    4. Return full timeline dict with elements list
    """
    from kairos.models import Timeline, TimelineElement

    now_ts = _now()
    timeline_id = str(uuid.uuid4())

    timeline = Timeline(
        timeline_id        = timeline_id,
        project_id         = project_id,
        timeline_name      = name,
        story_template     = template_id,
        aspect_ratio       = aspect_ratio,
        target_duration_ms = None,    # computed after elements are created
        timeline_status    = "ready",
        created_at         = now_ts,
        updated_at         = now_ts,
    )
    db.add(timeline)
    db.flush()   # ensure timeline_id is written before FK references

    # Build TimelineElement rows with cumulative start_ms
    element_rows: list[TimelineElement] = []
    cumulative_ms = 0
    clip_count = 0

    for position, elem in enumerate(elements):
        element_id    = str(uuid.uuid4())
        duration_ms   = elem.get("duration_ms", 0) or 0
        clip_id       = elem.get("clip_id")

        # Collect extra params (everything except known top-level keys)
        params = {
            k: v for k, v in elem.items()
            if k not in ("element_type", "clip_id", "duration_ms", "position")
        }
        # Merge in 'params' sub-dict if present
        if "params" in elem and isinstance(elem["params"], dict):
            params.update(elem["params"])
            del params["params"]

        element_params_json = json.dumps(params) if params else None

        row = TimelineElement(
            element_id     = element_id,
            timeline_id    = timeline_id,
            element_type   = elem.get("element_type", "clip"),
            position       = position,
            start_ms       = cumulative_ms,
            duration_ms    = duration_ms,
            clip_id        = clip_id,
            element_params = element_params_json,
            created_at     = now_ts,
        )
        db.add(row)
        element_rows.append(row)

        cumulative_ms += duration_ms
        if elem.get("element_type") == "clip":
            clip_count += 1

    # Update timeline with final duration
    timeline.target_duration_ms = cumulative_ms
    timeline.updated_at = _now()
    db.commit()
    db.refresh(timeline)

    # Build return dict
    elements_out = []
    for row in element_rows:
        elements_out.append({
            "element_id":     row.element_id,
            "timeline_id":    row.timeline_id,
            "element_type":   row.element_type,
            "position":       row.position,
            "start_ms":       row.start_ms,
            "duration_ms":    row.duration_ms,
            "clip_id":        row.clip_id,
            "element_params": row.element_params,
            "created_at":     row.created_at,
        })

    return {
        "timeline_id":        timeline.timeline_id,
        "timeline_name":      timeline.timeline_name,
        "project_id":         timeline.project_id,
        "story_template":     timeline.story_template,
        "aspect_ratio":       timeline.aspect_ratio,
        "target_duration_ms": timeline.target_duration_ms,
        "timeline_status":    timeline.timeline_status,
        "element_count":      len(element_rows),
        "clip_count":         clip_count,
        "elements":           elements_out,
        "created_at":         timeline.created_at,
        "updated_at":         timeline.updated_at,
    }


def get_timeline_with_elements(db, timeline_id: str) -> dict | None:
    """Load a Timeline + all its TimelineElements, return as nested dict."""
    from kairos.models import Timeline, TimelineElement

    timeline = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not timeline:
        return None

    element_rows = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
        .order_by(TimelineElement.position)
        .all()
    )

    elements_out = [
        {
            "element_id":     row.element_id,
            "timeline_id":    row.timeline_id,
            "element_type":   row.element_type,
            "position":       row.position,
            "start_ms":       row.start_ms,
            "duration_ms":    row.duration_ms,
            "clip_id":        row.clip_id,
            "element_params": row.element_params,
            "created_at":     row.created_at,
        }
        for row in element_rows
    ]

    clip_count = sum(1 for e in element_rows if e.element_type == "clip")

    return {
        "timeline_id":        timeline.timeline_id,
        "timeline_name":      timeline.timeline_name,
        "project_id":         timeline.project_id,
        "story_template":     timeline.story_template,
        "aspect_ratio":       timeline.aspect_ratio,
        "target_duration_ms": timeline.target_duration_ms,
        "timeline_status":    timeline.timeline_status,
        "element_count":      len(elements_out),
        "clip_count":         clip_count,
        "elements":           elements_out,
        "created_at":         timeline.created_at,
        "updated_at":         timeline.updated_at,
    }


def delete_timeline(db, timeline_id: str) -> bool:
    """Delete Timeline + all TimelineElements. Return True if found and deleted."""
    from kairos.models import Timeline, TimelineElement

    timeline = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not timeline:
        return False

    db.query(TimelineElement).filter(TimelineElement.timeline_id == timeline_id).delete(
        synchronize_session=False
    )
    db.delete(timeline)
    db.commit()
    return True
