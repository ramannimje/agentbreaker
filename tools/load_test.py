"""Simple load test harness to exercise the /events/tool_call endpoint."""
import asyncio
import os
import random
import uuid

import httpx


async def worker(base_url, session_id):
    async with httpx.AsyncClient(base_url=base_url) as client:
        for _ in range(10):
            await client.post(
                "/events/tool_call",
                json={
                    "session_id": session_id,
                    "tool_name": "t",
                    "args_hash": str(uuid.uuid4()),
                    "tokens_used": random.randint(1, 10),
                },
            )


async def main():
    base = os.getenv("AGENTBREAKER_BASE_URL", "http://127.0.0.1:8000")
    # create a session
    async with httpx.AsyncClient(base_url=base) as client:
        r = await client.post("/sessions", json={"project_id": "load", "token_budget": 100000})
        sid = r.json()["session_id"]

    await asyncio.gather(*[worker(base, sid) for _ in range(20)])


if __name__ == "__main__":
    asyncio.run(main())
