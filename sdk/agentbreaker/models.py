"""Pydantic data models for AgentBreaker."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BreachType(str, Enum):
    """Types of budget breaches."""

    BUDGET_EXCEEDED = "budget_exceeded"
    LOOP_DETECTED = "loop_detected"
    VELOCITY_BREACH = "velocity_breach"


class SessionBudget(BaseModel):
    """Budget tracking for a single agent session."""

    session_id: UUID = Field(default_factory=uuid4)
    team_id: str
    project_id: str
    token_budget: int = Field(gt=0)
    tokens_spent: int = Field(default=0, ge=0)
    task_total: Optional[int] = Field(default=None, gt=0)
    tasks_completed: int = Field(default=0, ge=0)
    status: str = Field(default="active")  # active | paused | terminated
    created_at: datetime = Field(default_factory=datetime.utcnow)
    terminated_at: Optional[datetime] = None
    termination_reason: Optional[BreachType] = None

    class Config:
        use_enum_values = False


class ToolCallRecord(BaseModel):
    """Record of a single tool call."""

    call_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    tool_name: str
    args_hash: str  # SHA-256 hash of canonical JSON args
    tokens_used: int = Field(gt=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    fingerprint_contribution: Optional[str] = None  # Composite fingerprint at this point


class CircuitBreakerResult(BaseModel):
    """Result of a circuit breaker check."""

    allowed: bool
    breach_type: Optional[BreachType] = None
    tokens_remaining: int
    spend_ratio: float = Field(ge=0.0, le=1.0)
    completion_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fingerprint_match: bool = False
    message: str


class Alert(BaseModel):
    """Alert for a budget breach."""

    alert_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    breach_type: BreachType
    payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None


# Exception hierarchy


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker breaches."""

    def __init__(
        self,
        breach_type: BreachType,
        session_id: UUID,
        tokens_spent: int,
        tokens_remaining: int,
        message: str,
    ):
        self.breach_type = breach_type
        self.session_id = session_id
        self.tokens_spent = tokens_spent
        self.tokens_remaining = tokens_remaining
        self.message = message
        super().__init__(message)


class BudgetExceededError(CircuitBreakerError):
    """Raised when session exceeds token budget."""

    pass


class LoopDetectedError(CircuitBreakerError):
    """Raised when repetitive tool calls are detected."""

    pass


class VelocityBreachError(CircuitBreakerError):
    """Raised when spend rate outpaces task completion."""

    pass
