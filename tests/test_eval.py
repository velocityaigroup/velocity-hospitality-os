"""The SOP Coach eval must stay high — CI gates on it."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from eval.run_eval import run


def test_eval_metrics_meet_bar():
    rep = run()
    assert rep.retrieval_precision >= 0.85    # finds the right SOP
    assert rep.refusal_accuracy >= 0.85       # refuses out-of-scope
    assert rep.grounding_rate >= 0.85         # in-scope answers cite a source
