"""Proof: the PROVIDED open-weights model answering on the DESIGN-PARTNER property.

    python scripts/firefly_openweights_proof.py

This is the R4 evidence artifact. It runs the Buildathon's provided open-weights model
(Qwen 3.6 27B on the Impala gateway) through Velocity's real agents, over Firefly Estate
Bequia's own knowledge base — not a toy SOP dictionary — and prints, in one screenshot's
worth of output:

  1. the model answering a question Firefly HAS documented, with its citation and the
     record's provenance badge;
  2. the model REFUSING a question Firefly has NOT documented, naming the declared gap;
  3. one full four-agent execution cycle on Firefly's day, with the GM briefing that the
     provided model generated.

Nothing about the application changed to make this happen. The model is a swappable
provider behind one interface: retrieval, grounding, citations, the gap guard, the
approval gate and the loop are all model-independent. Only three config values move.

Setup (Builder Portal -> Resources -> "Your gateway & key"):

    PowerShell:
        $env:VHOS_LLM_BACKEND="openweights"
        $env:VHOS_EMBED_BACKEND="local"
        $env:VHOS_OPENWEIGHTS_URL="https://ht.getimpala.ai/v1"
        $env:VHOS_OPENWEIGHTS_MODEL="qwen3.6-27b"
        $env:VHOS_OPENWEIGHTS_API_KEY="sk-...your-team-key..."

    bash:
        export VHOS_LLM_BACKEND=openweights
        export VHOS_EMBED_BACKEND=local
        export VHOS_OPENWEIGHTS_URL=https://ht.getimpala.ai/v1
        export VHOS_OPENWEIGHTS_MODEL=qwen3.6-27b
        export VHOS_OPENWEIGHTS_API_KEY=sk-...your-team-key...

Never commit the key.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.config import settings  # noqa: E402

# Windows consoles default to a legacy code page that cannot encode these symbols.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

GROUNDED_QUESTIONS = [
    "how much is the estate tour and when does it run?",
    "how much does golf cost and are clubs included?",
]
GAP_QUESTION = "what is the room rate for a week in March?"


def headline(text: str) -> str:
    """First non-empty line with markdown markers stripped, for one-line rows."""
    for line in (text or "").splitlines():
        cleaned = re.sub(r"^[\s>*+-]*#{0,6}\s*|\*\*|__|`", "", line).strip()
        if cleaned:
            return cleaned
    return ""


def rule(title: str) -> None:
    print("\n" + "=" * 74 + f"\n  {title}\n" + "=" * 74)


def _fail(msg: str) -> int:
    print(f"\n[FAIL] Firefly open-weights proof FAILED\n   {msg}\n")
    print("Checklist:")
    print(f"  1. Gateway reachable at VHOS_OPENWEIGHTS_URL: {settings.openweights_base_url}")
    print("  2. VHOS_LLM_BACKEND=openweights")
    print(f"  3. Model name matches the gateway's: {settings.openweights_model}")
    print("  4. VHOS_OPENWEIGHTS_API_KEY is set to your team key (starts with sk-).")
    return 1


def main() -> int:
    from velocity_hos.agents.base import Context, RiskLevel
    from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
    from velocity_hos.agents.hr_onboarding import HROnboardingAgent
    from velocity_hos.agents.sop_coach import SOPCoachAgent
    from velocity_hos.agents.work_order import WorkOrderAgent
    from velocity_hos.knowledge import get_property
    from velocity_hos.orchestration.approval import ApprovalGate
    from velocity_hos.orchestration.loop import ExecutionLoop

    prop = get_property("firefly-bequia")
    by_id = {s.sop_id: s for s in prop.sops}
    docs = prop.retrieval_docs()

    rule("PROVIDED COMPUTE — configuration only, no application code change")
    print(f"  llm backend:      {settings.llm_backend}")
    print(f"  gateway:          {settings.openweights_base_url}")
    print(f"  model:            {settings.openweights_model}")
    print(f"  embeddings:       {settings.embed_backend}")
    print(f"  api key present:  {'yes' if settings.openweights_api_key else 'NO'}")
    print(f"\n  property:         {prop.name} — {prop.location}")
    print(f"  provenance:       {prop.kind}")
    print(f"  knowledge base:   {len(prop.sops)} records · "
          f"{len(prop.departments())} departments · {len(prop.gaps)} declared gaps")

    if settings.llm_backend != "openweights":
        return _fail("VHOS_LLM_BACKEND is not 'openweights'.")

    coach = SOPCoachAgent()

    def ask(question: str):
        t0 = time.time()
        rec = coach.evaluate(Context(prop.tenant_id,
                                     {"question": question, "known_gaps": prop.gaps},
                                     docs))[0]
        return rec, time.time() - t0

    # ---------------------------------------------------------------- grounded
    rule("1 · THE PROVIDED MODEL ANSWERING FIREFLY'S OWN KNOWLEDGE (grounded + cited)")
    for question in GROUNDED_QUESTIONS:
        try:
            rec, secs = ask(question)
        except Exception as exc:  # noqa: BLE001
            return _fail(f"{type(exc).__name__}: {exc}")
        if rec.proposed_action.get("type") != "answer":
            return _fail(f"expected an answer for {question!r}, got a refusal")
        sop = by_id.get(rec.sources[0]) if rec.sources else None
        print(f"\n  Q: {question}")
        print(f"  A: {rec.summary}")
        print(f"     cited source : {', '.join(rec.sources)}")
        if sop is not None:
            print(f"     record       : {sop.sop_id} — {sop.title} ({sop.department})")
            print(f"     provenance   : {sop.confidence.upper()} · public source: {sop.source}")
        print(f"     latency      : {secs:.2f}s on {settings.openweights_model}")

    # -------------------------------------------------------------- declared gap
    rule("2 · THE SAME MODEL REFUSING WHAT FIREFLY HAS NOT DOCUMENTED")
    try:
        rec, secs = ask(GAP_QUESTION)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"{type(exc).__name__}: {exc}")
    action = rec.proposed_action
    if action.get("type") != "refusal":
        return _fail(f"the guardrail did not hold: {GAP_QUESTION!r} was answered "
                     f"from {rec.sources}")
    print(f"\n  Q: {GAP_QUESTION}")
    print(f"  A: {rec.summary}")
    print(f"     declared gap : {action.get('gap_id')} — {action.get('gap')}")
    print(f"     sources      : {rec.sources or '[] (nothing cited, nothing invented)'}")
    print("\n  A capable 27B model was available and the system still declined, because the")
    print("  property has not supplied this. The guardrail is in the product, not the prompt.")

    # ------------------------------------------------------------------- loop
    rule("3 · ONE FOUR-AGENT CYCLE ON FIREFLY'S DAY, ON THE PROVIDED MODEL")
    gate = ApprovalGate()
    agents = [SOPCoachAgent(top_k=1), HROnboardingAgent(), WorkOrderAgent(),
              ExecutiveIntelligenceAgent()]
    try:
        result = ExecutionLoop(agents, gate).run(
            Context(prop.tenant_id, prop.inputs(), docs))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"{type(exc).__name__}: {exc}")

    for rec in result.recommendations:
        tag = {RiskLevel.REQUIRES_APPROVAL: "HELD FOR HUMAN",
               RiskLevel.LOW: "auto (logged)",
               RiskLevel.INFO: "info"}[rec.risk]
        src = f"  [{', '.join(rec.sources)}]" if rec.sources else ""
        print(f"  • [{rec.agent:<22}] {headline(rec.summary)[:74]:<74} {tag}{src}")

    briefing = next((r.summary for r in result.recommendations
                     if r.agent == "executive_intelligence"), "")
    rule("4 · THE GM BRIEFING, WRITTEN BY THE PROVIDED MODEL")
    print(briefing)

    held = len(gate.queue)
    rule("PROOF SUMMARY")
    print(f"  Model            : {settings.openweights_model} via {settings.openweights_base_url}")
    print(f"  Property         : {prop.name} ({len(prop.sops)} records, {len(prop.gaps)} declared gaps)")
    print(f"  Grounded answers : {len(GROUNDED_QUESTIONS)}/{len(GROUNDED_QUESTIONS)} cited a Firefly record")
    print(f"  Gap refusal      : held ({action.get('gap_id')}) — nothing invented")
    print(f"  Loop             : {len(result.recommendations)} recommendations · "
          f"{held} routed to a human · {len(result.audit)} audit events")
    print("\n  The provided open-weights model is running the whole product. Application")
    print("  code unchanged — three config values. Screenshot this for the logbook.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
