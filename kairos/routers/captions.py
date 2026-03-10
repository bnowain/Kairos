"""
Caption style CRUD + preview API — Phase 6.

GET    /api/captions/styles                 — list all styles + built-in presets
POST   /api/captions/styles                 — create a new style
GET    /api/captions/styles/{style_id}      — single style
PATCH  /api/captions/styles/{style_id}      — update style fields
DELETE /api/captions/styles/{style_id}      — delete style
GET    /api/captions/presets                — return PLATFORM_PRESETS dict
POST   /api/captions/clips/{clip_id}/export — export captions for a single clip
POST   /api/captions/timeline/{timeline_id}/generate — generate ASS for full timeline
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from kairos.database import get_db
from kairos.models import CaptionStyle, Clip, Timeline, TimelineElement
from kairos.schemas import CaptionStyleCreate, CaptionStyleOut
from kairos.services.caption_engine.styler import PLATFORM_PRESETS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/captions", tags=["captions"])


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ── GET /api/captions/styles ──────────────────────────────────────────────────

@router.get("/styles", response_model=list[CaptionStyleOut])
def list_caption_styles(db: Session = Depends(get_db)):
    """List all CaptionStyle rows from the database."""
    return db.query(CaptionStyle).order_by(CaptionStyle.created_at.desc()).all()


# ── POST /api/captions/styles ─────────────────────────────────────────────────

@router.post("/styles", response_model=CaptionStyleOut, status_code=201)
def create_caption_style(req: CaptionStyleCreate, db: Session = Depends(get_db)):
    """Create a new CaptionStyle. Optionally seed from a platform_preset."""
    # Check unique name
    existing = db.query(CaptionStyle).filter(CaptionStyle.style_name == req.style_name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Style name '{req.style_name}' already exists")

    # If platform_preset provided, merge its defaults under any explicit values
    base: dict = {}
    if req.platform_preset and req.platform_preset in PLATFORM_PRESETS:
        base = PLATFORM_PRESETS[req.platform_preset].copy()

    style = CaptionStyle(
        style_id=str(uuid.uuid4()),
        style_name=req.style_name,
        platform_preset=req.platform_preset,
        font_name=req.font_name if req.font_name != "Arial" else base.get("font_name", req.font_name),
        font_size=req.font_size if req.font_size != 48 else base.get("font_size", req.font_size),
        font_color=req.font_color if req.font_color != "#FFFFFF" else base.get("font_color", req.font_color),
        outline_color=req.outline_color if req.outline_color != "#000000" else base.get("outline_color", req.outline_color),
        outline_width=req.outline_width if req.outline_width != 2 else base.get("outline_width", req.outline_width),
        shadow=req.shadow if req.shadow != 1 else base.get("shadow", req.shadow),
        animation_type=req.animation_type if req.animation_type is not None else base.get("animation_type"),
        position=req.position if req.position != "bottom" else base.get("position", req.position),
        style_params=req.style_params,
        created_at=_now(),
    )
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


# ── GET /api/captions/styles/{style_id} ──────────────────────────────────────

@router.get("/styles/{style_id}", response_model=CaptionStyleOut)
def get_caption_style(style_id: str, db: Session = Depends(get_db)):
    """Get a single CaptionStyle by ID."""
    style = db.query(CaptionStyle).filter(CaptionStyle.style_id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail=f"CaptionStyle {style_id} not found")
    return style


# ── PATCH /api/captions/styles/{style_id} ────────────────────────────────────

@router.patch("/styles/{style_id}", response_model=CaptionStyleOut)
def update_caption_style(
    style_id: str,
    updates: dict,
    db: Session = Depends(get_db),
):
    """Partial update of a CaptionStyle. Only provided fields are updated."""
    style = db.query(CaptionStyle).filter(CaptionStyle.style_id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail=f"CaptionStyle {style_id} not found")

    allowed_fields = {
        "style_name", "platform_preset", "font_name", "font_size",
        "font_color", "outline_color", "outline_width", "shadow",
        "animation_type", "position", "style_params",
    }

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(style, field, value)
        else:
            logger.warning("update_caption_style: ignoring unknown field '%s'", field)

    db.commit()
    db.refresh(style)
    return style


# ── DELETE /api/captions/styles/{style_id} ───────────────────────────────────

@router.delete("/styles/{style_id}")
def delete_caption_style(style_id: str, db: Session = Depends(get_db)):
    """Delete a CaptionStyle."""
    style = db.query(CaptionStyle).filter(CaptionStyle.style_id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail=f"CaptionStyle {style_id} not found")

    db.delete(style)
    db.commit()
    return {"deleted": True, "style_id": style_id}


# ── GET /api/captions/presets ─────────────────────────────────────────────────

@router.get("/presets")
def get_platform_presets():
    """Return the built-in PLATFORM_PRESETS dict (tiktok, youtube, instagram)."""
    return PLATFORM_PRESETS


# ── POST /api/captions/clips/{clip_id}/export ────────────────────────────────

@router.post("/clips/{clip_id}/export")
def export_clip_captions_endpoint(
    clip_id: str,
    fmt: str = Query("srt", description="srt | vtt | ass"),
    style_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Export captions for a single clip.
    Returns plain text content (SRT, VTT, or ASS format).
    """
    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

    if fmt not in ("srt", "vtt", "ass"):
        raise HTTPException(status_code=422, detail="fmt must be 'srt', 'vtt', or 'ass'")

    # Load style if provided
    style_dict: Optional[dict] = None
    if style_id:
        style_obj = db.query(CaptionStyle).filter(CaptionStyle.style_id == style_id).first()
        if not style_obj:
            raise HTTPException(status_code=404, detail=f"CaptionStyle {style_id} not found")
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

    from kairos.services.caption_engine.exporter import export_clip_captions
    content = export_clip_captions(db=db, clip_id=clip_id, fmt=fmt, style=style_dict)

    # Determine MIME type
    mime_map = {"srt": "text/plain", "vtt": "text/vtt", "ass": "text/plain"}
    media_type = mime_map.get(fmt, "text/plain")

    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{clip_id}.{fmt}"'},
    )


# ── POST /api/captions/timeline/{timeline_id}/generate ────────────────────────

@router.post("/timeline/{timeline_id}/generate")
def generate_timeline_captions_endpoint(
    timeline_id: str,
    style_id: Optional[str] = None,
    output_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Generate an ASS subtitle file for the full timeline.
    Writes to media/captions/{timeline_id}.ass (or custom output_name).
    Returns {"ass_path": str, "cue_count": int}
    """
    from kairos.config import BASE_DIR
    from kairos.models import Clip
    from kairos.services.caption_engine.generator import generate_timeline_captions
    from kairos.services.caption_engine.styler import get_default_style, write_ass_file

    timeline = db.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline {timeline_id} not found")

    # Load elements ordered by position
    elements = (
        db.query(TimelineElement)
        .filter(TimelineElement.timeline_id == timeline_id)
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

    # Build clip_file_map for clip elements
    clip_ids = [e["clip_id"] for e in elements_dicts if e.get("clip_id")]
    clips = db.query(Clip).filter(Clip.clip_id.in_(clip_ids)).all() if clip_ids else []
    clip_file_map = {c.clip_id: c.clip_file_path or "" for c in clips}

    # Load style
    style_dict: dict = get_default_style()
    if style_id:
        style_obj = db.query(CaptionStyle).filter(CaptionStyle.style_id == style_id).first()
        if not style_obj:
            raise HTTPException(status_code=404, detail=f"CaptionStyle {style_id} not found")
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

    # Generate captions
    captions = generate_timeline_captions(
        db=db,
        timeline_elements=elements_dicts,
        clip_file_map=clip_file_map,
        style=style_dict,
    )

    # Determine output resolution from timeline aspect_ratio
    from kairos.services.aspect_ratio.reframer import RESOLUTIONS
    resolution = RESOLUTIONS.get(timeline.aspect_ratio, (1920, 1080))

    # Output path
    captions_dir = BASE_DIR / "media" / "captions"
    captions_dir.mkdir(parents=True, exist_ok=True)

    fname = output_name if output_name else f"{timeline_id}.ass"
    if not fname.endswith(".ass"):
        fname += ".ass"
    ass_path = str(captions_dir / fname)

    write_ass_file(captions=captions, style=style_dict, output_path=ass_path, resolution=resolution)

    return {"ass_path": ass_path, "cue_count": len(captions)}
