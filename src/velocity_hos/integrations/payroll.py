"""Connector for the payroll system."""
from __future__ import annotations

from typing import Any

from .base import Connector


class PayrollConnector(Connector):
    system = "payroll"

    def fetch(self, tenant_id: str) -> dict[str, Any]:
        # TODO: call the real payroll API (REST/webhook) and normalize the payload.
        raise NotImplementedError("Wire up the payroll API during the sprint.")

    def apply(self, tenant_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # TODO: write the approved action back to payroll.
        raise NotImplementedError("Wire up the payroll API during the sprint.")
