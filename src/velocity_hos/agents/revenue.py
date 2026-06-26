"""5 - Revenue Agent.

Surfaces upsell opportunities, detects revenue leakage, and enforces pricing and
pour consistency (the Beverage Logic Engine).
"""
from __future__ import annotations

from .base import Agent, Context, Recommendation, RiskLevel


class RevenueAgent(Agent):
    name = "revenue"

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        recs: list[Recommendation] = []
        # Pour/pricing consistency: same SKU charged at different prices.
        prices: dict[str, set] = {}
        for line in ctx.inputs.get("pos_lines", []):
            prices.setdefault(line["sku"], set()).add(line["price"])
        for sku, seen in prices.items():
            if len(seen) > 1:
                recs.append(Recommendation(
                    agent=self.name,
                    summary=f"Pricing inconsistency on {sku}: {sorted(seen)}",
                    risk=RiskLevel.REQUIRES_APPROVAL,  # changes money
                    proposed_action={"type": "flag_pricing", "sku": sku},
                    rationale="Same item charged multiple ways — likely leakage.",
                ))
        return recs
