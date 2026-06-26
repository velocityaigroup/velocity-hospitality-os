"""2 - SOP Coach Agent.

Retrieves the right procedure on demand and answers "how do we do this here?"
against the property's own standards (RAG over the SOP store).
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class SOPCoachAgent(Agent):
    name = "sop_coach"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        question = ctx.inputs.get("question")
        if not question:
            return []
        # TODO: replace keyword match with vector retrieval over ctx.sops.
        hits = [k for k in ctx.sops if any(w in k.lower() for w in question.lower().split())]
        return [Recommendation(
            agent=self.name,
            summary=f"Answer for: {question!r}",
            risk=RiskLevel.INFO,
            proposed_action={"type": "answer", "sop_keys": hits},
            rationale="Role-specific guidance grounded in property SOPs.",
            sources=hits,
        )]
