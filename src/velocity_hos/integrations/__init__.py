"""Connectors to the existing hotel stack. Velocity integrates; it never replaces."""
from .base import Connector
from .pms import PMSConnector
from .pos import POSConnector
from .payroll import PayrollConnector

__all__ = ["Connector", "PMSConnector", "POSConnector", "PayrollConnector"]
