# Contributing

Thanks for your interest in Velocity Hospitality OS.

## Principles
- **Human-in-the-loop is non-negotiable.** Any action that moves money, staffing,
  or the guest relationship must route through the approval gate.
- **Auditability by default.** Every agent decision and action is logged.
- **Integrate, don't replace.** We sit above the existing hotel stack (PMS, POS,
  payroll); connectors live in `src/velocity_hos/integrations/`.

## Dev setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
ruff check .
```

## Adding an agent
1. Subclass `Agent` in `src/velocity_hos/agents/base.py`.
2. Implement `evaluate(context) -> list[Recommendation]`.
3. Register it with the orchestrator and add a test under `tests/`.

## Commits & PRs
- Conventional commits (`feat:`, `fix:`, `docs:`…).
- Keep PRs focused; include tests for new behavior.
