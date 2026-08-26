"""The live console's API surface — including the human decision that closes the loop.

These exercise the same functions the HTTP handlers call, so a demonstration path
that works here works in the browser.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "ui"))

import server  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    server.reset_all()
    yield
    server.reset_all()


# ------------------------------------------------------------------- basics
def test_status_reports_the_selected_property():
    s = server.status("firefly-bequia")
    assert s["property"]["key"] == "firefly-bequia"
    assert s["property"]["gaps"] == 11
    assert s["backend"]


def test_unknown_property_falls_back_rather_than_erroring():
    assert server.status("nope")["property"]["key"] == "azure-bay"


def test_kb_and_gaps_endpoints_are_property_scoped():
    assert all(r["id"].startswith("FF-") for r in server.api_kb("firefly-bequia"))
    assert not any(r["id"].startswith("FF-") for r in server.api_kb("azure-bay"))
    assert server.api_gaps("azure-bay") == []
    assert len(server.api_gaps("firefly-bequia")) == 11


def test_empty_question_is_handled_not_crashed():
    r = server.ask("firefly-bequia", "")
    assert r["ok"] is False and r["error"]


def test_ask_returns_a_citation_and_its_provenance():
    r = server.ask("firefly-bequia", "how much does golf cost and are clubs included?")
    assert r["ok"] and not r["refused"]
    assert r["sop"]["id"] == "FF-501"
    assert r["sop"]["confidence"] == "unconfirmed"
    assert r["sop"]["source"]


def test_ask_refuses_a_declared_gap_by_name():
    r = server.ask("firefly-bequia", "what time can I check in?")
    assert r["refused"] and r["gap_id"] == "G3"


# --------------------------------------------------------------------- loop
def test_loop_runs_four_agents_including_work_order():
    snap = server.run_loop("firefly-bequia")
    agents = {r["agent"] for r in snap["recommendations"]}
    assert agents == {"sop_coach", "hr_onboarding", "work_order", "executive_intelligence"}
    assert snap["ran"] and snap["briefing"]


def test_work_order_routing_is_grounded_in_the_property_own_records():
    snap = server.run_loop("firefly-bequia")
    wo = [r for r in snap["recommendations"] if r["agent"] == "work_order"]
    assert wo, "the work order agent produced nothing"
    assert any(r["sources"] for r in wo)
    for r in wo:
        assert all(s.startswith("FF-") for s in r["sources"])


def test_consequential_items_are_held_and_routine_work_is_not():
    snap = server.run_loop("azure-bay")
    assert snap["pending_count"] > 0
    assert any(r["risk"] == "low" for r in snap["recommendations"])


# ------------------------------------------------------ the loop closing
def test_approving_assigns_an_owner_and_an_sla_and_updates_the_briefing():
    snap = server.run_loop("firefly-bequia")
    held = snap["approvals"][0]["summary"]
    assert held in snap["briefing"]

    after = server.decide("firefly-bequia", 0, "approved")
    assert after["ok"]
    assert after["pending_count"] == snap["pending_count"] - 1

    task = after["tasks"][0]
    assert task["owner"] and task["sla_hours"] > 0 and task["due"]
    assert task["summary"] == held

    awaiting = after["briefing"].split("Awaiting Your Approval:")[-1].split("\n\n")[0]
    taken = after["briefing"].split("Actions Taken:")[-1].split("\n\n")[0]
    assert held not in awaiting, "approved item still shown as awaiting"
    assert held in taken, "approved item never appeared in actions taken"


def test_rejecting_records_the_decision_and_assigns_nothing():
    server.run_loop("firefly-bequia")
    after = server.decide("firefly-bequia", 0, "rejected")
    assert after["ok"] and after["tasks"] == []
    assert after["approvals"][0]["decision"] == "rejected"
    assert any(e["decision"] == "rejected" for e in after["trail"])


def test_every_decision_is_written_to_the_audit_trail():
    before = server.run_loop("firefly-bequia")
    after = server.decide("firefly-bequia", 1, "approved")
    assert len(after["trail"]) == len(before["trail"]) + 2   # decision + execution
    assert {"seq", "ts", "agent", "phase", "risk", "decision", "action", "sources"} <= set(
        after["trail"][-1])


def test_trail_rows_share_one_schema_whatever_produced_them():
    server.run_loop("azure-bay")
    trail = server.decide("azure-bay", 0, "approved")["trail"]
    keys = {frozenset(e) for e in trail}
    assert len(keys) == 1, "trail rows have inconsistent shapes"
    assert [e["seq"] for e in trail] == list(range(1, len(trail) + 1))


# ------------------------------------------------------------------- errors
def test_decide_before_running_the_loop_is_refused_politely():
    r = server.decide("azure-bay", 0, "approved")
    assert r["ok"] is False and "cycle" in r["error"].lower()


def test_decide_rejects_a_bad_index_and_a_bad_decision():
    server.run_loop("azure-bay")
    assert server.decide("azure-bay", 99, "approved")["ok"] is False
    assert server.decide("azure-bay", 0, "maybe")["ok"] is False


def test_an_item_cannot_be_decided_twice():
    server.run_loop("azure-bay")
    assert server.decide("azure-bay", 0, "approved")["ok"]
    assert server.decide("azure-bay", 0, "rejected")["ok"] is False


# -------------------------------------------------------------------- reset
def test_reset_returns_the_property_to_a_clean_pre_demo_state():
    server.run_loop("azure-bay")
    server.decide("azure-bay", 0, "approved")
    snap = server.reset("azure-bay")
    assert snap["ran"] is False and snap["tasks"] == [] and snap["trail"] == []
    assert snap["approvals"] == [] and snap["briefing"] == ""
    # the property's own inputs are still there, ready for the next run
    assert snap["kpis"] and snap["hires"]


def test_state_is_isolated_per_property():
    server.run_loop("azure-bay")
    assert server._snapshot("firefly-bequia")["ran"] is False
    server.run_loop("firefly-bequia")
    assert server._snapshot("azure-bay")["ran"] is True
