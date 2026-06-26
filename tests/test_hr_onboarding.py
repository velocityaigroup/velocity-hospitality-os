"""HR Onboarding agent: docs, permits, training, and the readiness digest."""
from datetime import date

from velocity_hos.agents.hr_onboarding import HROnboardingAgent
from velocity_hos.agents.base import Context, RiskLevel

TODAY = date(2026, 6, 1)


def _actions(recs, kind):
    return [r for r in recs if r.proposed_action.get("type") == kind]


def test_missing_docs_and_role_training():
    agent = HROnboardingAgent(today=TODAY)
    ctx = Context(tenant_id="resort-001", inputs={"new_hires": [
        {"id": "h1", "name": "Ana", "role": "F&B Server", "documents": ["passport"]},
    ]})
    recs = agent.evaluate(ctx)

    req = _actions(recs, "request_documents")
    assert len(req) == 1
    # F&B role pulls in the food handler cert on top of the base docs.
    assert "food_handler_cert" in req[0].proposed_action["documents"]
    assert req[0].risk is RiskLevel.REQUIRES_APPROVAL

    train = _actions(recs, "assign_training")
    assert "POS/Micros" in train[0].proposed_action["modules"]
    assert train[0].risk is RiskLevel.LOW

    assert _actions(recs, "onboarding_digest"), "HR digest should be produced"


def test_expiring_permit_is_escalated():
    agent = HROnboardingAgent(today=TODAY)
    ctx = Context(tenant_id="t", inputs={"new_hires": [
        {"id": "h2", "name": "Leo", "role": "Housekeeping",
         "documents": list(("passport", "work_permit", "contract", "tax_form")),
         "start_date": "2026-07-01", "permit_expiry": "2026-07-10"},
    ]})
    recs = agent.evaluate(ctx)
    esc = _actions(recs, "escalate_permit")
    assert len(esc) == 1 and esc[0].risk is RiskLevel.REQUIRES_APPROVAL


def test_fully_ready_hire_marked_ready():
    agent = HROnboardingAgent(today=TODAY)
    ctx = Context(tenant_id="t", inputs={"new_hires": [
        {"id": "h3", "name": "Mia", "role": "Front Office",
         "documents": list(("passport", "work_permit", "contract", "tax_form")),
         "start_date": "2026-08-01", "permit_expiry": "2027-01-01"},
    ]})
    recs = agent.evaluate(ctx)
    assert not _actions(recs, "request_documents")
    digest = _actions(recs, "onboarding_digest")[0]
    assert "Mia" in digest.proposed_action["sections"]["ready_to_start"]


def test_no_hires_returns_nothing():
    assert HROnboardingAgent(today=TODAY).evaluate(
        Context(tenant_id="t", inputs={})) == []
