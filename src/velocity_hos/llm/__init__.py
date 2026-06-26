"""LLM + embeddings access with a pluggable backend.

Default backend is ``local`` (deterministic, no network) so tests and CI run
offline. Set ``VHOS_LLM_BACKEND=bedrock`` (with AWS credentials configured) to
use Amazon Bedrock — Titan for embeddings and Claude for answering.
"""
from __future__ import annotations

from velocity_hos.config import settings
from .base import Embeddings, LLM


def get_embeddings() -> Embeddings:
    if settings.llm_backend == "bedrock":
        from .bedrock import BedrockEmbeddings
        return BedrockEmbeddings()
    from .local import LocalEmbeddings
    return LocalEmbeddings()


def get_llm() -> LLM:
    if settings.llm_backend == "bedrock":
        from .bedrock import BedrockLLM
        return BedrockLLM()
    from .local import LocalLLM
    return LocalLLM()


__all__ = ["Embeddings", "LLM", "get_embeddings", "get_llm"]
