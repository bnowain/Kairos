"""
LLM-based highlight and virality analysis.

Supports two providers (configured via LLM_PROVIDER env var):
  - "ollama"           — direct Ollama API (default, local inference)
  - "mission_control"  — routes through Mission Control /models/run
                         (MC handles model routing, telemetry, fallbacks)

Segments are sent in batches of 20 to fit context windows.
Returns per-segment virality, hook, emotional, and controversy scores.
"""

import json
import logging
import urllib.request
import urllib.error
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


# ── Provider backends ────────────────────────────────────────────────────────

def _call_ollama(prompt: str) -> str:
    """Send prompt to Ollama and return raw response text."""
    from kairos.config import OLLAMA_HOST, OLLAMA_MODEL

    import ollama
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1},
    )
    return response.get("message", {}).get("content", "")


def _call_mission_control(prompt: str) -> str:
    """Send prompt to Mission Control /models/run and return response text."""
    from kairos.config import MC_HOST, MC_MODEL_ID, OLLAMA_MODEL

    # model_id is required by MC — fall back to ollama model format if not configured
    model_id = MC_MODEL_ID or f"ollama/{OLLAMA_MODEL}"

    body: dict = {
        "model_id": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    url = f"{MC_HOST}/models/run"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response_text", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise RuntimeError(f"Mission Control returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Mission Control unreachable at {url}: {exc.reason}") from exc


def _get_provider_fn():
    """Return the appropriate LLM call function based on LLM_PROVIDER config."""
    from kairos.config import LLM_PROVIDER

    if LLM_PROVIDER == "mission_control":
        return _call_mission_control, "mission_control"
    else:
        return _call_ollama, "ollama"


# ── Main entry point ─────────────────────────────────────────────────────────

def analyze_segments(segments: list[dict], item_title: str = "") -> list[dict]:
    """
    Analyze a list of transcript segments for highlight potential.

    Sends segments to the configured LLM provider in batches of 20.
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

    On provider error: logs warning, returns default scores (0.5 virality).
    """
    if not segments:
        return []

    try:
        call_fn, provider_name = _get_provider_fn()
    except Exception as exc:
        logger.warning("llm_analyzer: failed to init provider (%s) — returning defaults", exc)
        return [_default_scores(seg.get("segment_id", "")) for seg in segments]

    # For ollama provider, check import availability
    if provider_name == "ollama":
        try:
            import ollama  # noqa: F401
        except ImportError:
            logger.warning("llm_analyzer: ollama package not installed — returning defaults")
            return [_default_scores(seg.get("segment_id", "")) for seg in segments]

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
            raw_text = call_fn(prompt)
            batch_results = _parse_llm_response(raw_text, batch)
        except Exception as exc:
            logger.warning(
                "llm_analyzer: %s error for batch %d-%d (%s) — using defaults",
                provider_name, batch_start, batch_start + len(batch) - 1, exc,
            )
            batch_results = [_default_scores(seg.get("segment_id", "")) for seg in batch]

        all_results.extend(batch_results)
        logger.info(
            "llm_analyzer: scored batch %d-%d (%d segments) via %s",
            batch_start, batch_start + len(batch) - 1, len(batch), provider_name,
        )

    return all_results
