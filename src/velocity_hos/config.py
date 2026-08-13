"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")

    # LLM backend: "local" (offline, default), "bedrock", or "openweights"
    llm_backend: str = os.getenv("VHOS_LLM_BACKEND", "local")
    # Embeddings backend. Empty = follow llm_backend. Set VHOS_EMBED_BACKEND=local to
    # run a Bedrock foundation model for answers while keeping offline embeddings — so you
    # can go live without also enabling a Bedrock embeddings model.
    embed_backend: str = os.getenv("VHOS_EMBED_BACKEND", "") or llm_backend
    # Bedrock uses the Converse API (foundation-model agnostic). Default to a foundation
    # model available on the account; set BEDROCK_MODEL_ID to switch to any other
    # Converse-capable foundation model — a config change, never a code change.
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    embed_model_id: str = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")

    # Open-weights backend — the OFFICIAL Velocity deployment. An OpenAI-compatible
    # server (vLLM) serving an open-weights model on self-hosted GPU. See
    # docs/openweights-runbook.md. Default target = the H200 production model; override
    # VHOS_OPENWEIGHTS_MODEL to a small model when proving the path locally via Ollama.
    openweights_base_url: str = os.getenv("VHOS_OPENWEIGHTS_URL", "http://localhost:8000/v1")
    openweights_model: str = os.getenv("VHOS_OPENWEIGHTS_MODEL", "Qwen/Qwen3.6-27B-Instruct")
    openweights_embed_model: str = os.getenv(
        "VHOS_OPENWEIGHTS_EMBED_MODEL", "BAAI/bge-small-en-v1.5"
    )
    openweights_api_key: str | None = os.getenv("VHOS_OPENWEIGHTS_API_KEY") or None
    # Reasoning models (e.g. Qwen 3.x) emit chain-of-thought before the answer. When
    # true (default) the provider suppresses it (Qwen "/no_think" hint) and strips any
    # <think>…</think> block, so staff/judges see the concise final answer only.
    openweights_no_think: bool = os.getenv("VHOS_OPENWEIGHTS_NO_THINK", "1") not in ("0", "false", "False", "")

    # DynamoDB tables (per-tenant isolation)
    state_table: str = os.getenv("DDB_STATE_TABLE", "vhos-state")
    audit_table: str = os.getenv("DDB_AUDIT_TABLE", "vhos-audit")

    # Approval routing
    approval_webhook_url: str | None = os.getenv("APPROVAL_WEBHOOK_URL") or None


settings = Settings()
