import asyncio
import pytest

from agentbreaker.store.memory import InMemoryStore
from agentbreaker.core.fingerprint import FingerprintEngine
from agentbreaker.core.velocity import VelocityGate
from agentbreaker.models import SessionBudget


@pytest.mark.asyncio
async def test_atomic_decrement_concurrent():
    store = InMemoryStore()
    s = SessionBudget(team_id="t1", project_id="p1", token_budget=100)
    await store.create_session(s)

    async def worker():
        try:
            await store.atomic_decrement(s.session_id, 2)
            return True
        except Exception:
            return False

    tasks = [asyncio.create_task(worker()) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    # All 50 should succeed (50 * 2 = 100)
    assert sum(1 for r in results if r) == 50
    ss = await store.get_session(s.session_id)
    assert ss.tokens_spent == 100


@pytest.mark.asyncio
async def test_fingerprint_repeat_and_rotating():
    fe = FingerprintEngine(window_size=10, repeat_threshold=3)
    store = InMemoryStore()
    s = SessionBudget(team_id="t1", project_id="p1", token_budget=1000)
    await store.create_session(s)

    # simple repeat
    for _ in range(3):
        await store.record_tool_call(s.session_id, "calc", "hash1", 1)
    recent = await store.get_recent_calls(s.session_id, 10)
    assert fe.detect_loop(recent)

    # rotating pattern A->B->A->B
    s2 = SessionBudget(team_id="t1", project_id="p1", token_budget=1000)
    await store.create_session(s2)
    await store.record_tool_call(s2.session_id, "A", "h1", 1)
    await store.record_tool_call(s2.session_id, "B", "h2", 1)
    await store.record_tool_call(s2.session_id, "A", "h1", 1)
    await store.record_tool_call(s2.session_id, "B", "h2", 1)
    recent2 = await store.get_recent_calls(s2.session_id, 10)
    assert fe.detect_loop(recent2)


def test_velocity_gate():
    vg = VelocityGate()
    # spend_ratio = 0.8, completion_ratio = 0.2 -> spend > 2*completion and > 0.5
    should_pause, msg = vg.evaluate(tokens_spent=80, token_budget=100, tasks_completed=2, task_total=10)
    assert should_pause is True
