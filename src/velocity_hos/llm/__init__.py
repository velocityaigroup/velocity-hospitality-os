"""LLM + embeddings access with a pluggable backend.

Default backend is ``local`` (deterministic, no network) so tests and CI run
offline. Set ``VHOS_LLM_BACKEND`` to:
  - ``bedrock``     — Amazon Bedrock via the Converse API (any foundation model), needs AWS creds.
  - ``openweights`` — a self-hosted open-weights model (vLLM/TGI) on your GPU;
                      see ``velocity_hos.llm.openweights`` and the runbook.
"""
from __future__ import annotations

from velocity_hos.config import settings

from .base import LLM, Embeddings


def get_embeddings() -> Embeddings:
    # Embeddings can use a different backend from the LLM (settings.embed_backend),
    # so you can answer with a Bedrock foundation model while keeping offline embeddings.
    if settings.embed_backend == "bedrock":
        from .bedrock import BedrockEmbeddings
        return BedrockEmbeddings()
    if settings.embed_backend == "openweights":
        from .openweights import OpenWeightsEmbeddings
        return OpenWeightsEmbeddings()
    from .local import LocalEmbeddings
    return LocalEmbeddings()


def get_llm() -> LLM:
    if settings.llm_backend == "bedrock":
        from .bedrock import BedrockLLM
        return BedrockLLM()
    if settings.llm_backend == "openweights":
        from .openweights import OpenWeightsLLM
        return OpenWeightsLLM()
    from .local import LocalLLM
    return LocalLLM()


__all__ = ["LLM", "Embeddings", "get_embeddings", "get_llm"]
