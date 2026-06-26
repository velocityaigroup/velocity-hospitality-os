"""1 - HR Onboarding Agent.

Runs preboarding before arrival, tracks visas/work permits, collects documents,
and assigns training so an employee arrives already partly onboarded.
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class HROnboardingAgent(Agent):
    name = "hr_onboarding"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for hire in ctx.inputs.get("new_hires", []):
            missing = [d for d in ("passport", "work_permit", "contract")
                       if d not in hire.get("documents", [])]
            if missing:
                recs.append(Recommendation(
                    agent=self.name,
                    summary=f"{hire.get('name','New hire')} is missing: {', '.join(missing)}",
                    risk=RiskLevel.REQUIRES_APPROVAL,  # contacts a person
                    proposed_action={"type": "request_documents",
                                     "hire_id": hire.get("id"), "documents": missing},
                    rationale="Preboarding incomplete; documents required before start date.",
                ))
        return recs
