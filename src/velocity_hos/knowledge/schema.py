"""Velocity Demo Knowledge Base — the SOP schema.

A production-grade, model-independent representation of a hotel Standard Operating
Procedure. It is deliberately rich (every field a hotel's L&D / operations team
would expect) AND designed for RAG ingestion: ``to_retrieval_text()`` flattens an
SOP into the grounded context the SOP Coach retrieves over, while the structured
fields power quizzes, decision support, KPIs, and cross-references.

This is ORIGINAL content authored to international luxury-hospitality standards — no
proprietary or copyrighted documentation. Any property (including a design partner)
can replace the demo corpus with their own SOPs with zero code change: same schema,
same retrieval, same guardrails.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class QuizItem:
    question: str
    answer: str


@dataclass
class DecisionBranch:
    """One branch of an operational decision tree: if <condition> then <action>."""
    condition: str
    action: str


@dataclass
class SOP:
    # --- identity ---
    sop_id: str                       # e.g. "FO-101"
    title: str
    department: str                   # e.g. "Front Office"
    # --- the "why" ---
    purpose: str
    business_outcome: str
    scope: str
    # --- ownership & systems ---
    roles_responsible: list[str] = field(default_factory=list)
    required_systems: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    # --- the "how" ---
    procedure: list[str] = field(default_factory=list)          # ordered steps
    decision_tree: list[DecisionBranch] = field(default_factory=list)
    escalation_rules: list[str] = field(default_factory=list)
    quality_standards: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    # --- AI / retrieval affordances ---
    ai_summary: str = ""
    related_sops: list[str] = field(default_factory=list)
    search_keywords: list[str] = field(default_factory=list)
    quiz: list[QuizItem] = field(default_factory=list)
    follow_up_actions: list[str] = field(default_factory=list)
    # --- metadata ---
    category_tags: list[str] = field(default_factory=list)
    priority: str = "standard"        # critical | high | standard
    version: str = "1.0"
    approval_status: str = "approved" # approved | draft | in_review
    # --- provenance (per-property governance) ---
    # "authored"           - written by Velocity for the demo corpus
    # "unconfirmed"        - seeded from a public source, NOT yet confirmed by the operator
    # "operator_confirmed" - the property has confirmed this fact in writing
    # An agent may state an unconfirmed fact only with its provenance visible; nothing
    # is promoted to operator_confirmed without the operator saying so.
    confidence: str = "authored"
    source: str = ""                  # where the content came from (page key / document)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def from_dict(d: dict[str, Any]) -> "SOP":
        d = dict(d)
        d["quiz"] = [QuizItem(**q) if isinstance(q, dict) else q for q in d.get("quiz", [])]
        d["decision_tree"] = [
            DecisionBranch(**b) if isinstance(b, dict) else b
            for b in d.get("decision_tree", [])
        ]
        allowed = SOP.__dataclass_fields__.keys()
        return SOP(**{k: v for k, v in d.items() if k in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_retrieval_text(self) -> str:
        """Flatten to the grounded passage the SOP Coach retrieves and cites.

        Includes the human-readable procedure, decision logic, escalation, quality
        bar, and keywords so both semantic and keyword retrieval land on it.
        """
        parts = [f"{self.sop_id} — {self.title} ({self.department})",
                 f"Purpose: {self.purpose}"]
        if self.scope:
            parts.append(f"Scope: {self.scope}")
        if self.procedure:
            steps = " ".join(f"{i+1}) {s}" for i, s in enumerate(self.procedure))
            parts.append(f"Procedure: {steps}")
        if self.decision_tree:
            dt = " ".join(f"If {b.condition}, then {b.action}." for b in self.decision_tree)
            parts.append(f"Decisions: {dt}")
        if self.escalation_rules:
            parts.append("Escalation: " + " ".join(self.escalation_rules))
        if self.quality_standards:
            parts.append("Quality standard: " + " ".join(self.quality_standards))
        if self.search_keywords:
            parts.append("Keywords: " + ", ".join(self.search_keywords))
        return "\n".join(parts)

    def search_text(self) -> str:
        """All text a keyword search should match against."""
        return " ".join([
            self.sop_id, self.title, self.department, self.purpose, self.ai_summary,
            " ".join(self.search_keywords), " ".join(self.category_tags),
            " ".join(self.procedure),
        ]).lower()


def retrieval_docs(sops: list[SOP]) -> dict[str, str]:
    """Map SOP id -> retrieval text, the exact shape the SOP Coach ingests."""
    return {s.sop_id: s.to_retrieval_text() for s in sops}
