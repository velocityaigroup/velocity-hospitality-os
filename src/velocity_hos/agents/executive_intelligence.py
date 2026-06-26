"""7 - Executive Intelligence Agent.

Delivers a daily executive briefing - risks, staffing alerts, revenue alerts, and
compliance alerts - across one or many properties.
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class ExecutiveIntelligenceAgent(Agent):
    name = "executive_intelligence"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        signals = ctx.inputs.get("signals", {})
        briefing = {
            "risks": signals.get("risks", []),
            "staffing_alerts": signals.get("staffing_alerts", []),
            "revenue_alerts": signals.get("revenue_alerts", []),
            "compliance_alerts": signals.get("compliance_alerts", []),
        }
        return [Recommendation(
            agent=self.name,
            summary="Daily executive briefing",
            risk=RiskLevel.INFO,
            proposed_action={"type": "briefing", "content": briefing},
            rationale="Cross-property roll-up for the GM/owner.",
        )]
