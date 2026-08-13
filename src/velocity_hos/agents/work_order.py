"""4 - Work Order Agent (grounded + human-gated).

Triages maintenance and guest-request tickets against the property's own
maintenance/safety standards, scores priority, computes an SLA, and routes each
ticket to the right owner — routing consequential work (anything safety-critical,
guest-impacting, or above a cost threshold) through the human-approval gate rather
than acting on it autonomously.

Why this matters for the loop: the Work Order agent is where "an event happened in
the building" becomes "a prioritised, owned, SLA-bound action grounded in our own
standards" — and where a human stays in control of the calls that touch guest
safety, the guest relationship, or money. Routine work (a dripping tap, a scuff
mark) is auto-routed and logged; the judgement calls are held for a person.

Grounding: each ticket is matched against the retrieved SOPs (the same retriever
the SOP Coach uses), so the routing decision cites the standard that governs it and
appears, with its source, in the inspectable decision trail. If nothing in the
property's standards covers the ticket it is still routed, but flagged as having no
governing SOP so a human can close the gap.
"""
from __future__ import annotations

from velocity_hos.rag import Retriever, overlap_score

from .base import Agent, Context, Recommendation, RiskLevel

# Category -> (priority rank, SLA hours, default owner).
# Lower rank = more urgent. SLA is the time-to-response the property commits to.
_CATEGORY = {
    "safety":   (1, 1,  "Engineering / Duty Manager"),
    "vip":      (2, 4,  "Duty Manager"),
    "comfort":  (3, 24, "Maintenance"),
    "cosmetic": (4, 72, "Maintenance"),
}
_UNKNOWN = (9, 72, "Maintenance")


class WorkOrderAgent(Agent):
    """Prioritise, ground, SLA, and human-gate maintenance/guest-request tickets."""

    name = "work_order"

    def __init__(
        self,
        embeddings=None,
        top_k: int = 1,
        min_overlap: int = 2,
        approval_cost_threshold: float = 500.0,
    ):
        # Reuse the shared retriever so routing grounds on the SAME SOP library the
        # SOP Coach answers from — one knowledge base, cited consistently.
        from velocity_hos.llm import get_embeddings
        self._retriever = Retriever(embeddings or get_embeddings())
        self.top_k = top_k
        # Require two topical matches so a single incidental word (e.g. "guest")
        # doesn't falsely bind a ticket to an unrelated SOP — same guardrail the
        # SOP Coach uses to avoid grounding on thin air.
        self.min_overlap = min_overlap
        # Work above this estimated cost is held for a human even if low-urgency —
        # spend is a consequential action, like safety and the guest relationship.
        self.approval_cost_threshold = approval_cost_threshold

    # ------------------------------------------------------------------ helpers
    def _ground(self, ctx: Context, ticket: dict) -> list[str]:
        """Return the SOP id(s) that govern this ticket, or [] if none applies."""
        if not ctx.sops:
            return []
        self._retriever.ingest(ctx.sops)
        query = f"{ticket.get('category', '')} {ticket.get('description', '')}".strip()
        if not query:
            return []
        hits = self._retriever.query(query, k=self.top_k)
        contexts = [str(ctx.sops.get(h.doc_id, h.text)) for h in hits]
        if overlap_score(query, contexts) >= self.min_overlap:
            return [h.doc_id for h in hits]
        return []

    @staticmethod
    def _requires_approval(category: str, cost: float, threshold: float) -> bool:
        """Consequential = safety, the guest relationship (VIP), or real spend."""
        return category in ("safety", "vip") or cost >= threshold

    # ------------------------------------------------------------------ evaluate
    def evaluate(self, ctx: Context) -> list[Recommendation]:
        tickets = ctx.inputs.get("tickets", [])
        recs: list[Recommendation] = []

        # Most urgent first — the order a duty manager should see them.
        for t in sorted(tickets, key=lambda x: _CATEGORY.get(
                x.get("category", ""), _UNKNOWN)[0]):
            category = t.get("category", "")
            rank, sla_hours, default_owner = _CATEGORY.get(category, _UNKNOWN)
            owner = t.get("owner") or default_owner
            cost = float(t.get("cost_estimate", 0) or 0)
            sources = self._ground(ctx, t)

            hold = self._requires_approval(category, cost, self.approval_cost_threshold)
            risk = RiskLevel.REQUIRES_APPROVAL if hold else RiskLevel.LOW

            desc = t.get("description", "").strip()
            gate = "approval required" if hold else f"auto-route · SLA {sla_hours}h"
            summary = (f"P{rank} · {t.get('id','WO')} ({category or 'general'}): "
                       f"{desc[:80]} → {owner} — {gate}")

            why = [f"Priority P{rank}, SLA {sla_hours}h."]
            if hold:
                if category == "safety":
                    why.append("Safety-critical — held for a human before dispatch.")
                elif category == "vip":
                    why.append("Touches an in-house guest — held for Duty Manager review.")
                if cost >= self.approval_cost_threshold:
                    why.append(f"Estimated spend €{cost:.0f} exceeds the approval threshold.")
            if sources:
                why.append(f"Governed by {', '.join(sources)}.")
            else:
                why.append("No governing SOP matched — flagged so a human can close the gap.")

            recs.append(Recommendation(
                agent=self.name,
                summary=summary,
                risk=risk,
                proposed_action={
                    "type": "work_order",
                    "ticket_id": t.get("id"),
                    "category": category,
                    "priority": rank,
                    "sla_hours": sla_hours,
                    "owner": owner,
                    "cost_estimate": cost,
                    "requires_approval": hold,
                },
                rationale=" ".join(why),
                sources=sources,
            ))
        return recs
