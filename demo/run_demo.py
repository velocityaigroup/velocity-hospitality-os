"""Velocity Hospitality OS — end-to-end hero demo.

    python demo/run_demo.py                            # authored demonstration resort
    python demo/run_demo.py --property firefly-bequia  # the design-partner property

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
from velocity_hos.knowledge import get_property, property_index
from velocity_hos.orchestration.approval import ApprovalDecision, ApprovalGate
from velocity_hos.orchestration.loop import ExecutionLoop


def rule(title: str) -> None:
    print("\n" + "=" * 68 + f"\n  {title}\n" + "=" * 68)


# The property's own knowledge base and its day of operational inputs both come from
# the property registry (``velocity_hos.knowledge.properties``), so the CLI demo, the
# console and the tests all run on exactly the same content — and the dates in the
# onboarding pipeline are generated relative to today, never hard-coded.


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    key = None
    if "--property" in argv:
        key = argv[argv.index("--property") + 1]
    if key in ("--help", "-h") or "--help" in argv:
        print("usage: python demo/run_demo.py [--property KEY]")
        print("  properties: " + ", ".join(p["key"] for p in property_index()))
        return 0

    prop = get_property(key)
    inputs = prop.inputs()

    # top_k=1 for the demo: the KB spans many departments, so answer from the single
    # best-matched record for a clean, correctly-cited response on screen.
    agents = [SOPCoachAgent(top_k=1), HROnboardingAgent(), WorkOrderAgent(),
              ExecutiveIntelligenceAgent()]
    gate = ApprovalGate()
    loop = ExecutionLoop(agents, gate)
    ctx = Context(tenant_id=prop.tenant_id, inputs=inputs, sops=prop.retrieval_docs())

    rule("1 · INPUTS  (one property, one day of operational exhaust)")
    print(f"  Property: {prop.name} — {prop.location}")
    print(f"  Provenance: {prop.kind}")
    print(f"  Knowledge base: {len(prop.sops)} records · {len(prop.departments())} departments"
          + (f" · {len(prop.gaps)} declared gaps" if prop.gaps else ""))
    print(f"  Staff question: {inputs['question']!r}")
    print(f"  New hires in pipeline: {len(inputs['new_hires'])}")
    print(f"  Maintenance tickets: {len(inputs['tickets'])}")
    print(f"  Operational alerts: {sum(len(v) for v in inputs['signals'].values())}")

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
        stem = "decision_trail" if prop.key == "azure-bay" else f"decision_trail_{prop.key}"
        (here / f"{stem}.md").write_text(result.trail.to_markdown(), encoding="utf-8")
        (here / f"{stem}.json").write_text(result.trail.to_json(), encoding="utf-8")
        counts = result.trail.counts()
        print(f"  Decision trail exported → demo/{stem}.md · {stem}.json")
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
