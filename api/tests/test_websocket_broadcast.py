import os
import asyncio
import socket
import json
import subprocess
import time

import pytest
import websockets
from httpx import AsyncClient


def find_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr, port = s.getsockname()
    s.close()
    return port


@pytest.mark.asyncio
async def test_websocket_broadcasts(postgres_url):
    os.environ["AGENTBREAKER_DATABASE_URL"] = postgres_url
    port = find_free_port()

    # start uvicorn as a subprocess
    uvicorn_cmd = [
        "uvicorn",
        "api.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(
        uvicorn_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        # wait for server to be ready
        await asyncio.sleep(1)

        async with AsyncClient(base_url=f"http://127.0.0.1:{port}") as ac:
            # connect websocket to all sessions
            ws_uri = f"ws://127.0.0.1:{port}/ws/sessions"
            async with websockets.connect(ws_uri) as ws:
                # create a session
                resp = await ac.post("/sessions", json={"project_id": "p1", "token_budget": 3})
                assert resp.status_code == 200
                sid = resp.json()["session_id"]

                # connect session-specific websocket
                session_ws_uri = f"ws://127.0.0.1:{port}/ws/sessions/{sid}"
                async with websockets.connect(session_ws_uri) as session_ws:
                    # post a tool_call that triggers an alert/broadcast
                    event = {
                        "session_id": sid,
                        "tool_name": "t1",
                        "args_hash": "h1",
                        "tokens_used": 5,
                        "breach_type": "budget_exceeded",
                    }
                    er = await ac.post("/events/tool_call", json=event)
                    assert er.status_code == 200

                    # wait for message on either websocket
                    async def recv_one(ws_conn):
                        try:
                            msg = await asyncio.wait_for(ws_conn.recv(), timeout=5)
                            return json.loads(msg)
                        except Exception:
                            return None

                    msg_all = await recv_one(ws)
                    msg_session = await recv_one(session_ws)

                    assert msg_all or msg_session, "No broadcast received on websockets"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
