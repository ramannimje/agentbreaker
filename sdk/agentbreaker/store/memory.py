"""In-memory store implementation for AgentBreaker (development/testing)."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque, List
from uuid import UUID

from agentbreaker.models import SessionBudget, ToolCallRecord


class InMemoryStore:
    """Thread-safe asyncio in-memory store.

    Stores sessions and tool call logs per session. Uses an asyncio.Lock per
    session to provide atomic operations for `atomic_decrement`.
    """

    def __init__(self):
        self._sessions: Dict[UUID, SessionBudget] = {}
        self._tool_calls: Dict[UUID, Deque[ToolCallRecord]] = defaultdict(deque)
        self._locks: Dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def create_session(self, session: SessionBudget) -> None:
        self._sessions[session.session_id] = session

    async def get_session(self, session_id: UUID) -> SessionBudget:
        return self._sessions[session_id]

    async def atomic_decrement(self, session_id: UUID, tokens_used: int) -> SessionBudget:
        lock = self._locks[session_id]
        async with lock:
            s = self._sessions[session_id]
            if s.status != "active":
                return s
            if s.tokens_spent + tokens_used > s.token_budget:
                # terminate the session
                s.termination_reason = None
                s.status = "terminated"
                s.terminated_at = s.terminated_at or s.created_at
                raise ValueError("budget_exceeded")
            s.tokens_spent += tokens_used
            return s

    async def record_tool_call(
        self, session_id: UUID, tool_name: str, args_hash: str, tokens_used: int
    ) -> ToolCallRecord:
        rec = ToolCallRecord(
            session_id=session_id, tool_name=tool_name, args_hash=args_hash, tokens_used=tokens_used
        )
        self._tool_calls[session_id].append(rec)
        # keep some reasonable cap (e.g., 1000) to avoid unbounded memory
        if len(self._tool_calls[session_id]) > 2000:
            self._tool_calls[session_id].popleft()
        return rec

    async def get_recent_calls(self, session_id: UUID, window_size: int) -> List[ToolCallRecord]:
        dq = self._tool_calls.get(session_id, deque())
        return list(dq)[-window_size:]

    async def increment_tasks_completed(self, session_id: UUID, amount: int = 1) -> None:
        s = self._sessions[session_id]
        s.tasks_completed += amount
