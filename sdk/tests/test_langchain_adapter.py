import asyncio
import pytest
from uuid import uuid4

from agentbreaker.adapters.langchain import AgentBreakerCallbackHandler
from agentbreaker.models import BudgetExceededError, LoopDetectedError


class DummyResponse:
    def __init__(self, total_tokens: int, tool_name: str = "llm"):
        self.usage = type("U", (), {"total_tokens": total_tokens})
        self.tool_name = tool_name


def test_langchain_adapter_budget_exceeded():
    sid = uuid4()
    handler = AgentBreakerCallbackHandler(session_id=sid, budget=5)

    # first call uses 3 tokens
    handler.on_llm_end(DummyResponse(3))
    # second call uses 3 tokens -> should raise BudgetExceededError
    with pytest.raises(BudgetExceededError):
        handler.on_llm_end(DummyResponse(3))


def test_langchain_adapter_loop_detection():
    sid = uuid4()
    handler = AgentBreakerCallbackHandler(session_id=sid, budget=1000)

    # create simple repeat A,A,A
    handler.on_llm_end(DummyResponse(1))
    # simulate tool_name and args_hash by attaching attributes
    r = DummyResponse(1)
    r.tool_name = "calc"
    r.args_hash = "h1"
    handler.on_llm_end(r)
    handler.on_llm_end(r)
    # third repeat should raise LoopDetectedError
    with pytest.raises(LoopDetectedError):
        handler.on_llm_end(r)
