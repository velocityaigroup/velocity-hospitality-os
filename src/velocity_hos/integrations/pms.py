"""Connector for the property management system (PMS)."""
from __future__ import annotations

from typing import Any

from .base import Connector


class PMSConnector(Connector):
    system = "pms"

    def fetch(self, tenant_id: str) -> dict[str, Any]:
        # TODO: call the real pms API (REST/webhook) and normalize the payload.
        raise NotImplementedError("Wire up the pms API during the sprint.")

    def apply(self, tenant_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # TODO: write the approved action back to pms.
        raise NotImplementedError("Wire up the pms API during the sprint.")
