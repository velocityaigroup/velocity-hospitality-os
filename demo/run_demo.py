"""Velocity Hospitality OS — end-to-end hero demo.

    python demo/run_demo.py

Runs ONE execution loop across three supervised agents on a single property's
operational inputs, and shows the whole spine live:

    Inputs -> Agents -> Human Approval -> Actions -> Reporting

The point of the demo is the human-in-the-loop gate: consequential actions
(contacting a hire, escalating a permit) are HELD for a human, who approves or
rejects them; only then do they become actions. Informational output (the SOP
answer, the GM briefing) flows straight through. Offline by default — no network,
no credentials — so it runs anywhere for a recording.

Model-agnostic: the official deployment runs an open-weights model we self-host
(vLLM on H200); the offline default answers here with zero setup. Swap freely:

    VHOS_LLM_BACKEND=openweights  python demo/run_demo.py   # self-hosted open model (official)
    VHOS_LLM_BACKEND=bedrock      python demo/run_demo.py   # optional managed provider
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context, RiskLevel
from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
from velocity_hos.agents.hr_onboarding import HROnboardingAgent
from velocity_hos.agents.sop_coach import SOPCoachAgent
from velocity_hos.orchestration.approval import ApprovalDecision, ApprovalGate
from velocity_hos.orchestration.loop import ExecutionLoop


def rule(title: str) -> None:
    print("\n" + "=" * 68 + f"\n  {title}\n" + "=" * 68)


# --- Property SOPs (sanitized) ------------------------------------------------
SOPS = {
    "bev.mojito": "Mojito: 50ml white rum, 8 mint, 25ml lime, 2 tsp sugar, top soda. Jigger every pour.",
    "hr.onboarding_docs": "New hires need passport, work permit, contract, tax form. F&B/kitchen also need a food handler certificate.",
    "hr.permit": "Work permits must stay valid through the contract. HR escalates any permit expiring within 30 days of the start date.",
}

# --- A day's operational inputs for one property ------------------------------
INPUTS = {
    # a floor staff question for the SOP Coach
    "question": "how much rum goes in a mojito?",
    # onboarding pipeline for the HR agent (one hire has a problem)
    "new_hires": [
        {"id": "H-101", "name": "Ana P.", "role": "f&b",
         "documents": ["passport", "contract", "tax_form"],   # missing work_permit + food handler cert
         "permit_expiry": "2026-08-20", "start_date": "2026-08-10"},   # permit expires near start
        {"id": "H-102", "name": "Marko D.", "role": "front office",
         "documents": ["passport", "work_permit", "contract", "tax_form"],
         "start_date": "2026-08-12"},                          # clean — ready to start
    ],
    # alerts feeding the Executive Intelligence briefing
    "signals": {
        "risks": ["Storm warning Thursday PM — pool & watersports"],
        "staffing_alerts": ["F&B short 2 covers for Friday peak"],
        "revenue_alerts": ["Cabanas unbooked for the weekend (premium inventory idle)"],
        "compliance_alerts": ["1 work permit expiring within 30 days"],
    },
}


def main() -> int:
    agents = [SOPCoachAgent(), HROnboardingAgent(), ExecutiveIntelligenceAgent()]
    gate = ApprovalGate()
    loop = ExecutionLoop(agents, gate)
    ctx = Context(tenant_id="sunset-boutique-svg", inputs=INPUTS, sops=SOPS)

    rule("1 · INPUTS  (one property, one day of operational exhaust)")
    print(f"  Tenant: {ctx.tenant_id}")
    print(f"  Staff question: {INPUTS['question']!r}")
    print(f"  New hires in pipeline: {len(INPUTS['new_hires'])}")
    print(f"  Operational alerts: {sum(len(v) for v in INPUTS['signals'].values())}")

    rule("2 · AGENTS  (each reasons against the property's own standards)")
    result = loop.run(ctx)
    for rec in result.recommendations:
        gate_tag = {
            RiskLevel.REQUIRES_APPROVAL: "  ⏸ HELD FOR HUMAN",
            RiskLevel.LOW: "  ✓ auto (logged)",
            RiskLevel.INFO: "  ℹ info",
        }[rec.risk]
        src = f"  [sources: {', '.join(rec.sources)}]" if rec.sources else ""
        print(f"  • [{rec.agent}] {rec.summary.splitlines()[0][:80]}{gate_tag}{src}")

    rule("3 · HUMAN APPROVAL  (nothing consequential acts without a person)")
    if not gate.queue:
        print("  (no consequential actions this cycle)")
    for i, pending in enumerate(gate.queue):
        print(f"  [{i}] {pending.recommendation.summary}")
    # A human (the HR manager) reviews the queue:
    #   - approve the permit escalation (real risk, act now)
    #   - approve the document request
    decisions = {}
    for i, pending in enumerate(gate.queue):
        action = pending.recommendation.proposed_action.get("type")
        decision = ApprovalDecision.APPROVED  # HR manager approves both in this demo
        gate.resolve(i, decision)
        decisions[i] = decision
        print(f"      -> human decision on [{i}] ({action}): {decision.value.upper()}")

    rule("4 · ACTIONS  (only approved items become actions)")
    approved_now = [p.recommendation for p in gate.queue
                    if p.decision is ApprovalDecision.APPROVED]
    auto = [r for r in result.approved if r.risk is not RiskLevel.INFO]
    for r in approved_now:
        print(f"  ✅ EXECUTE  [{r.agent}] {r.proposed_action.get('type')}: {r.summary}")
    for r in auto:
        print(f"  ✅ EXECUTE  [{r.agent}] {r.proposed_action.get('type')} (low-risk, pre-approved)")
    if not approved_now and not auto:
        print("  (nothing to execute)")

    rule("5 · REPORTING  (audit trail + the GM's daily briefing)")
    briefing = next((r.summary for r in result.recommendations
                     if r.agent == "executive_intelligence"), "")
    print(briefing + "\n")
    print(f"  Audit events logged this cycle: {len(result.audit)}")
    print("  Every recommendation, decision, and action is recorded for review.\n")

    rule("SUMMARY")
    held = len(gate.queue)
    print(f"  {len(result.recommendations)} recommendations · {held} routed to a human · "
          f"{len(approved_now)+len(auto)} actions executed after approval.")
    print("  Human-in-the-loop, grounded in the property's own standards. That's the loop.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
