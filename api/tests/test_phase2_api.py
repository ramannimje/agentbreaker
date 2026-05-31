import os
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_teams_crud_and_session_budget_and_trace(postgres_url):
    os.environ["AGENTBREAKER_DATABASE_URL"] = postgres_url
    from api.app.main import create_app

    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create team
        resp = await ac.post("/teams", json={"name": "T1", "default_budget": 5000})
        assert resp.status_code == 200
        tid = resp.json()["team_id"]

        # get team
        g = await ac.get(f"/teams/{tid}")
        assert g.status_code == 200

        # create session attached to team
        s = await ac.post("/sessions", json={"team_id": tid, "project_id": "p1", "token_budget": 100})
        assert s.status_code == 200
        sid = s.json()["session_id"]

        # patch budget
        p = await ac.patch(f"/sessions/{sid}/budget", json={"tokens_spent": 10})
        assert p.status_code == 200

        # post a tool call to create trace
        ev = {
            "session_id": sid,
            "tool_name": "t1",
            "args_hash": "h1",
            "tokens_used": 5,
        }
        er = await ac.post("/events/tool_call", json=ev)
        assert er.status_code == 200

        # get trace
        tr = await ac.get(f"/sessions/{sid}/trace")
        assert tr.status_code == 200
        assert isinstance(tr.json(), list)
