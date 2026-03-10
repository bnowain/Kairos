"""
Load and validate story template JSON files from the templates/ directory.
"""

import json
import logging
from pathlib import Path

from kairos.config import TEMPLATES_DIR

logger = logging.getLogger(__name__)

_VALID_PACING = {"fast", "medium", "slow", "moderate"}
_REQUIRED_TEMPLATE_KEYS = {"template_id", "slots", "pacing", "target_duration_ms"}
_REQUIRED_SLOT_KEYS = {"slot_id", "position", "required", "max_clips", "score_signals"}


def list_templates() -> list[dict]:
    """Return all available templates (metadata only, not full slot definitions)."""
    results = []
    templates_path = Path(TEMPLATES_DIR)
    for json_file in sorted(templates_path.glob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "template_id":          data.get("template_id", json_file.stem),
                "template_name":        data.get("template_name", json_file.stem),
                "description":          data.get("description", ""),
                "pacing":               data.get("pacing", "medium"),
                "target_duration_ms":   data.get("target_duration_ms", 0),
                "aspect_ratio_default": data.get("aspect_ratio_default", "16:9"),
            })
        except Exception as exc:
            logger.warning("template_loader: could not read %s — %s", json_file.name, exc)
    return results


def load_template(template_id: str) -> dict:
    """
    Load and return a full template dict from templates/{template_id}.json.

    Raises FileNotFoundError if not found.
    Validates required keys: template_id, slots, pacing, target_duration_ms.
    """
    template_path = Path(TEMPLATES_DIR) / f"{template_id}.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template '{template_id}' not found at {template_path}")

    with open(template_path, encoding="utf-8") as f:
        data = json.load(f)

    missing = _REQUIRED_TEMPLATE_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Template '{template_id}' is missing required keys: {missing}")

    return data


def validate_template(template: dict) -> list[str]:
    """
    Return list of validation errors (empty list = valid).

    Checks:
    - Required top-level keys present
    - slots list is non-empty
    - Each slot has: slot_id, position, required, max_clips, score_signals
    - No duplicate slot positions
    - pacing in ['fast', 'medium', 'slow', 'moderate']
    """
    errors: list[str] = []

    # Required top-level keys
    for key in _REQUIRED_TEMPLATE_KEYS:
        if key not in template:
            errors.append(f"Missing required key: '{key}'")

    if errors:
        # Can't meaningfully continue without the basics
        return errors

    # slots non-empty
    slots = template.get("slots", [])
    if not isinstance(slots, list) or len(slots) == 0:
        errors.append("'slots' must be a non-empty list")
        return errors

    # Per-slot validation
    seen_positions: set[int] = set()
    for i, slot in enumerate(slots):
        label = slot.get("slot_id", f"slot[{i}]")
        for key in _REQUIRED_SLOT_KEYS:
            if key not in slot:
                errors.append(f"Slot '{label}': missing required key '{key}'")
        pos = slot.get("position")
        if pos is not None:
            if pos in seen_positions:
                errors.append(f"Slot '{label}': duplicate position {pos}")
            else:
                seen_positions.add(pos)

    # Pacing value
    pacing = template.get("pacing", "")
    if pacing not in _VALID_PACING:
        errors.append(
            f"'pacing' must be one of {sorted(_VALID_PACING)}, got '{pacing}'"
        )

    return errors
