"""3 - Workforce Planning Agent.

Produces staffing forecasts, plans for seasonal peaks, and recommends when and
whom to recruit before the season starts.
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class WorkforcePlanningAgent(Agent):
    name = "workforce_planning"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        forecast = ctx.inputs.get("occupancy_forecast", {})
        recs: list[Recommendation] = []
        for dept, gap in self._staffing_gaps(forecast).items():
            if gap > 0:
                recs.append(Recommendation(
                    agent=self.name,
                    summary=f"{dept}: short ~{gap} staff for forecast peak",
                    risk=RiskLevel.REQUIRES_APPROVAL,  # triggers recruitment spend
                    proposed_action={"type": "open_requisition", "dept": dept, "count": gap},
                    rationale="Projected demand exceeds current rostered capacity.",
                ))
        return recs

    @staticmethod
    def _staffing_gaps(forecast: dict) -> dict[str, int]:
        # TODO: real model. Placeholder: required - current per department.
        return {d: int(v.get("required", 0)) - int(v.get("current", 0))
                for d, v in forecast.items()}
