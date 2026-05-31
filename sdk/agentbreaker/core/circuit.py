"""Circuit breaker interceptor: decorator and async context manager."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from typing import Optional, Callable, Any
from uuid import UUID

from agentbreaker.models import (
    SessionBudget,
    CircuitBreakerError,
    BudgetExceededError,
    LoopDetectedError,
    VelocityBreachError,
)
from agentbreaker.store.memory import InMemoryStore
from agentbreaker.core.fingerprint import FingerprintEngine
from agentbreaker.core.velocity import VelocityGate


class _SessionContext:
    def __init__(self, session_id: UUID, store: InMemoryStore, fingerprint: FingerprintEngine, velocity: VelocityGate):
        self.session_id = session_id
        self.store = store
        self.fingerprint = fingerprint
        self.velocity = velocity

    async def record(self, tool_name: str, args_hash: str, tokens_used: int, task_completed: bool = False) -> None:
        # Atomic decrement
        try:
            await self.store.atomic_decrement(self.session_id, tokens_used)
        except ValueError:
            # budget exceeded
            s = await self.store.get_session(self.session_id)
            raise BudgetExceededError(
                breach_type=s.termination_reason or None,
                session_id=s.session_id,
                tokens_spent=s.tokens_spent,
                tokens_remaining=max(0, s.token_budget - s.tokens_spent),
                message="budget exceeded",
            )

        # record tool call
        await self.store.record_tool_call(self.session_id, tool_name, args_hash, tokens_used)

        # fingerprint check
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

        # velocity gate
        s = await self.store.get_session(self.session_id)
        if task_completed:
            await self.store.increment_tasks_completed(self.session_id, 1)
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


def session(session_id: UUID, budget: Optional[int] = None, team_id: Optional[str] = None, project_id: Optional[str] = None, task_total: Optional[int] = None, store: Optional[InMemoryStore] = None):
    """Factory that returns a decorator or async context manager for a session.

    Usage:
    @session(session_id=sid, budget=10000)
    async def f(): ...

    async with session(session_id=sid) as s:
        await s.record(...)
    """
    if store is None:
        store = InMemoryStore()
    fingerprint = FingerprintEngine(window_size=10, repeat_threshold=3)
    velocity = VelocityGate()

    @asynccontextmanager
    async def _ctx():
        # ensure session exists
        s = SessionBudget(session_id=session_id, team_id=team_id or "", project_id=project_id or "default", token_budget=budget or 100000, task_total=task_total)
        await store.create_session(s)
        ctx = _SessionContext(session_id, store, fingerprint, velocity)
        try:
            yield ctx
        finally:
            pass

    def _decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                async with _ctx() as sess:
                    return await func(*args, **kwargs)

            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # run sync function inside event loop
                async def _run():
                    async with _ctx() as sess:
                        return func(*args, **kwargs)

                return asyncio.run(_run())

            return wrapper

    # make callable as context manager and decorator
    def _session_callable(obj=None):
        if obj is None:
            return _ctx()
        return _decorator(obj)

    return _session_callable
