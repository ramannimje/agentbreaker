"""Velocity gate implementation."""
from __future__ import annotations

from typing import Tuple, Optional


class VelocityGate:
    """Pause and escalate when spend ratio >> completion ratio.

    Default: if spend_ratio > velocity_multiplier * completion_ratio AND spend_ratio > 0.5
    """

    def evaluate(
        self,
        tokens_spent: int,
        token_budget: int,
        tasks_completed: int,
        task_total: Optional[int],
        velocity_multiplier: float = 2.0,
    ) -> Tuple[bool, str]:
        if token_budget <= 0:
            return False, "no budget"
        spend_ratio = tokens_spent / token_budget
        completion_ratio = None
        if task_total and task_total > 0:
            completion_ratio = tasks_completed / task_total

        if completion_ratio is None:
            return False, "completion ratio unavailable"

        if spend_ratio > velocity_multiplier * completion_ratio and spend_ratio > 0.5:
            return True, f"spend_ratio {spend_ratio:.2f} exceeds velocity threshold"

        return False, "within velocity threshold"
