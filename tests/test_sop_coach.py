"""RAG SOP Coach: retrieval picks the right SOP and the answer cites it."""
from velocity_hos.agents.sop_coach import SOPCoachAgent
from velocity_hos.agents.base import Context, RiskLevel

SOPS = {
    "bev.mojito": (
        "Mojito spec: 50ml white rum, 8 mint leaves, 25ml lime juice, 2 tsp sugar, "
        "top with soda. Always free-pour with a jigger; never eyeball the rum."
    ),
    "fo.checkin": (
        "Front office check-in: greet within 10 seconds, verify ID and reservation, "
        "offer welcome drink, confirm departure date, escort VIPs to the room."
    ),
    "hk.turndown": (
        "Housekeeping turndown begins at 6pm: lower blinds, dim lights, place water "
        "and chocolate, fold the bed corner."
    ),
}


def test_retrieves_relevant_sop_and_cites_source():
    agent = SOPCoachAgent()  # local backend, no network
    ctx = Context(tenant_id="resort-001",
                  inputs={"question": "how much rum goes in a mojito?"},
                  sops=SOPS)
    recs = agent.evaluate(ctx)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.risk is RiskLevel.INFO
    assert "bev.mojito" in rec.sources           # retrieved the right doc
    assert rec.sources[0] == "bev.mojito"        # ranked it first
    assert "rum" in rec.summary.lower()          # answer is grounded


def test_no_question_returns_nothing():
    assert SOPCoachAgent().evaluate(
        Context(tenant_id="t", inputs={}, sops=SOPS)) == []


def test_empty_sops_is_handled_gracefully():
    recs = SOPCoachAgent().evaluate(
        Context(tenant_id="t", inputs={"question": "anything?"}, sops={}))
    assert len(recs) == 1
    assert recs[0].sources == []
