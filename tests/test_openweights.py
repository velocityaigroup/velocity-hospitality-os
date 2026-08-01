"""Open-weights backend shapes OpenAI-compatible requests and parses responses.

No network: the HTTP POST is monkeypatched, so this verifies wiring/parsing only
(the real model runs on the GPU host — see docs/openweights-runbook.md).
"""
import velocity_hos.llm.openweights as ow


def test_answer_calls_chat_completions_and_parses(monkeypatch):
    seen = {}

    def fake_post(path, payload, timeout=60.0):
        seen["path"] = path
        seen["payload"] = payload
        return {"choices": [{"message": {"content": "  Per the SOP: 50ml rum.  "}}]}

    monkeypatch.setattr(ow, "_post", fake_post)
    out = ow.OpenWeightsLLM().answer("how much rum?", ["Mojito: 50ml white rum."])
    assert out == "Per the SOP: 50ml rum."                 # trimmed
    assert seen["path"] == "/chat/completions"
    assert seen["payload"]["messages"][0]["role"] == "system"
    assert "rum" in seen["payload"]["messages"][1]["content"]


def test_summarize_uses_briefing_prompt(monkeypatch):
    def fake_post(path, payload, timeout=60.0):
        return {"choices": [{"message": {"content": "Briefing."}}]}

    monkeypatch.setattr(ow, "_post", fake_post)
    out = ow.OpenWeightsLLM().summarize("Brief the GM.", {"risks": ["storm"]})
    assert out == "Briefing."


def test_embeddings_sorted_by_index(monkeypatch):
    def fake_post(path, payload, timeout=60.0):
        assert path == "/embeddings"
        # return out of order to prove we sort by index
        return {"data": [
            {"index": 1, "embedding": [0.3, 0.4]},
            {"index": 0, "embedding": [0.1, 0.2]},
        ]}

    monkeypatch.setattr(ow, "_post", fake_post)
    vecs = ow.OpenWeightsEmbeddings().embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
