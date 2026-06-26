"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"
    )
    state_table: str = os.getenv("DDB_STATE_TABLE", "vhos-state")
    audit_table: str = os.getenv("DDB_AUDIT_TABLE", "vhos-audit")
    approval_webhook_url: str | None = os.getenv("APPROVAL_WEBHOOK_URL") or None


settings = Settings()
