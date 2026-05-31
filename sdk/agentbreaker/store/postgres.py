"""PostgreSQL store implementation using asyncpg.

Provides atomic_decrement using row-level locking (SELECT ... FOR UPDATE)
"""
from __future__ import annotations

import asyncio
from typing import List
from uuid import UUID

import asyncpg

from agentbreaker.models import SessionBudget, ToolCallRecord


class PostgresStore:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> "PostgresStore":
        pool = await asyncpg.create_pool(database_url)
        return cls(pool)

    async def create_session(self, session: SessionBudget) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions(session_id, team_id, project_id, token_budget, tokens_spent, task_total, tasks_completed, status, created_at)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (session_id) DO NOTHING
                """,
                str(session.session_id),
                session.team_id,
                session.project_id,
                session.token_budget,
                session.tokens_spent,
                session.task_total,
                session.tasks_completed,
                session.status,
                session.created_at,
            )

    async def get_session(self, session_id: UUID) -> SessionBudget:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT session_id, team_id, project_id, token_budget, tokens_spent, task_total, tasks_completed, status, created_at, terminated_at, termination_reason FROM sessions WHERE session_id = $1",
                str(session_id),
            )
            if not row:
                raise KeyError("session not found")
            return SessionBudget(
                session_id=UUID(row["session_id"]),
                team_id=row["team_id"],
                project_id=row["project_id"],
                token_budget=row["token_budget"],
                tokens_spent=row["tokens_spent"],
                task_total=row["task_total"],
                tasks_completed=row["tasks_completed"],
                status=row["status"],
                created_at=row["created_at"],
                terminated_at=row["terminated_at"],
                termination_reason=row["termination_reason"],
            )

    async def atomic_decrement(self, session_id: UUID, tokens_used: int) -> SessionBudget:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT tokens_spent, token_budget, status FROM sessions WHERE session_id = $1 FOR UPDATE",
                    str(session_id),
                )
                if not row:
                    raise KeyError("session not found")
                tokens_spent = row["tokens_spent"]
                token_budget = row["token_budget"]
                status = row["status"]
                if status != "active":
                    # return current state
                    cur = await conn.fetchrow("SELECT * FROM sessions WHERE session_id=$1", str(session_id))
                    return await self.get_session(session_id)
                if tokens_spent + tokens_used > token_budget:
                    # terminate
                    await conn.execute(
                        "UPDATE sessions SET status='terminated', terminated_at=now(), termination_reason='budget_exceeded' WHERE session_id = $1",
                        str(session_id),
                    )
                    raise ValueError("budget_exceeded")
                await conn.execute(
                    "UPDATE sessions SET tokens_spent = tokens_spent + $1 WHERE session_id = $2",
                    tokens_used,
                    str(session_id),
                )
                return await self.get_session(session_id)

    async def record_tool_call(self, session_id: UUID, tool_name: str, args_hash: str, tokens_used: int) -> ToolCallRecord:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tool_call_log(session_id, tool_name, args_hash, tokens_used) VALUES($1,$2,$3,$4) RETURNING call_id, timestamp",
                str(session_id),
                tool_name,
                args_hash,
                tokens_used,
            )
            return ToolCallRecord(
                call_id=UUID(row["call_id"]),
                session_id=session_id,
                tool_name=tool_name,
                args_hash=args_hash,
                tokens_used=tokens_used,
                timestamp=row["timestamp"],
            )

    async def get_recent_calls(self, session_id: UUID, window_size: int) -> List[ToolCallRecord]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT call_id, session_id, tool_name, args_hash, tokens_used, timestamp FROM tool_call_log WHERE session_id = $1 ORDER BY timestamp DESC LIMIT $2",
                str(session_id),
                window_size,
            )
            # return chronological order
            records = [ToolCallRecord(call_id=UUID(r["call_id"]), session_id=UUID(r["session_id"]), tool_name=r["tool_name"], args_hash=r["args_hash"], tokens_used=r["tokens_used"], timestamp=r["timestamp"]) for r in rows]
            return list(reversed(records))

    async def increment_tasks_completed(self, session_id: UUID, amount: int = 1) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE sessions SET tasks_completed = tasks_completed + $1 WHERE session_id = $2",
                amount,
                str(session_id),
            )
