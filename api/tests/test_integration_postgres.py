import asyncio
import pytest
from uuid import uuid4

from agentbreaker.store.postgres import PostgresStore
from agentbreaker.models import SessionBudget


@pytest.mark.asyncio
async def test_postgresstore_atomic_decrement(postgres_url):
    store = await PostgresStore.connect(postgres_url)
    sid = uuid4()
    s = SessionBudget(session_id=sid, team_id="t1", project_id="p1", token_budget=100)
    await store.create_session(s)

    async def worker():
        try:
            await store.atomic_decrement(sid, 2)
            return True
        except Exception:
            return False

    tasks = [asyncio.create_task(worker()) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    assert sum(1 for r in results if r) == 50
    ss = await store.get_session(sid)
    assert ss.tokens_spent == 100
