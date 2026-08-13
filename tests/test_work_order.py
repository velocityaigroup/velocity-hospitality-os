"""Tests for the Work Order agent: priority, SLA, grounding, and the human gate."""
from __future__ import annotations

from velocity_hos.agents.base import Context, RiskLevel
from velocity_hos.agents.work_order import WorkOrderAgent

# A small maintenance/safety SOP slice for grounding.
SOPS = {
    "eng.lift_safety": (
        "Lift and elevator faults that can trap or endanger guests are "
        "safety-critical: take the car out of service, call the duty engineer, and "
        "raise a work order within one hour. Guest-impacting or safety defects "
        "require Duty Manager approval before dispatch."
    ),
    "eng.hvac": (
        "Guest-room air-conditioning and climate faults affecting an in-house guest "
        "are prioritised same day; a VIP-occupied room is escalated to the Duty "
        "Manager."
    ),
    "eng.minor": (
        "Routine minor repairs such as a dripping tap or a cosmetic scuff mark are "
        "logged and scheduled within the standard maintenance cycle."
    ),
}

TICKETS = [
    {"id": "WO-1", "category": "cosmetic", "description": "scuff mark on corridor wall"},
    {"id": "WO-2", "category": "safety", "description": "elevator stalling between floors"},
    {"id": "WO-3", "category": "vip", "description": "suite AC not cooling, VIP in house"},
    {"id": "WO-4", "category": "comfort", "description": "lobby tap dripping"},
]


def _run(tickets, sops=SOPS):
    agent = WorkOrderAgent()
    return agent.evaluate(Context("t", {"tickets": tickets}, sops))


def test_returns_one_rec_per_ticket():
    assert len(_run(TICKETS)) == 4


def test_most_urgent_first():
    recs = _run(TICKETS)
    order = [r.proposed_action["ticket_id"] for r in recs]
    assert order[0] == "WO-2"  # safety first
    assert order[-1] == "WO-1"  # cosmetic last


def test_safety_is_held_for_a_human():
    rec = _run([TICKETS[1]])[0]
    assert rec.risk is RiskLevel.REQUIRES_APPROVAL
    assert rec.proposed_action["sla_hours"] == 1
    assert rec.proposed_action["requires_approval"] is True


def test_vip_touches_guest_so_held():
    rec = _run([TICKETS[2]])[0]
    assert rec.risk is RiskLevel.REQUIRES_APPROVAL


def test_routine_auto_routes():
    for t in (TICKETS[0], TICKETS[3]):  # cosmetic, comfort
        rec = _run([t])[0]
        assert rec.risk is RiskLevel.LOW
        assert rec.proposed_action["requires_approval"] is False


def test_high_cost_routine_is_held():
    pricey = {"id": "WO-9", "category": "comfort",
              "description": "replace lobby tap unit", "cost_estimate": 900}
    rec = _run([pricey])[0]
    assert rec.risk is RiskLevel.REQUIRES_APPROVAL
    assert "threshold" in rec.rationale.lower()


def test_grounds_and_cites_a_governing_sop():
    rec = _run([TICKETS[1]])[0]  # elevator -> lift_safety
    assert rec.sources, "expected a governing SOP to be cited"
    assert "eng.lift_safety" in rec.sources


def test_ungrounded_ticket_is_flagged_not_invented():
    odd = {"id": "WO-7", "category": "comfort",
           "description": "guest wants a birthday cake for the penguin exhibit"}
    rec = _run([odd], sops=SOPS)[0]
    assert rec.sources == []
    assert "no governing sop" in rec.rationale.lower()


def test_sla_and_owner_in_action():
    rec = _run([TICKETS[2]])[0]
    assert rec.proposed_action["owner"]
    assert rec.proposed_action["sla_hours"] == 4
    assert rec.proposed_action["type"] == "work_order"


def test_work_order_coordinates_through_the_loop_into_the_briefing():
    """The loop must hold the safety ticket for a human and surface the routine one
    as an action taken — and both must reach the GM briefing (loop closes)."""
    from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
    from velocity_hos.orchestration.loop import ExecutionLoop

    loop = ExecutionLoop([WorkOrderAgent(), ExecutiveIntelligenceAgent()])
    result = loop.run(Context("t", {"tickets": TICKETS}, SOPS))

    awaiting = result.cycle_activity["awaiting_your_approval"]
    auto = result.cycle_activity["actions_auto_executed"]
    assert any("WO-2" in s for s in awaiting)   # safety held for a human
    assert any("WO-1" in s for s in auto)       # cosmetic auto-routed

    # the reporting agent saw this cycle's activity — the loop closed
    briefing = next(r.summary for r in result.recommendations
                    if r.agent == "executive_intelligence")
    assert "WO-2" in briefing
