"""The seven supervised agents."""
from .base import Agent, Recommendation, RiskLevel
from .hr_onboarding import HROnboardingAgent
from .sop_coach import SOPCoachAgent
from .workforce_planning import WorkforcePlanningAgent
from .work_order import WorkOrderAgent
from .revenue import RevenueAgent
from .guest_recovery import GuestRecoveryAgent
from .executive_intelligence import ExecutiveIntelligenceAgent

ALL_AGENTS = [
    HROnboardingAgent,
    SOPCoachAgent,
    WorkforcePlanningAgent,
    WorkOrderAgent,
    RevenueAgent,
    GuestRecoveryAgent,
    ExecutiveIntelligenceAgent,
]

__all__ = [
    "Agent", "Recommendation", "RiskLevel", "ALL_AGENTS",
    "HROnboardingAgent", "SOPCoachAgent", "WorkforcePlanningAgent",
    "WorkOrderAgent", "RevenueAgent", "GuestRecoveryAgent",
    "ExecutiveIntelligenceAgent",
]
