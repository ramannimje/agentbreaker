import os
import asyncio
import pytest
from uuid import uuid4

from agentbreaker.store.postgres import PostgresStore
from agentbreaker.models import SessionBudget

DATABASE_URL = os.getenv("AGENTBREAKER_DATABASE_URL")


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="AGENTBREAKER_DATABASE_URL not set")


@pytest.mark.asyncio
async def test_postgresstore_atomic_decrement():
    store = await PostgresStore.connect(DATABASE_URL)
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
