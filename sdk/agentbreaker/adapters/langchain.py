"""LangChain adapter: callback handler integrating AgentBreaker enforcement.

This adapter is optional and imports LangChain only at runtime if available.
For testing, the handler can be exercised directly without LangChain.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from agentbreaker.models import SessionBudget, BudgetExceededError, LoopDetectedError, VelocityBreachError
from agentbreaker.store.memory import InMemoryStore
from agentbreaker.core.fingerprint import FingerprintEngine
from agentbreaker.core.velocity import VelocityGate


class AgentBreakerCallbackHandler:
    """Minimal LangChain-like callback handler for enforcing budgets.

    Methods mirror the common callback hooks: `on_tool_start`, `on_llm_end`.
    The handler maintains an in-memory store by default; production users
    should supply a Postgres-backed store.
    """

    def __init__(self, session_id: UUID, budget: int = 10000, team_id: str = "", project_id: str = "default", task_total: Optional[int] = None, store: Optional[InMemoryStore] = None):
        self.session_id = session_id
        self.store = store or InMemoryStore()
        self.fingerprint = FingerprintEngine()
        self.velocity = VelocityGate()
        # ensure session exists
        s = SessionBudget(session_id=session_id, team_id=team_id or "", project_id=project_id or "default", token_budget=budget, task_total=task_total)
        # create session synchronously via async run
        import asyncio

        asyncio.get_event_loop().run_until_complete(self.store.create_session(s))

    def on_tool_start(self, tool: Any, input_str: str, **kwargs: Any) -> None:
        # placeholder: can attach timestamps or in-flight markers
        return None

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when an LLM response completes. Extracts token usage and applies enforcement."""
        # Attempt to extract token usage from response (support common shapes)
        tokens = 0
        if hasattr(response, "usage"):
            usage = getattr(response, "usage")
            tokens = getattr(usage, "total_tokens", getattr(usage, "total", 0))
        elif isinstance(response, dict):
            tokens = response.get("usage", {}).get("total_tokens", 0)

        import asyncio

        async def _process():
            # atomic decrement
            try:
                await self.store.atomic_decrement(self.session_id, int(tokens))
            except ValueError:
                s = await self.store.get_session(self.session_id)
                raise BudgetExceededError(
                    breach_type=None,
                    session_id=s.session_id,
                    tokens_spent=s.tokens_spent,
                    tokens_remaining=max(0, s.token_budget - s.tokens_spent),
                    message="budget exceeded",
                )

            # record call
            await self.store.record_tool_call(self.session_id, getattr(response, "tool_name", "llm"), getattr(response, "args_hash", ""), int(tokens))

            # fingerprint and loop detection
            recent = await self.store.get_recent_calls(self.session_id, self.fingerprint.window_size)
            if self.fingerprint.detect_loop(recent):
                s = await self.store.get_session(self.session_id)
                s.status = "terminated"
                s.termination_reason = None
                raise LoopDetectedError(
                    breach_type=None,
                    session_id=s.session_id,
                    tokens_spent=s.tokens_spent,
                    tokens_remaining=max(0, s.token_budget - s.tokens_spent),
                    message="loop detected",
                )

            # velocity
            s = await self.store.get_session(self.session_id)
            should_pause, reason = self.velocity.evaluate(
                tokens_spent=s.tokens_spent,
                token_budget=s.token_budget,
                tasks_completed=s.tasks_completed,
                task_total=s.task_total or None,
            )
            if should_pause:
                s.status = "paused"
                raise VelocityBreachError(
                    breach_type=None,
                    session_id=s.session_id,
                    tokens_spent=s.tokens_spent,
                    tokens_remaining=max(0, s.token_budget - s.tokens_spent),
                    message=reason,
                )

        asyncio.get_event_loop().run_until_complete(_process())
