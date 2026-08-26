"""Open-weights backend: an OpenAI-compatible server (vLLM / TGI) on your GPU.

This lets Velocity run entirely on a self-hosted open-weights model served on the
Buildathon's provided H200 compute — no managed-API dependency — while keeping the
exact same ``LLM`` / ``Embeddings`` interface as the local and Bedrock backends. The
model id is config-driven (``settings.openweights_model``); confirm the exact
Hugging Face repo id for the model you serve.

Serve a model with vLLM (see docs/openweights-runbook.md), then:

    export VHOS_LLM_BACKEND=openweights
    export VHOS_OPENWEIGHTS_URL=http://<gpu-host>:8000/v1
    export VHOS_OPENWEIGHTS_MODEL=<hf-repo-id-you-served>

Uses only the standard library (urllib) so it adds no dependency and imports
cleanly with no server running.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from velocity_hos.config import settings

from .base import (
    BRIEFING_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_prompt,
    render_sections,
)

# Matches a reasoning model's chain-of-thought block, e.g. Qwen's <think>…</think>.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    """Return only the final answer: remove any <think>…</think> block (and a
    dangling, unclosed <think> preamble) that reasoning models emit."""
    text = _THINK_RE.sub("", text)
    # Unclosed <think> (truncated/streamed): drop everything up to the last </think>,
    # else everything before an explicit final-answer marker if present.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]
    elif "<think>" in text:
        text = text.split("<think>", 1)[0]
    return text.strip()


# Transient upstream conditions on a shared inference gateway. These are worth
# retrying; a 400/404/422 (bad request, wrong model, unsupported field) is not,
# and must surface immediately so the caller's own fallback logic can run.
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 3.0)


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    """Honour a Retry-After header when the gateway sends one (seconds only)."""
    try:
        value = exc.headers.get("Retry-After") if exc.headers else None
        return max(0.0, min(30.0, float(value))) if value else None
    except (TypeError, ValueError):
        return None


def _post(path: str, payload: dict, timeout: float = 90.0) -> dict:
    """POST JSON to the OpenAI-compatible server and return the parsed response.

    Retries transient gateway failures with backoff. A shared gateway will
    occasionally return 502/503 or drop a long generation; one such blip should
    not end a four-agent cycle that is otherwise working.
    """
    url = settings.openweights_base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.openweights_api_key:
        headers["Authorization"] = f"Bearer {settings.openweights_api_key}"

    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                raise
            last_exc = exc
            delay = _retry_after(exc) or _BACKOFF_SECONDS[attempt]
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            last_exc = exc
            delay = _BACKOFF_SECONDS[attempt]
        print(
            f"     [retry] {type(last_exc).__name__}: {last_exc} "
            f"- attempt {attempt + 1}/{_MAX_ATTEMPTS}, retrying in {delay:.0f}s",
            flush=True,
        )
        time.sleep(delay)

    raise RuntimeError("unreachable")  # pragma: no cover


def _chat(system: str, user: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
    no_think = settings.openweights_no_think
    if no_think:
        # Belt-and-suspenders CoT suppression on reasoning models (e.g. Qwen 3.x):
        system = system + "\n\nAnswer with only the final response. Do not show your reasoning."
        user = user + " /no_think"
    payload = {
        "model": settings.openweights_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # Reasoning models spend tokens "thinking"; give headroom so the final
        # answer isn't truncated even if some reasoning slips through.
        "max_tokens": max_tokens if not no_think else max(max_tokens, 768),
        "temperature": temperature,
    }
    if no_think:
        # Primary lever: turn off the model's thinking phase at the chat-template
        # level (Qwen/vLLM). Sent via extra body; if the gateway rejects the field
        # we retry without it and fall back to the hints + strip above.
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    try:
        resp = _post("/chat/completions", payload)
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        if no_think and exc.code in (400, 404, 422) and "chat_template_kwargs" in payload:
            payload.pop("chat_template_kwargs")
            resp = _post("/chat/completions", payload)
        else:
            raise

    content = resp["choices"][0]["message"]["content"]
    return _strip_reasoning(content) if no_think else content.strip()


class OpenWeightsLLM:
    """Chat completion against a self-hosted open-weights model."""

    def answer(self, question: str, contexts: list[str]) -> str:
        return _chat(SYSTEM_PROMPT, build_prompt(question, contexts))

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        user = f"{instruction}\n\nAlerts:\n{render_sections(sections)}"
        return _chat(BRIEFING_SYSTEM_PROMPT, user)


class OpenWeightsEmbeddings:
    """Embeddings against an OpenAI-compatible /embeddings endpoint."""

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.openweights_embed_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = _post("/embeddings", {"model": self.model_id, "input": texts})
        # OpenAI schema returns data sorted by index; sort defensively.
        rows = sorted(resp["data"], key=lambda d: d.get("index", 0))
        return [row["embedding"] for row in rows]
