"""6 - Guest Recovery Agent.

Analyses complaints, recommends recovery actions, and tracks follow-up to closure
so no guest issue falls through the cracks.
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class GuestRecoveryAgent(Agent):
    name = "guest_recovery"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for c in ctx.inputs.get("complaints", []):
            recs.append(Recommendation(
                agent=self.name,
                summary=f"Recovery for guest {c.get('guest_id')} (room {c.get('room')})",
                risk=RiskLevel.REQUIRES_APPROVAL,  # touches the guest relationship
                proposed_action={"type": "recovery_offer", "complaint_id": c.get("id"),
                                 "suggestion": c.get("suggested_remedy", "manager follow-up")},
                rationale="Complaint open; recovery + follow-up to closure recommended.",
            ))
        return recs
