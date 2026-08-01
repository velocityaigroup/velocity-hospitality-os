"""Open-weights backend: an OpenAI-compatible server (vLLM / TGI) on your GPU.

This lets Velocity run entirely on open-weights models (e.g. Llama-3.1) served on
the Buildathon's provided H200 compute — no managed-API dependency — while keeping
the exact same ``LLM`` / ``Embeddings`` interface as the local and Bedrock backends.

Serve a model with vLLM (see docs/openweights-runbook.md), then:

    export VHOS_LLM_BACKEND=openweights
    export VHOS_OPENWEIGHTS_URL=http://<gpu-host>:8000/v1
    export VHOS_OPENWEIGHTS_MODEL=meta-llama/Llama-3.1-8B-Instruct

Uses only the standard library (urllib) so it adds no dependency and imports
cleanly with no server running.
"""
from __future__ import annotations

import json
import urllib.request

from velocity_hos.config import settings

from .base import (
    BRIEFING_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_prompt,
    render_sections,
)


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
    resp = _post("/chat/completions", {
        "model": settings.openweights_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    })
    return resp["choices"][0]["message"]["content"].strip()


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
