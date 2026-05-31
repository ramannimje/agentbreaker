import asyncio
import pytest
from uuid import uuid4

from agentbreaker.core.circuit import session
from agentbreaker.models import BudgetExceededError


@pytest.mark.asyncio
async def test_context_manager_record_and_budget():
    sid = uuid4()
    async with session(session_id=sid, budget=5) as s:
        # one record of 3 tokens
        await s.record(tool_name="t1", args_hash="h1", tokens_used=3)
        # second record of 3 tokens should raise BudgetExceededError
        with pytest.raises(BudgetExceededError):
            await s.record(tool_name="t2", args_hash="h2", tokens_used=3)


def test_decorator_usage_sync():
    sid = uuid4()

    @session(session_id=sid, budget=2)
    def fn():
        # sync function; the decorator will run it inside an event loop
        return "done"

    res = fn()
    assert res == "done"
