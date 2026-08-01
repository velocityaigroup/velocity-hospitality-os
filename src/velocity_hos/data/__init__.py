"""Model-independent hospitality knowledge (SOP seed).

Retrieval, guardrails, citations and evaluation all operate on this data and are
completely independent of which LLM backend answers. Swap the model (local /
open-weights / Bedrock / …) and this knowledge layer is unchanged.
"""
from .sops_seed import SEED_SOPS

__all__ = ["SEED_SOPS"]
