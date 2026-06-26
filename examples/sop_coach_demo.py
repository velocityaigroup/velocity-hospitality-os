"""Run the SOP Coach end-to-end.

    python examples/sop_coach_demo.py

Offline by default. For real Bedrock answers:
    VHOS_LLM_BACKEND=bedrock AWS_REGION=us-east-1 python examples/sop_coach_demo.py
"""
from velocity_hos.agents.sop_coach import SOPCoachAgent
from velocity_hos.agents.base import Context

SOPS = {
    "bev.mojito": "Mojito: 50ml white rum, 8 mint leaves, 25ml lime, 2 tsp sugar, top soda. Free-pour with a jigger.",
    "fo.checkin": "Check-in: greet within 10s, verify ID + reservation, offer welcome drink, escort VIPs.",
    "hk.turndown": "Turndown from 6pm: lower blinds, dim lights, water + chocolate, fold bed corner.",
}

if __name__ == "__main__":
    agent = SOPCoachAgent()
    for q in ["how much rum in a mojito?", "what time does turndown start?"]:
        rec = agent.evaluate(Context("resort-001", {"question": q}, SOPS))[0]
        print(f"\nQ: {q}\nA: {rec.summary}\n   sources: {rec.sources}")


# --- Executive Intelligence demo (run this file to see both) ------------------
def _exec_demo():
    from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
    from velocity_hos.agents.base import Context
    signals = {"signals": {
        "risks": ["Storm warning Thursday"],
        "staffing_alerts": ["F&B short 2 for Friday peak"],
        "revenue_alerts": ["Mojito priced 3 ways at pool bar"],
        "compliance_alerts": ["2 work permits expire this month"],
    }}
    rec = ExecutiveIntelligenceAgent().evaluate(Context("resort-001", signals))[0]
    print("\n=== Executive briefing ===\n" + rec.summary)


if __name__ == "__main__":
    _exec_demo()
