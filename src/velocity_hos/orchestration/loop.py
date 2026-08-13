"""The execution loop: Inputs -> Agents -> Human Approval -> Actions -> Reporting.

This is the heart of Velocity Hospitality OS. It runs in two coordinated phases so
the loop actually *closes*:

  1. OPERATE — the operational agents (SOP Coach, HR Onboarding, ...) observe the
     property's inputs and produce recommendations, each routed through the
     human-approval gate.
  2. REPORT — the reporting agent(s) (Executive Intelligence) run last and are
     handed a summary of what just happened this cycle, so the GM's daily briefing
     reflects the actions the other agents took and what is waiting on a human.

Every recommendation and decision is written to an inspectable, JSON-serializable
audit trail. Action execution against real systems is delegated to integration
connectors (not invoked here for safety in tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from velocity_hos.agents.base import Agent, Context, Recommendation, RiskLevel
from .approval import ApprovalDecision, ApprovalGate
from .audit import AuditTrail


@dataclass
class LoopResult:
    recommendations: list[Recommendation] = field(default_factory=list)
    approved: list[Recommendation] = field(default_factory=list)
    pending: list[Recommendation] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)          # flat, back-compat view
    trail: AuditTrail | None = None                          # rich inspectable trail
    cycle_activity: dict = field(default_factory=dict)       # what fed the briefing


class ExecutionLoop:
    def __init__(self, agents: list[Agent], gate: ApprovalGate | None = None):
        self.agents = agents
        self.gate = gate or ApprovalGate()

    def run(self, ctx: Context) -> LoopResult:
        trail = AuditTrail(tenant=ctx.tenant_id)
        result = LoopResult(trail=trail)

        operate = [a for a in self.agents if getattr(a, "phase", "operate") != "report"]
        report = [a for a in self.agents if getattr(a, "phase", "operate") == "report"]

        # --- Phase 1: operate -------------------------------------------------
        for agent in operate:
            self._run_agent(agent, ctx, result, phase="operate")

        # --- Build the cycle summary that closes the loop ---------------------
        activity = self._summarize_cycle(result)
        result.cycle_activity = activity

        # --- Phase 2: report (sees this cycle's activity) ---------------------
        report_ctx = Context(
            tenant_id=ctx.tenant_id,
            inputs={**ctx.inputs, "cycle_activity": activity},
            sops=ctx.sops,
        )
        for agent in report:
            self._run_agent(agent, report_ctx, result, phase="report")

        return result

    # ------------------------------------------------------------------ helpers
    def _run_agent(self, agent: Agent, ctx: Context, result: LoopResult, *, phase: str) -> None:
        for rec in agent.evaluate(ctx):
            result.recommendations.append(rec)
            decision = self.gate.submit(rec)
            event = result.trail.record(rec, decision.value, phase=phase)
            result.audit.append({
                "tenant": event.tenant, "agent": event.agent,
                "summary": rec.summary, "risk": event.risk,
                "decision": event.decision,
            })
            if decision is ApprovalDecision.APPROVED:
                result.approved.append(rec)
            elif decision is ApprovalDecision.PENDING:
                result.pending.append(rec)

    @staticmethod
    def _summarize_cycle(result: LoopResult) -> dict[str, list[str]]:
        """Distil the operate phase into the lines a GM briefing should surface."""
        answered: list[str] = []
        auto_actions: list[str] = []
        awaiting: list[str] = []
        for rec in result.recommendations:
            head = rec.summary.splitlines()[0][:120] if rec.summary else ""
            if rec.risk is RiskLevel.REQUIRES_APPROVAL:
                awaiting.append(head)
            elif rec.risk is RiskLevel.LOW:
                auto_actions.append(head)
            elif rec.proposed_action.get("type") == "answer":
                answered.append(head)
        return {
            "answered_for_staff": answered,
            "actions_auto_executed": auto_actions,
            "awaiting_your_approval": awaiting,
        }
