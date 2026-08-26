"""Velocity Demo Knowledge Base — schema, corpus, and RAG helpers."""
from __future__ import annotations

from .corpus import DEMO_SOPS, load_demo_kb
from .firefly import FIREFLY_GAPS, FIREFLY_SOPS, firefly_departments
from .evidence import FINDINGS, Finding, evidence_summary, live_findings
from .properties import (
    AZURE_BAY, DEFAULT_PROPERTY, FIREFLY, PROPERTIES, Property,
    get_property, property_index,
)
from .schema import SOP, DecisionBranch, QuizItem, retrieval_docs


def demo_retrieval_docs() -> dict[str, str]:
    """SOP id -> grounded retrieval text for the whole demo knowledge base.

    This is the exact shape the SOP Coach ingests (``ctx.sops``), so pointing the
    agent at the full knowledge base is a one-liner and needs no code change to swap
    in a design partner's real SOPs later.
    """
    return retrieval_docs(DEMO_SOPS)


def departments() -> list[str]:
    seen: list[str] = []
    for s in DEMO_SOPS:
        if s.department not in seen:
            seen.append(s.department)
    return seen


__all__ = [
    "SOP", "QuizItem", "DecisionBranch", "retrieval_docs",
    "DEMO_SOPS", "load_demo_kb", "demo_retrieval_docs", "departments",
    "FINDINGS", "Finding", "live_findings", "evidence_summary",
    "FIREFLY_SOPS", "FIREFLY_GAPS", "firefly_departments",
    "Property", "PROPERTIES", "DEFAULT_PROPERTY", "AZURE_BAY", "FIREFLY",
    "get_property", "property_index",
]
