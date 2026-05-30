"""AgentBreaker — Real-time budget enforcement for multi-agent systems."""

__version__ = "0.1.0"

from agentbreaker.core.circuit import session
from agentbreaker.models import (
    BreachType,
    CircuitBreakerError,
    BudgetExceededError,
    LoopDetectedError,
    VelocityBreachError,
)

__all__ = [
    "session",
    "BreachType",
    "CircuitBreakerError",
    "BudgetExceededError",
    "LoopDetectedError",
    "VelocityBreachError",
]
