"""Executive Intelligence agent: synthesizes a briefing from alerts."""
from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
from velocity_hos.agents.base import Context, RiskLevel


def test_briefing_reflects_alerts():
    agent = ExecutiveIntelligenceAgent()  # local backend
    ctx = Context(tenant_id="resort-001", inputs={"signals": {
        "risks": ["Storm warning Thursday"],
        "staffing_alerts": ["F&B short 2 for Friday peak"],
        "revenue_alerts": ["Mojito priced 3 ways at pool bar"],
        "compliance_alerts": [],
    }})
    rec = agent.evaluate(ctx)[0]
    assert rec.risk is RiskLevel.INFO
    assert "Friday" in rec.summary or "F&B" in rec.summary
    # raw alerts are preserved for drill-down
    assert rec.proposed_action["sections"]["risks"] == ["Storm warning Thursday"]


def test_all_clear_when_no_alerts():
    rec = ExecutiveIntelligenceAgent().evaluate(
        Context(tenant_id="t", inputs={"signals": {}}))[0]
    assert "all clear" in rec.summary.lower()
