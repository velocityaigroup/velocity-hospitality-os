"""Smoke tests for the execution loop + human-in-the-loop gate."""
from velocity_hos.agents import ALL_AGENTS
from velocity_hos.agents.base import Context, RiskLevel
from velocity_hos.orchestration import ExecutionLoop


def _ctx() -> Context:
    return Context(
        tenant_id="resort-001",
        inputs={
            "new_hires": [{"id": "h1", "name": "Ana", "documents": ["passport"]}],
            "pos_lines": [
                {"sku": "mojito", "price": 9.0},
                {"sku": "mojito", "price": 12.0},
            ],
            "complaints": [{"id": "c1", "guest_id": "g9", "room": "210"}],
            "tickets": [{"id": "t1", "category": "safety", "owner": "maintenance"}],
            "signals": {"risks": ["staffing tight Fri"]},
        },
        sops={"how to make a mojito": "..."},
    )


def test_loop_runs_all_agents_and_audits():
    loop = ExecutionLoop([A() for A in ALL_AGENTS])
    result = loop.run(_ctx())
    assert result.recommendations, "agents should produce recommendations"
    assert len(result.audit) == len(result.recommendations)


def test_consequential_actions_require_human_approval():
    loop = ExecutionLoop([A() for A in ALL_AGENTS])
    result = loop.run(_ctx())
    # The pricing inconsistency + guest recovery + missing docs must be held.
    assert result.pending, "consequential recs must wait for approval"
    assert all(r.risk is RiskLevel.REQUIRES_APPROVAL for r in result.pending)
