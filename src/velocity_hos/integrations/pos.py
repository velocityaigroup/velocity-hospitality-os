"""Connector for the point-of-sale (POS/Micros)."""
from __future__ import annotations

from typing import Any

from .base import Connector


class POSConnector(Connector):
    system = "pos"

    def fetch(self, tenant_id: str) -> dict[str, Any]:
        # TODO: call the real pos API (REST/webhook) and normalize the payload.
        raise NotImplementedError("Wire up the pos API during the sprint.")

    def apply(self, tenant_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # TODO: write the approved action back to pos.
        raise NotImplementedError("Wire up the pos API during the sprint.")
