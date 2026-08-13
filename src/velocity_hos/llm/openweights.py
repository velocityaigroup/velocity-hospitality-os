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


def _post(path: str, payload: dict, timeout: float = 60.0) -> dict:
    """POST JSON to the OpenAI-compatible server and return the parsed response."""
    url = settings.openweights_base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.openweights_api_key:
        headers["Authorization"] = f"Bearer {settings.openweights_api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
