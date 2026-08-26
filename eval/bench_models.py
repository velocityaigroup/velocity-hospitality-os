"""Benchmark foundation models on Velocity's hospitality use cases.

Runs the golden SOP set through the CURRENTLY CONFIGURED provider and reports the
signals that matter for the buildathon demo: answer latency, faithfulness to the
retrieved SOP (grounded recall), conciseness, and out-of-scope refusal. Provider-
agnostic — point it at any model and compare.

    # Bench two Bedrock foundation models and compare:
    VHOS_LLM_BACKEND=bedrock VHOS_EMBED_BACKEND=local \
      BEDROCK_MODEL_ID=amazon.nova-lite-v1:0 python eval/bench_models.py --label nova-lite
    VHOS_LLM_BACKEND=bedrock VHOS_EMBED_BACKEND=local \
      BEDROCK_MODEL_ID=amazon.nova-pro-v1:0  python eval/bench_models.py --label nova-pro
    python eval/bench_models.py --compare        # prints a comparison table

Faithfulness = share of the expected SOP's key content tokens that survive into the
answer (a grounding proxy); latency is measured with a monotonic clock.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from eval.golden_sop_set import CASES, SOPS          # noqa: E402
from velocity_hos.agents.base import Context          # noqa: E402
from velocity_hos.agents.sop_coach import SOPCoachAgent  # noqa: E402
from velocity_hos.config import settings              # noqa: E402
from velocity_hos.rag.grounding import content_tokens  # noqa: E402

_OUT = Path(__file__).resolve().parent


def _label_default() -> str:
    return settings.bedrock_model_id if settings.llm_backend == "bedrock" else settings.llm_backend


def run(label: str) -> dict:
    agent = SOPCoachAgent()
    lat_ms: list[float] = []
    faith: list[float] = []
    lengths: list[int] = []
    refuse_ok = refuse_total = 0
    for question, expected in CASES:
        t0 = time.monotonic()
        rec = agent.evaluate(Context("bench", {"question": question}, SOPS))[0]
        lat_ms.append((time.monotonic() - t0) * 1000)
        refused = rec.proposed_action.get("type") == "refusal"
        if expected is None:
            refuse_total += 1
            refuse_ok += int(refused)
            continue
        lengths.append(len(rec.summary))
        # faithfulness = recall of the expected SOP's key tokens in the answer
        want = content_tokens(SOPS[expected])
        got = content_tokens(rec.summary)
        faith.append(len(want & got) / len(want) if want else 0.0)

    def avg(xs):
        return round(sum(xs) / len(xs), 3) if xs else 0.0

    result = {
        "label": label,
        "backend": settings.llm_backend,
        "model": _label_default(),
        "avg_latency_ms": round(avg(lat_ms), 1),
        "faithfulness": avg(faith),          # 0..1 grounded-recall
        "refusal_accuracy": round(refuse_ok / refuse_total, 3) if refuse_total else 0.0,
        "avg_answer_chars": round(avg(lengths)),
        "n_cases": len(CASES),
    }
    (_OUT / f"bench_{label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


def compare() -> None:
    rows = [json.loads(p.read_text()) for p in sorted(_OUT.glob("bench_*.json"))]
    if not rows:
        print("No bench_*.json yet. Run a benchmark first.")
        return
    print(f"{'label':16} {'model':26} {'lat(ms)':>8} {'faith':>7} {'refuse':>7} {'chars':>6}")
    print("-" * 76)
    for r in rows:
        print(f"{r['label']:16} {r['model'][:26]:26} {r['avg_latency_ms']:>8} "
              f"{r['faithfulness']:>7} {r['refusal_accuracy']:>7} {r['avg_answer_chars']:>6}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=None)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    if args.compare:
        compare()
    else:
        run(args.label or _label_default().replace(":", "_").replace("/", "_"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
