# The Agentic Loop & the Seven Agents

Each agent observes operational `Context`, reasons against the property's own
SOPs, and returns `Recommendation`s tagged with a `RiskLevel`. Only INFO/LOW recs
pass automatically; `REQUIRES_APPROVAL` recs are held for a human.

| # | Agent | Primary signal in | Typical risk |
|---|-------|-------------------|--------------|
| 1 | HR Onboarding | new hires, documents | requires approval |
| 2 | SOP Coach | staff question | info |
| 3 | Workforce Planning | occupancy forecast | requires approval |
| 4 | Work Order | tickets | low |
| 5 | Revenue | POS lines | requires approval |
| 6 | Guest Recovery | complaints | requires approval |
| 7 | Executive Intelligence | aggregated signals | info |

Code: `src/velocity_hos/agents/`. Loop: `src/velocity_hos/orchestration/loop.py`.
