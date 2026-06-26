"""Base contracts shared by every agent.

An agent observes operational `context`, reasons about it against the property's
own SOPs/standards, and returns zero or more `Recommendation`s. Agents never act
directly on systems — consequential recommendations are routed to a human via the
approval gate before any action is executed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Determines whether human approval is required before acting."""
    INFO = "info"        # no action; surfaced for awareness
    LOW = "low"          # safe to auto-execute (still logged)
    REQUIRES_APPROVAL = "requires_approval"  # touches money/staffing/guest


@dataclass
class Recommendation:
    agent: str
    summary: str
    risk: RiskLevel
    proposed_action: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    sources: list[str] = field(default_factory=list)  # SOPs / data referenced


@dataclass
class Context:
    """The slice of operational state an agent reasons over."""
    tenant_id: str
    inputs: dict[str, Any] = field(default_factory=dict)   # PMS/POS/messages/etc.
    sops: dict[str, Any] = field(default_factory=dict)     # property standards


class Agent(ABC):
    """Abstract supervised agent."""
    name: str = "agent"

    @abstractmethod
    def evaluate(self, ctx: Context) -> list[Recommendation]:
        """Return recommendations for the given context. Pure: no side effects."""
        raise NotImplementedError
