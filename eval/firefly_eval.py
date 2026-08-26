"""Evaluation harness for the Firefly Estate Bequia design-partner corpus.

Run:  python eval/firefly_eval.py

This is a SECOND, independent evaluation. It does not touch the authored demo
corpus or its published 95% / 100% / 100% result — each property is scored on its
own knowledge base, which is exactly how the product is deployed.

Three things are measured:

  1. retrieval@1   — for a question the property HAS documented, does the assistant
                     cite the right record first?
  2. gap refusal   — for a question the property has NOT documented (rates, service
                     times, transfer prices), does the assistant refuse and name the
                     declared gap, rather than answering from a neighbouring record?
  3. out-of-scope  — for a question that is nothing to do with the property at all,
                     does it refuse?

Nothing in the seed corpus is operator-confirmed, so this measures the SEED. When
Firefly supplies real documents the same harness re-runs unchanged and the number is
comparable — that is the point of keeping it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context  # noqa: E402
from velocity_hos.agents.sop_coach import SOPCoachAgent  # noqa: E402
from velocity_hos.knowledge import get_property  # noqa: E402

# --- questions the property HAS documented -> the record that should be cited ----
GROUNDED: list[tuple[str, str]] = [
    ("how much is the estate tour?", "FF-503"),
    ("what day does the plantation tour not run?", "FF-503"),
    ("what is the private tour price?", "FF-504"),
    ("how much does golf cost and are clubs included?", "FF-501"),
    ("is croquet free?", "FF-502"),
    ("who runs the diving?", "FF-505"),
    ("is breakfast included?", "FF-205"),
    ("is laundry included in the room?", "FF-205"),
    ("do you cater for special diets?", "FF-402"),
    ("can non residents eat at the restaurant?", "FF-401"),
    ("how much deposit do I pay when booking?", "FF-301"),
    ("can I cancel and get a refund?", "FF-302"),
    ("what happens if I arrive late?", "FF-302"),
    ("which credit cards do you accept?", "FF-303"),
    ("is tipping expected?", "FF-605"),
    ("is there a ferry from Barbados?", "FF-604"),
    ("where is the hotel and how far is the dock?", "FF-101"),
    ("how old is the sugar mill?", "FF-102"),
    ("which rooms are on the upper floor?", "FF-201"),
    ("is there wifi in the rooms?", "FF-603"),
    ("what sockets do you use, do I need an adaptor?", "FF-603"),
    ("are there mosquitoes or malaria?", "FF-602"),
    ("are there dogs on the property?", "FF-602"),
    ("tell me about the beach and sand flies", "FF-601"),
    ("does the villa have a private pool?", "FF-204"),
    ("does the estate cottage suit a family with children?", "FF-203"),
    ("what is the number to book a table?", "FF-701"),
    ("how should our messages to guests sound?", "FF-901"),
]

# --- questions inside a DECLARED GAP -> must refuse and name the gap -------------
GAPS: list[tuple[str, str]] = [
    ("what is the room rate for a week in March?", "G1"),
    ("how much is the villa per night?", "G1"),
    ("what time is dinner served?", "G2"),
    ("what time can I check in?", "G3"),
    ("how much is a taxi from the airport?", "G4"),
    ("what is your tripadvisor rating?", "G9"),
]

# --- nothing to do with the property -> must refuse -----------------------------
OUT_OF_SCOPE: list[str] = [
    "what is the capital of France?",
    "tell me a joke about penguins",
    "what's the weather forecast tomorrow?",
    "how do I reset my email password?",
]


def run() -> dict:
    prop = get_property("firefly-bequia")
    docs = prop.retrieval_docs()
    agent = SOPCoachAgent()

    def answer(question: str):
        ctx = Context(prop.tenant_id,
                      {"question": question, "known_gaps": prop.gaps}, docs)
        return agent.evaluate(ctx)[0]

    rows: list[dict] = []
    grounded_ok = 0
    for q, expected in GROUNDED:
        rec = answer(q)
        got = rec.sources[0] if rec.sources else "REFUSED"
        ok = got == expected
        grounded_ok += ok
        rows.append({"kind": "grounded", "question": q, "expected": expected,
                     "got": got, "ok": ok})

    gap_ok = 0
    for q, gid in GAPS:
        rec = answer(q)
        got = rec.proposed_action.get("gap_id")
        ok = rec.proposed_action.get("type") == "refusal" and got == gid
        gap_ok += ok
        rows.append({"kind": "gap", "question": q, "expected": gid,
                     "got": got or "ANSWERED", "ok": ok})

    oos_ok = 0
    for q in OUT_OF_SCOPE:
        rec = answer(q)
        ok = rec.proposed_action.get("type") == "refusal"
        oos_ok += ok
        rows.append({"kind": "out_of_scope", "question": q, "expected": "refuse",
                     "got": "REFUSED" if ok else (rec.sources[:1] or ["ANSWERED"])[0],
                     "ok": ok})

    total = len(GROUNDED) + len(GAPS) + len(OUT_OF_SCOPE)
    correct = grounded_ok + gap_ok + oos_ok
    confirmed = sum(1 for s in prop.sops if s.confidence == "operator_confirmed")
    return {
        "property": prop.name,
        "records": len(prop.sops),
        "departments": len(prop.departments()),
        "declared_gaps": len(prop.gaps),
        "operator_confirmed_records": confirmed,
        "retrieval_at_1": grounded_ok / len(GROUNDED),
        "gap_refusal": gap_ok / len(GAPS),
        "out_of_scope_refusal": oos_ok / len(OUT_OF_SCOPE),
        "overall": correct / total,
        "cases": total,
        "rows": rows,
    }


def to_markdown(r: dict) -> str:
    lines = [
        f"# Firefly Estate Bequia — SOP Coach evaluation ({r['cases']} cases)",
        "",
        f"- Corpus: **{r['records']} records** across **{r['departments']} departments**, "
        f"**{r['declared_gaps']} declared knowledge gaps**",
        f"- Operator-confirmed records: **{r['operator_confirmed_records']} of {r['records']}** "
        "— this is a public-source seed, not confirmed content",
        f"- Retrieval@1 on documented questions: **{r['retrieval_at_1']:.0%}**",
        f"- Declared-gap refusal (refused AND named the right gap): **{r['gap_refusal']:.0%}**",
        f"- Out-of-scope refusal: **{r['out_of_scope_refusal']:.0%}**",
        f"- Overall correct: **{r['overall']:.0%}**",
        "",
        "| | Question | Expected | Got |",
        "|---|---|---|---|",
    ]
    for row in r["rows"]:
        mark = "✅" if row["ok"] else "❌"
        lines.append(f"| {mark} | {row['question']} | {row['expected']} | {row['got']} |")
    lines += ["", "_Run with `python eval/firefly_eval.py`. The authored demo corpus is "
              "evaluated separately by `eval/run_eval.py`; the two corpora are never mixed._"]
    return "\n".join(lines)


def main() -> int:
    r = run()
    here = Path(__file__).resolve().parent
    (here / "firefly_report.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (here / "firefly_report.md").write_text(to_markdown(r), encoding="utf-8")
    print(to_markdown(r))
    print("\nWritten: eval/firefly_report.md · eval/firefly_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
