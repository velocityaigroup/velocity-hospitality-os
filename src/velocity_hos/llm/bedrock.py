"""Amazon Bedrock backend via the Converse API (model-family agnostic).

Converse gives one request/response shape across every Bedrock foundation model —
no model-specific request formatting anywhere — so switching foundation models is a
config change, never a code change. Default model is set in config (a foundation
model available on the account); set BEDROCK_MODEL_ID to switch to any other.

boto3 is imported lazily so the package imports cleanly without AWS installed.
Embeddings use Amazon Titan (only needed if VHOS_EMBED_BACKEND=bedrock).
"""
from __future__ import annotations

import json

from velocity_hos.config import settings
from .base import (
    BRIEFING_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_prompt,
    render_sections,
)


def _client():
    import boto3  # lazy
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _converse(client, model_id: str, system: str, user: str,
              max_tokens: int = 512, temperature: float = 0.2) -> str:
    """One call shape for every Bedrock foundation model — no per-model formatting."""
    resp = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return resp["output"]["message"]["content"][0]["text"].strip()


class BedrockEmbeddings:
    """Amazon Titan Text Embeddings (only used if VHOS_EMBED_BACKEND=bedrock)."""

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.embed_model_id

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = _client()
        out: list[list[float]] = []
        for text in texts:
            resp = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({"inputText": text}),
            )
            payload = json.loads(resp["body"].read())
            out.append(payload["embedding"])
        return out


class BedrockLLM:
    """Answering via Bedrock Converse — works with any Converse-capable foundation model."""

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.bedrock_model_id

    def answer(self, question: str, contexts: list[str]) -> str:
        return _converse(_client(), self.model_id, SYSTEM_PROMPT,
                         build_prompt(question, contexts))

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        user = f"{instruction}\n\nAlerts:\n{render_sections(sections)}"
        return _converse(_client(), self.model_id, BRIEFING_SYSTEM_PROMPT, user)
