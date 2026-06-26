"""Base connector contract. Each connector reads signals from and writes approved
actions back to an external system (PMS, POS/Micros, payroll, ...)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Connector(ABC):
    system: str = "system"

    @abstractmethod
    def fetch(self, tenant_id: str) -> dict[str, Any]:
        """Pull current signals for the tenant."""
        raise NotImplementedError

    @abstractmethod
    def apply(self, tenant_id: str, action: dict[str, Any]) -> dict[str, Any]:
        """Write an approved action back to the external system."""
        raise NotImplementedError
