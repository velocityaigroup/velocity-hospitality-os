"""The execution loop: Inputs -> Agents -> Human Approval -> Actions -> Reporting.

This is the heart of Velocity Hospitality OS. It fans context out to every
registered agent, collects recommendations, runs them through the approval gate,
and produces an auditable result. Action execution against real systems is
delegated to integration connectors (not invoked here for safety in tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from velocity_hos.agents.base import Agent, Context, Recommendation
from .approval import ApprovalDecision, ApprovalGate


@dataclass
class LoopResult:
    recommendations: list[Recommendation] = field(default_factory=list)
    approved: list[Recommendation] = field(default_factory=list)
    pending: list[Recommendation] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)


class ExecutionLoop:
    def __init__(self, agents: list[Agent], gate: ApprovalGate | None = None):
        self.agents = agents
        self.gate = gate or ApprovalGate()

    def run(self, ctx: Context) -> LoopResult:
        result = LoopResult()
        for agent in self.agents:
            for rec in agent.evaluate(ctx):
                result.recommendations.append(rec)
                decision = self.gate.submit(rec)
                result.audit.append({
                    "tenant": ctx.tenant_id, "agent": rec.agent,
                    "summary": rec.summary, "risk": rec.risk.value,
                    "decision": decision.value,
                })
                if decision is ApprovalDecision.APPROVED:
                    result.approved.append(rec)
                elif decision is ApprovalDecision.PENDING:
                    result.pending.append(rec)
        return result
