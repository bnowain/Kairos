"""
LLM-based highlight and virality analysis via Ollama.
Model is configured in config.py (OLLAMA_MODEL, default: llama3).

Segments are sent to Ollama in batches of 20 to fit context window.
Returns per-segment virality, hook, emotional, and controversy scores.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are analyzing a video transcript to identify the most engaging highlight clips.

For each segment below, score it from 0.0 to 1.0 on:
- virality_score: How likely this clip would go viral on social media
- hook_score: How strong this would be as an opening hook (strong claim, surprising statement)
- emotional_score: Emotional intensity (anger, excitement, sadness, humor)
- controversy_score: Controversial claim, contradiction, or confrontational moment

Also provide:
- highlight_reason: One sentence explaining why this segment is or isn't notable
- is_hook_candidate: true/false

Return ONLY a JSON array, one object per segment, in the same order as input.

Segments:
{segments_json}
"""

BATCH_SIZE = 20


def _default_scores(segment_id: str) -> dict:
    """Return neutral default scores when LLM is unavailable."""
    return {
        "segment_id": segment_id,
        "virality_score": 0.5,
        "hook_score": 0.0,
        "emotional_score": 0.0,
        "controversy_score": 0.0,
        "highlight_reason": "",
        "is_hook_candidate": False,
    }


def _clamp(v, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _parse_llm_response(raw_text: str, batch: list[dict]) -> list[dict]:
    """
    Parse LLM JSON response robustly.
    Handles markdown code fences, extra text before/after JSON array.
    Falls back to defaults for any unparseable segments.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if "```" in text:
        lines = text.splitlines()
        cleaned = []
        in_fence = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence or in_fence:
                cleaned.append(line)
        text = "\n".join(cleaned).strip()

    # Extract the JSON array portion
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("llm_analyzer: no JSON array found in response, using defaults")
        return [_default_scores(seg.get("segment_id", "")) for seg in batch]

    json_text = text[start : end + 1]

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        logger.warning("llm_analyzer: JSON parse error (%s), using defaults", exc)
        return [_default_scores(seg.get("segment_id", "")) for seg in batch]

    if not isinstance(parsed, list):
        logger.warning("llm_analyzer: parsed JSON is not a list, using defaults")
        return [_default_scores(seg.get("segment_id", "")) for seg in batch]

    results = []
    for i, seg in enumerate(batch):
        seg_id = seg.get("segment_id", "")
        if i < len(parsed) and isinstance(parsed[i], dict):
            raw = parsed[i]
            results.append({
                "segment_id":        seg_id,
                "virality_score":    _clamp(raw.get("virality_score", 0.5)),
                "hook_score":        _clamp(raw.get("hook_score", 0.0)),
                "emotional_score":   _clamp(raw.get("emotional_score", 0.0)),
                "controversy_score": _clamp(raw.get("controversy_score", 0.0)),
                "highlight_reason":  str(raw.get("highlight_reason", ""))[:500],
                "is_hook_candidate": bool(raw.get("is_hook_candidate", False)),
            })
        else:
            results.append(_default_scores(seg_id))

    return results


def analyze_segments(segments: list[dict], item_title: str = "") -> list[dict]:
    """
    Analyze a list of transcript segments for highlight potential.

    Sends segments to Ollama in batches of 20 (to fit context window).
    For each segment returns:
        {
            "segment_id": str,
            "virality_score": float,    # 0.0-1.0
            "hook_score": float,        # 0.0-1.0 (good opening line?)
            "emotional_score": float,   # 0.0-1.0
            "controversy_score": float, # 0.0-1.0
            "highlight_reason": str,    # brief explanation
            "is_hook_candidate": bool,
        }

    On Ollama connection error: logs warning, returns default scores (0.5 virality).
    """
    from kairos.config import OLLAMA_HOST, OLLAMA_MODEL

    if not segments:
        return []

    try:
        import ollama
    except ImportError:
        logger.warning("llm_analyzer: ollama package not installed — returning defaults")
        return [_default_scores(seg.get("segment_id", "")) for seg in segments]

    client = ollama.Client(host=OLLAMA_HOST)
    all_results: list[dict] = []

    for batch_start in range(0, len(segments), BATCH_SIZE):
        batch = segments[batch_start : batch_start + BATCH_SIZE]

        # Build compact representation for the prompt
        segments_for_prompt = []
        for seg in batch:
            start_s = seg.get("start_ms", 0) / 1000.0
            end_s = seg.get("end_ms", 0) / 1000.0
            segments_for_prompt.append({
                "segment_id": seg.get("segment_id", ""),
                "start":      f"{start_s:.1f}s",
                "end":        f"{end_s:.1f}s",
                "speaker":    seg.get("speaker_label") or "unknown",
                "text":       seg.get("segment_text", ""),
            })

        prompt = ANALYSIS_PROMPT.format(
            segments_json=json.dumps(segments_for_prompt, indent=2)
        )
        if item_title:
            prompt = f"Video title: {item_title}\n\n" + prompt

        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )
            raw_text = response.get("message", {}).get("content", "")
            batch_results = _parse_llm_response(raw_text, batch)
        except Exception as exc:
            logger.warning(
                "llm_analyzer: Ollama error for batch %d-%d (%s) — using defaults",
                batch_start, batch_start + len(batch) - 1, exc,
            )
            batch_results = [_default_scores(seg.get("segment_id", "")) for seg in batch]

        all_results.extend(batch_results)
        logger.info(
            "llm_analyzer: scored batch %d-%d (%d segments)",
            batch_start, batch_start + len(batch) - 1, len(batch),
        )

    return all_results
