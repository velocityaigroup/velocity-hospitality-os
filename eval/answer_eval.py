"""Evaluate SOP Coach ANSWER faithfulness (model-dependent).

    python eval/answer_eval.py

Scores whether the language model's generated answer contains the correct fact from
the property's SOP. This is the metric that reflects the *model*, not just retrieval:
run it against the provided open-weights model to get a real quality number.

    VHOS_LLM_BACKEND=openweights VHOS_EMBED_BACKEND=local \
    VHOS_OPENWEIGHTS_URL=https://ht.getimpala.ai/v1 \
    VHOS_OPENWEIGHTS_MODEL=qwen3.6-27b VHOS_OPENWEIGHTS_API_KEY=... \
    python eval/answer_eval.py

Offline (default) it is a near-100% sanity baseline. Prints a report and writes
eval/answer_report.md / .json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from eval.answer_golden import ANSWER_CASES
from eval.golden_sop_set import SOPS
from velocity_hos.agents.base import Context
from velocity_hos.agents.sop_coach import SOPCoachAgent
from velocity_hos.config import settings


def _norm(text: str) -> str:
    """Lowercase and strip everything but alphanumerics for tolerant matching."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _has_fact(answer: str, fact: str) -> bool:
    return _norm(fact) in _norm(answer)


def run() -> dict:
    agent = SOPCoachAgent()  # uses the active backend
    rows = []
    correct = 0
    for question, facts in ANSWER_CASES:
        rec = agent.evaluate(Context("answer-eval", {"question": question}, SOPS))[0]
        answer = rec.summary if rec.proposed_action.get("type") == "answer" else "(refused)"
        ok = all(_has_fact(answer, f) for f in facts)
        correct += int(ok)
        rows.append({"question": question, "required": facts, "pass": ok,
                     "source": (rec.sources[0] if rec.sources else None),
                     "answer": answer[:200]})
    return {
        "backend": settings.llm_backend,
        "model": ({"openweights": settings.openweights_model,
                   "bedrock": settings.bedrock_model_id}
                  .get(settings.llm_backend, "offline deterministic")),
        "total": len(ANSWER_CASES),
        "correct": correct,
        "faithfulness": correct / len(ANSWER_CASES) if ANSWER_CASES else 0.0,
        "rows": rows,
    }


def _fmt(r: dict) -> str:
    lines = ["# SOP Coach — Answer Faithfulness Report", "",
             f"- Backend: **{r['backend']}**  ·  Model: **{r['model']}**",
             f"- Answer faithfulness (contains the correct SOP fact): "
             f"**{r['faithfulness']*100:.0f}%**  ({r['correct']}/{r['total']})", "",
             "| ✓ | question | required fact(s) | source | answer (truncated) |",
             "|---|----------|------------------|--------|--------------------|"]
    for row in r["rows"]:
        mark = "✅" if row["pass"] else "❌"
        ans = row["answer"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {mark} | {row['question']} | {', '.join(row['required'])} | "
                     f"{row['source'] or '—'} | {ans} |")
    return "\n".join(lines)


def main() -> int:
    report = run()
    md = _fmt(report)
    print(md)
    out = Path(__file__).resolve().parent
    (out / "answer_report.md").write_text(md, encoding="utf-8")
    (out / "answer_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
