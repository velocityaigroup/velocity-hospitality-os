"""Prove the Bedrock path is live on AWS.

Run this with AWS credentials configured and Bedrock model access enabled:

    export AWS_REGION=us-east-1
    python scripts/bedrock_smoketest.py

It calls Bedrock for real — a foundation model (Converse) answering over a tiny SOP —
and prints the results. A green run is your evidence that the agents are genuinely
running on AWS Bedrock (screenshot it for the logbook / data room). Exits 1 with an
actionable message if credentials, region, or model access aren't set up yet.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.config import settings  # noqa: E402


def _fail(msg: str) -> int:
    print(f"\n❌ Bedrock smoke test FAILED\n   {msg}\n")
    print("Checklist:")
    print("  1. AWS credentials configured (aws configure / env vars / role).")
    print("  2. The model is available on this account + region (Converse-capable):")
    print(f"       region = {settings.aws_region}   model = {settings.bedrock_model_id}")
    print("     Some foundation models are entitlement-gated (403) on this account;")
    print("     amazon.nova-lite-v1:0 is available — use it or the open-weights backend.")
    print("  3. IAM allows bedrock:InvokeModel / bedrock:Converse (see docs/bedrock-deploy.md).")
    return 1


def main() -> int:
    print("Velocity Hospitality OS — Bedrock smoke test")
    print(f"  region:     {settings.aws_region}")
    print(f"  llm backend:   {settings.llm_backend}   model: {settings.bedrock_model_id}")
    print(f"  embed backend: {settings.embed_backend}   model: {settings.embed_model_id}\n")

    if settings.llm_backend != "bedrock":
        return _fail("VHOS_LLM_BACKEND is not 'bedrock'. Run: export VHOS_LLM_BACKEND=bedrock")

    try:
        import boto3  # noqa: F401
    except ImportError:
        return _fail("boto3 is not installed. Run: pip install boto3")

    from velocity_hos.agents.base import Context
    from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent
    from velocity_hos.agents.sop_coach import SOPCoachAgent

    sops = {
        "bev.mojito": ("Mojito: 50ml white rum, 8 mint leaves, 25ml lime, 2 tsp sugar, "
                       "top with soda. Free-pour with a jigger."),
    }

    try:
        # Agents pick up the configured backends automatically (get_llm/get_embeddings).
        # Bedrock uses the Converse API — default model is Amazon Nova Lite.
        print(f"→ SOP Coach via Bedrock Converse [{settings.bedrock_model_id}] (RAG) ...", flush=True)
        rec = SOPCoachAgent().evaluate(
            Context("smoketest", {"question": "how much rum in a mojito?"}, sops))[0]
        print("   Q: how much rum in a mojito?")
        print(f"   A: {rec.summary}")
        print(f"   sources: {rec.sources}")

        print("\n→ Executive briefing via Bedrock Converse ...", flush=True)
        signals = {"signals": {"risks": ["Storm Thursday"],
                               "compliance_alerts": ["1 permit expiring"]}}
        brief = ExecutiveIntelligenceAgent().evaluate(Context("smoketest", signals))[0]
        print("   " + brief.summary.replace("\n", "\n   "))
    except Exception as exc:  # noqa: BLE001 — surface any AWS error actionably
        return _fail(f"{type(exc).__name__}: {exc}")

    print(f"\n✅ Bedrock is LIVE — {settings.bedrock_model_id} answered on AWS. Screenshot for the logbook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
