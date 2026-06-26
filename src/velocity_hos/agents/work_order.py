"""4 - Work Order Agent.

Triages maintenance and guest-request tickets, scores priority, and routes
escalations to the right owner with an SLA.
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel

_PRIORITY = {"safety": 1, "vip": 2, "comfort": 3, "cosmetic": 4}


class WorkOrderAgent(Agent):
    name = "work_order"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for t in sorted(ctx.inputs.get("tickets", []),
                        key=lambda x: _PRIORITY.get(x.get("category", "cosmetic"), 9)):
            recs.append(Recommendation(
                agent=self.name,
                summary=f"Route ticket {t.get('id')} ({t.get('category')}) to {t.get('owner','owner')}",
                risk=RiskLevel.LOW,  # internal routing
                proposed_action={"type": "assign", "ticket_id": t.get("id"),
                                 "priority": _PRIORITY.get(t.get("category", "cosmetic"), 9)},
                rationale="Priority-scored and SLA-routed.",
            ))
        return recs
