"""Prove Velocity runs on a self-hosted open-weights model.

Point it at any OpenAI-compatible server — Ollama on your laptop for a quick proof,
or vLLM on the Buildathon H200 for the "on provided compute" version:

    # Fast local proof (Ollama):
    #   ollama serve ; ollama pull llama3.2
    export VHOS_LLM_BACKEND=openweights
    export VHOS_EMBED_BACKEND=local
    export VHOS_OPENWEIGHTS_URL=http://localhost:11434/v1
    export VHOS_OPENWEIGHTS_MODEL=llama3.2
    python scripts/openweights_smoketest.py

A green run means an open-weights model answered through Velocity's agents.
Screenshot it for the logbook / data room.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.config import settings  # noqa: E402

# Windows consoles default to a legacy code page (cp1252) that can't encode the
# symbols below; force UTF-8 so the proof output is clean everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def _fail(msg: str) -> int:
    print(f"\n[FAIL] Open-weights smoke test FAILED\n   {msg}\n")
    print("Checklist:")
    print("  1. The gateway is reachable at VHOS_OPENWEIGHTS_URL:")
    print(f"       {settings.openweights_base_url}")
    print("  2. VHOS_LLM_BACKEND=openweights")
    print(f"  3. The model name matches the gateway's: {settings.openweights_model}")
    print("  4. VHOS_OPENWEIGHTS_API_KEY is set to your team key (starts with sk-).")
    return 1


def main() -> int:
    print("Velocity Hospitality OS — open-weights smoke test")
    print(f"  llm backend:   {settings.llm_backend}")
    print(f"  server:        {settings.openweights_base_url}")
    print(f"  model:         {settings.openweights_model}")
    print(f"  embed backend: {settings.embed_backend}\n")

    if settings.llm_backend != "openweights":
        return _fail("VHOS_LLM_BACKEND is not 'openweights'. Run: export VHOS_LLM_BACKEND=openweights")

    from velocity_hos.agents.base import Context
    from velocity_hos.agents.sop_coach import SOPCoachAgent

    sops = {
        "bev.mojito": ("Mojito: 50ml white rum, 8 mint leaves, 25ml lime, 2 tsp sugar, "
                       "top with soda. Free-pour with a jigger."),
    }
    try:
        print("-> SOP Coach via the open-weights model (RAG) ...", flush=True)
        rec = SOPCoachAgent().evaluate(
            Context("smoketest", {"question": "how much rum in a mojito?"}, sops))[0]
        print("   Q: how much rum in a mojito?")
        print(f"   A: {rec.summary}")
        print(f"   sources: {rec.sources}")
    except Exception as exc:  # noqa: BLE001
        return _fail(f"{type(exc).__name__}: {exc}")

    print("\n✅ An open-weights model answered through Velocity. Screenshot this for the logbook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
