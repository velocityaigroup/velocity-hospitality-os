"""Multi-property isolation, provenance governance, and the Firefly seed corpus."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context  # noqa: E402
from velocity_hos.agents.sop_coach import SOPCoachAgent, match_known_gap  # noqa: E402
from velocity_hos.knowledge import (  # noqa: E402
    AZURE_BAY, DEMO_SOPS, FIREFLY, FIREFLY_GAPS, FIREFLY_SOPS,
    PROPERTIES, get_property, property_index,
)


# --------------------------------------------------------------------- registry
def test_two_properties_are_registered():
    assert set(PROPERTIES) == {"azure-bay", "firefly-bequia"}


def test_unknown_property_key_falls_back_to_the_demo_property():
    assert get_property("does-not-exist").key == AZURE_BAY.key
    assert get_property(None).key == AZURE_BAY.key


def test_property_index_is_json_shaped_for_the_console():
    for row in property_index():
        assert {"key", "name", "sops", "departments", "gaps"} <= set(row)
        assert row["sops"] > 0


# ------------------------------------------------------------------- isolation
def test_corpora_never_mix():
    """One tenant, one knowledge base — no record id appears in both properties."""
    azure_ids = {s.sop_id for s in DEMO_SOPS}
    firefly_ids = {s.sop_id for s in FIREFLY_SOPS}
    assert not (azure_ids & firefly_ids)
    assert set(AZURE_BAY.retrieval_docs()) == azure_ids
    assert set(FIREFLY.retrieval_docs()) == firefly_ids


def test_firefly_answers_never_cite_the_demo_corpus():
    agent = SOPCoachAgent()
    docs = FIREFLY.retrieval_docs()
    rec = agent.evaluate(Context(FIREFLY.tenant_id,
                                 {"question": "how much is the estate tour?"}, docs))[0]
    assert rec.sources
    assert all(sid.startswith("FF-") for sid in rec.sources)


# ------------------------------------------------------------------ provenance
def test_every_firefly_record_is_unconfirmed_and_carries_its_source():
    for sop in FIREFLY_SOPS:
        assert sop.confidence == "unconfirmed", sop.sop_id
        assert sop.approval_status == "draft", sop.sop_id
        assert sop.source, sop.sop_id


def test_demo_corpus_records_are_authored():
    assert all(s.confidence == "authored" for s in DEMO_SOPS)


def test_firefly_is_never_described_as_a_live_or_paid_pilot():
    text = FIREFLY.provenance.lower()
    assert "not a live or paid pilot" in text
    for banned in ("paid pilot in production", "customer since", "revenue from firefly"):
        assert banned not in text


# ------------------------------------------------------------------ gap guard
def test_declared_gap_refuses_and_names_the_gap():
    agent = SOPCoachAgent()
    ctx = Context(FIREFLY.tenant_id,
                  {"question": "what is the room rate for a week in March?",
                   "known_gaps": FIREFLY.gaps},
                  FIREFLY.retrieval_docs())
    rec = agent.evaluate(ctx)[0]
    assert rec.proposed_action["type"] == "refusal"
    assert rec.proposed_action["reason"] == "declared_knowledge_gap"
    assert rec.proposed_action["gap_id"] == "G1"
    assert rec.sources == []


def test_gap_guard_does_not_swallow_questions_the_property_has_answered():
    """A published fact must still be answered even when it shares gap vocabulary."""
    agent = SOPCoachAgent()
    for question, expected in [("how much deposit do I pay when booking?", "FF-301"),
                               ("is breakfast included?", "FF-205"),
                               ("can non residents eat at the restaurant?", "FF-401")]:
        ctx = Context(FIREFLY.tenant_id,
                      {"question": question, "known_gaps": FIREFLY.gaps},
                      FIREFLY.retrieval_docs())
        rec = agent.evaluate(ctx)[0]
        assert rec.proposed_action["type"] == "answer", question
        assert rec.sources[0] == expected, question


def test_gap_guard_is_opt_in_and_off_by_default():
    """Without declared gaps the agent behaves exactly as before — no regression."""
    assert match_known_gap("what is the room rate?", []) is None
    assert match_known_gap("what is the room rate?", None) is None


def test_gap_needs_both_a_subject_and_a_detail_term():
    gap = {"gid": "GX", "gap": "x", "terms": ["price"], "topic": ["room"]}
    assert match_known_gap("what is the room price?", [gap]) is not None
    assert match_known_gap("what is the room like?", [gap]) is None   # no detail term
    assert match_known_gap("what is the golf price?", [gap]) is None  # no subject


def test_every_declared_gap_documents_what_the_operator_must_supply():
    for gap in FIREFLY_GAPS:
        assert gap["gid"] and gap["gap"] and gap["blocks"]
        assert gap["needed_from_operator"]


# ---------------------------------------------------------------------- inputs
def test_operational_inputs_are_relative_to_today_so_a_demo_never_goes_stale():
    today = date.today()
    for prop in PROPERTIES.values():
        for hire in prop.inputs(today)["new_hires"]:
            start = date.fromisoformat(hire["start_date"])
            assert start > today, f"{prop.key}: {hire['name']} starts in the past"
            assert start < today + timedelta(days=90)


def test_inputs_carry_the_declared_gaps_to_the_agents():
    assert FIREFLY.inputs()["known_gaps"]
    assert AZURE_BAY.inputs()["known_gaps"] == []
