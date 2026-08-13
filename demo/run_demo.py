"""Velocity Hospitality OS — end-to-end hero demo.

    python demo/run_demo.py

Runs ONE execution loop across four supervised agents on a single property's
operational inputs, and shows the whole spine live:

    Inputs -> Agents -> Human Approval -> Actions -> Reporting

The point of the demo is the human-in-the-loop gate: consequential actions
(contacting a hire, escalating a permit, dispatching a safety-critical repair) are
HELD for a human, who approves or rejects them; only then do they become actions.
Routine work (a dripping tap) is auto-routed and logged; informational output (the
SOP answer, the GM briefing) flows straight through. Offline by default — no
network, no credentials — so it runs anywhere for a recording. It also writes an
inspectable decision trail (decision_trail.md / .json) a judge can open afterwards.

Model-agnostic: the buildathon's provided compute is an open-weights model
(Qwen 3.6 27B on the Impala gateway); the offline default answers here with zero
setup, and self-hosting the same class of open model is an alternative. Swap freely:

    VHOS_LLM_BACKEND=openweights  python demo/run_demo.py   # provided open weights (Impala/Qwen)
    VHOS_LLM_BACKEND=bedrock      python demo/run_demo.py   # optional managed provider (Nova)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context, RiskLevel
from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
from velocity_hos.agents.hr_onboarding import HROnboardingAgent
from velocity_hos.agents.sop_coach import SOPCoachAgent
from velocity_hos.agents.work_order import WorkOrderAgent
from velocity_hos.orchestration.approval import ApprovalDecision, ApprovalGate
from velocity_hos.orchestration.loop import ExecutionLoop


def rule(title: str) -> None:
    print("\n" + "=" * 68 + f"\n  {title}\n" + "=" * 68)


# --- Property SOPs (sanitized) ------------------------------------------------
SOPS = {
    "bev.mojito": "Mojito: 50ml white rum, 8 mint, 25ml lime, 2 tsp sugar, top soda. Jigger every pour.",
    "hr.onboarding_docs": "New hires need passport, work permit, contract, tax form. F&B/kitchen also need a food handler certificate.",
    "hr.permit": "Work permits must stay valid through the contract. HR escalates any permit expiring within 30 days of the start date.",
    "eng.lift_safety": "Lift/elevator faults that can trap or endanger guests are safety-critical: take the car out of service, call the duty engineer, and raise a work order within 1 hour. Guest-impacting or safety defects require Duty Manager approval before dispatch.",
    "eng.hvac": "Guest-room air-conditioning and climate faults affecting an in-house guest are prioritised same day; a VIP-occupied room is escalated to the Duty Manager.",
    "eng.minor": "Routine minor repairs such as a dripping tap or a cosmetic scuff mark are logged and scheduled within the standard maintenance cycle.",
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
    # maintenance / guest-request tickets for the Work Order agent (mixed urgency)
    "tickets": [
        {"id": "WO-501", "category": "safety",
         "description": "elevator 2 stalling intermittently between floors"},
        {"id": "WO-502", "category": "vip",
         "description": "suite 610 AC not cooling, VIP guest in house"},
        {"id": "WO-503", "category": "comfort",
         "description": "lobby restroom tap dripping"},
        {"id": "WO-504", "category": "cosmetic",
         "description": "scuff mark on the floor 3 corridor wall"},
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
    # top_k=1 for the demo: the KB now spans several departments, so answer from the
    # single best-matched SOP for a clean, correctly-cited response on screen.
    agents = [SOPCoachAgent(top_k=1), HROnboardingAgent(), WorkOrderAgent(),
              ExecutiveIntelligenceAgent()]
    gate = ApprovalGate()
    loop = ExecutionLoop(agents, gate)
    ctx = Context(tenant_id="sunset-boutique-svg", inputs=INPUTS, sops=SOPS)

    rule("1 · INPUTS  (one property, one day of operational exhaust)")
    print(f"  Tenant: {ctx.tenant_id}")
    print(f"  Staff question: {INPUTS['question']!r}")
    print(f"  New hires in pipeline: {len(INPUTS['new_hires'])}")
    print(f"  Maintenance tickets: {len(INPUTS['tickets'])}")
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
    # Export the inspectable decision trail — the artifact a judge opens to answer
    # "why did the system do that?": every recommendation, its grounding SOP, and
    # the human/automatic decision, timestamped and ordered.
    if result.trail is not None:
        here = Path(__file__).resolve().parent
        (here / "decision_trail.md").write_text(result.trail.to_markdown(), encoding="utf-8")
        (here / "decision_trail.json").write_text(result.trail.to_json(), encoding="utf-8")
        counts = result.trail.counts()
        print("  Decision trail exported → demo/decision_trail.md · decision_trail.json")
        print(f"  Trail roll-up: {counts}")
    print("  Every recommendation, decision, and action is recorded for review.\n")

    rule("SUMMARY")
    held = len(gate.queue)
    print(f"  {len(result.recommendations)} recommendations · {held} routed to a human · "
          f"{len(approved_now)+len(auto)} actions executed after approval.")
    print("  Human-in-the-loop, grounded in the property's own standards. That's the loop.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
