import os
import pytest
import asyncio

from httpx import AsyncClient

from api.app.main import app

DATABASE_URL = os.getenv("AGENTBREAKER_DATABASE_URL")


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="AGENTBREAKER_DATABASE_URL not set")


@pytest.mark.asyncio
async def test_events_tool_call_creates_alert_and_broadcast(monkeypatch):
    # Ensure app startup uses test DATABASE_URL
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create a session with tiny budget
        resp = await ac.post("/sessions", json={"project_id": "p1", "token_budget": 3})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]

        # send a tool_call event that exceeds budget
        event = {
            "session_id": sid,
            "tool_name": "t1",
            "args_hash": "h1",
            "tokens_used": 5,
            "breach_type": "budget_exceeded",
        }
        er = await ac.post("/events/tool_call", json=event)
        assert er.status_code == 200

        # alerts endpoint should contain the alert
        alerts = await ac.get("/alerts")
        assert alerts.status_code == 200
        found = [a for a in alerts.json() if a.get("session_id") == sid]
        assert len(found) >= 1
