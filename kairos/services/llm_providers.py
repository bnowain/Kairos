"""
Shared LLM provider backends for Kairos.

Used by both the analysis pipeline (llm_analyzer.py) and the Smart Query
intent scorer. Each provider takes a prompt string and returns raw response text.

Providers:
  - ollama           — direct Ollama API (local inference)
  - mission_control  — routes through Mission Control /models/run
  - claude_cli       — shells out to `claude -p` (authenticated account)
"""

import json
import logging
import subprocess
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


def call_ollama(prompt: str) -> str:
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


def call_mission_control(prompt: str) -> str:
    """Send prompt to Mission Control /models/run and return response text."""
    from kairos.config import MC_HOST, MC_MODEL_ID, OLLAMA_MODEL

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


def call_claude_cli(prompt: str) -> str:
    """Send prompt to Claude Code CLI via `claude -p` and return response text."""
    result = subprocess.run(
        ["claude", "-p"],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"claude -p exited {result.returncode}: {stderr}")
    return result.stdout


def get_provider(provider_name: str | None = None):
    """
    Return (call_fn, provider_name) for the given provider.
    If provider_name is None, uses the default from LLM_PROVIDER config.
    """
    if provider_name is None:
        from kairos.config import LLM_PROVIDER
        provider_name = LLM_PROVIDER

    if provider_name == "mission_control":
        return call_mission_control, "mission_control"
    elif provider_name == "claude_cli":
        return call_claude_cli, "claude_cli"
    else:
        return call_ollama, "ollama"


def get_model_id(provider_name: str | None = None) -> str:
    """Return a human-readable model identifier for the current provider."""
    if provider_name is None:
        from kairos.config import LLM_PROVIDER
        provider_name = LLM_PROVIDER

    if provider_name == "mission_control":
        from kairos.config import MC_MODEL_ID, OLLAMA_MODEL
        return MC_MODEL_ID or f"ollama/{OLLAMA_MODEL}"
    elif provider_name == "claude_cli":
        return "claude_cli"
    else:
        from kairos.config import OLLAMA_MODEL
        return OLLAMA_MODEL
