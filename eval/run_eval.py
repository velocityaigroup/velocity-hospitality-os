"""Evaluate the SOP Coach against the golden set and report accuracy.

    python eval/run_eval.py

Reports three metrics that map directly to what judges probe on an agentic RAG
system: retrieval precision (does it find the right SOP?), grounding/citation
(does an in-scope answer cite a source?), and out-of-scope refusal (does it
decline when nothing supports the question, instead of hallucinating policy?).

Offline by default (deterministic, reproducible in CI). Point at a real backend
with VHOS_LLM_BACKEND=bedrock|openweights to score production quality.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from eval.golden_sop_set import CASES, SOPS
from velocity_hos.agents.base import Context
from velocity_hos.agents.sop_coach import SOPCoachAgent


@dataclass
class EvalReport:
    total: int = 0
    in_scope: int = 0
    out_scope: int = 0
    retrieval_correct: int = 0     # top source == expected (in-scope)
    grounded_answers: int = 0      # in-scope answered WITH a source
    refusal_correct: int = 0       # out-of-scope correctly refused
    rows: list[dict] = field(default_factory=list)

    @property
    def retrieval_precision(self) -> float:
        return self.retrieval_correct / self.in_scope if self.in_scope else 0.0

    @property
    def grounding_rate(self) -> float:
        return self.grounded_answers / self.in_scope if self.in_scope else 0.0

    @property
    def refusal_accuracy(self) -> float:
        return self.refusal_correct / self.out_scope if self.out_scope else 0.0

    @property
    def overall(self) -> float:
        correct = self.retrieval_correct + self.refusal_correct
        return correct / self.total if self.total else 0.0


def run() -> EvalReport:
    agent = SOPCoachAgent()  # offline unless VHOS_LLM_BACKEND is set
    rep = EvalReport(total=len(CASES))
    for question, expected in CASES:
        recs = agent.evaluate(Context("eval-tenant", {"question": question}, SOPS))
        rec = recs[0] if recs else None
        top = rec.sources[0] if (rec and rec.sources) else None
        refused = bool(rec) and rec.proposed_action.get("type") == "refusal"

        if expected is None:  # out-of-scope
            rep.out_scope += 1
            ok = refused
            rep.refusal_correct += int(ok)
            outcome = "REFUSED" if refused else f"answered ({top})"
        else:                 # in-scope
            rep.in_scope += 1
            ok = top == expected
            rep.retrieval_correct += int(ok)
            rep.grounded_answers += int(bool(top) and not refused)
            outcome = f"{top}" if top else ("REFUSED" if refused else "no-source")

        rep.rows.append({"question": question, "expected": expected,
                         "outcome": outcome, "pass": ok})
    return rep


def _fmt(report: EvalReport) -> str:
    lines = ["# SOP Coach — Evaluation Report", ""]
    lines.append(f"- Cases: {report.total}  (in-scope {report.in_scope}, out-of-scope {report.out_scope})")
    lines.append(f"- Retrieval precision@1 (in-scope): {report.retrieval_precision*100:.0f}%")
    lines.append(f"- Grounding/citation rate (in-scope answered with a source): {report.grounding_rate*100:.0f}%")
    lines.append(f"- Out-of-scope refusal accuracy: {report.refusal_accuracy*100:.0f}%")
    lines.append(f"- Overall correct (right SOP or right refusal): {report.overall*100:.0f}%")
    lines.append("")
    lines.append("| ✓ | question | expected | outcome |")
    lines.append("|---|----------|----------|---------|")
    for r in report.rows:
        mark = "✅" if r["pass"] else "❌"
        lines.append(f"| {mark} | {r['question']} | {r['expected'] or '(refuse)'} | {r['outcome']} |")
    return "\n".join(lines)


def main() -> int:
    report = run()
    md = _fmt(report)
    print(md)
    out_dir = Path(__file__).resolve().parent
    (out_dir / "last_report.md").write_text(md, encoding="utf-8")
    (out_dir / "last_report.json").write_text(json.dumps({
        "retrieval_precision": report.retrieval_precision,
        "grounding_rate": report.grounding_rate,
        "refusal_accuracy": report.refusal_accuracy,
        "overall": report.overall,
        "total": report.total,
        "rows": report.rows,
    }, indent=2), encoding="utf-8")
    # Non-zero exit if quality regressed, so CI can gate on it.
    ok = report.retrieval_precision >= 0.85 and report.refusal_accuracy >= 0.85
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
