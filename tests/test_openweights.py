"""Open-weights backend shapes OpenAI-compatible requests and parses responses.

No network: the HTTP POST is monkeypatched, so this verifies wiring/parsing only
(the real model runs on the GPU host — see docs/openweights-runbook.md).
"""
import io
import urllib.error

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


class _FakeResponse:
    """Minimal stand-in for the urlopen context manager."""

    def __init__(self, body=b'{"ok": true}'):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _http_error(code):
    return urllib.error.HTTPError("http://gateway/v1", code, "boom", {}, io.BytesIO(b""))


def test_post_retries_transient_gateway_failure(monkeypatch):
    """A shared inference gateway drops the occasional long generation with a
    502. One blip must not end a four-agent cycle that is otherwise working."""
    attempts = {"n": 0}

    def flaky_urlopen(request, timeout=None):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _http_error(502)
        return _FakeResponse()

    monkeypatch.setattr(ow.urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(ow.time, "sleep", lambda seconds: None)

    assert ow._post("/chat/completions", {"model": "m"}) == {"ok": True}
    assert attempts["n"] == 3


def test_post_does_not_retry_a_bad_request(monkeypatch):
    """400/404/422 mean the request itself is wrong. Retrying wastes time and
    hides the error from the caller's own fallback path."""
    attempts = {"n": 0}

    def rejecting_urlopen(request, timeout=None):
        attempts["n"] += 1
        raise _http_error(400)

    monkeypatch.setattr(ow.urllib.request, "urlopen", rejecting_urlopen)
    monkeypatch.setattr(ow.time, "sleep", lambda seconds: None)

    try:
        ow._post("/chat/completions", {"model": "m"})
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:  # pragma: no cover
        raise AssertionError("expected HTTPError")
    assert attempts["n"] == 1


def test_post_gives_up_after_the_attempt_limit(monkeypatch):
    """Retry is bounded: a gateway that is genuinely down must surface, not hang."""
    attempts = {"n": 0}

    def always_502(request, timeout=None):
        attempts["n"] += 1
        raise _http_error(502)

    monkeypatch.setattr(ow.urllib.request, "urlopen", always_502)
    monkeypatch.setattr(ow.time, "sleep", lambda seconds: None)

    try:
        ow._post("/chat/completions", {"model": "m"})
    except urllib.error.HTTPError as exc:
        assert exc.code == 502
    else:  # pragma: no cover
        raise AssertionError("expected HTTPError")
    assert attempts["n"] == ow._MAX_ATTEMPTS
