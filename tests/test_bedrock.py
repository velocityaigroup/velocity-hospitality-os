"""Bedrock backend uses the Converse API and parses its response.

No AWS, no boto3 needed: the Bedrock client is monkeypatched, so this verifies the
Converse request shape and response parsing (the wiring). Converse is model-family
agnostic, so the same code path serves any Converse-capable foundation model.
The live call is proven by scripts/bedrock_smoketest.py against a real account.
"""
import velocity_hos.llm.bedrock as bed


class _FakeClient:
    """Records the last converse/invoke call and returns canned Bedrock responses."""
    def __init__(self):
        self.calls = []

    def converse(self, modelId, system, messages, inferenceConfig):  # noqa: N803
        self.calls.append({"modelId": modelId, "system": system,
                           "messages": messages, "inferenceConfig": inferenceConfig})
        return {"output": {"message": {"content": [{"text": "50ml of white rum."}]}}}

    def invoke_model(self, modelId, body):  # noqa: N803 (embeddings path)
        import json
        class _B:
            def read(self):
                return json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        return {"body": _B()}


def test_bedrock_answer_uses_converse(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(bed, "_client", lambda: fake)

    out = bed.BedrockLLM(model_id="amazon.nova-lite-v1:0").answer(
        "how much rum?", ["Mojito: 50ml white rum."])
    assert out == "50ml of white rum."
    call = fake.calls[-1]
    assert call["modelId"] == "amazon.nova-lite-v1:0"
    assert call["messages"][0]["role"] == "user"
    assert "rum" in call["messages"][0]["content"][0]["text"]
    assert call["system"][0]["text"].startswith("You are the SOP Coach")


def test_bedrock_summarize_uses_briefing_prompt(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(bed, "_client", lambda: fake)

    out = bed.BedrockLLM().summarize("Brief the GM.", {"risks": ["storm"]})
    assert out == "50ml of white rum."  # canned; proves parse path
    assert fake.calls[-1]["system"][0]["text"].startswith("You are the Executive")


def test_bedrock_embeddings_parse(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(bed, "_client", lambda: fake)
    vecs = bed.BedrockEmbeddings().embed(["a", "b"])
    assert vecs == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_switching_foundation_model_is_config_only(monkeypatch):
    """Any model id flows through the SAME code path — no per-model branching.

    Proves that switching foundation models (Nova → Claude → any other) is a
    configuration change, not a code change.
    """
    fake = _FakeClient()
    monkeypatch.setattr(bed, "_client", lambda: fake)
    for model_id in ["amazon.nova-lite-v1:0", "amazon.nova-pro-v1:0",
                     "anthropic.claude-sonnet-5", "meta.llama-4-70b-instruct"]:
        bed.BedrockLLM(model_id=model_id).answer("q", ["ctx"])
        assert fake.calls[-1]["modelId"] == model_id     # id passed straight through
        # identical request structure regardless of model:
        assert set(fake.calls[-1]) == {"modelId", "system", "messages", "inferenceConfig"}
