"""Amazon Bedrock backend: Titan Text Embeddings v2 + Claude (messages API).

boto3 is imported lazily so the package imports cleanly without AWS installed.
Requires AWS credentials and Bedrock model access enabled in the target region.
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


def _claude(client, model_id: str, system: str, user: str,
            max_tokens: int = 512, temperature: float = 0.2) -> str:
    resp = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
        }),
    )
    payload = json.loads(resp["body"].read())
    return payload["content"][0]["text"].strip()


class BedrockEmbeddings:
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
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.bedrock_model_id

    def answer(self, question: str, contexts: list[str]) -> str:
        return _claude(_client(), self.model_id, SYSTEM_PROMPT,
                       build_prompt(question, contexts))

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        user = f"{instruction}\n\nAlerts:\n{render_sections(sections)}"
        return _claude(_client(), self.model_id, BRIEFING_SYSTEM_PROMPT, user)
