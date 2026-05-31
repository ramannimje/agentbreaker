"""Simple WebSocket broadcaster for session burn updates."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket

class Broadcaster:
    def __init__(self):
        # mapping session_id -> set of websockets
        self.clients: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str | None = None):
        await websocket.accept()
        key = session_id or "all"
        async with self.lock:
            self.clients.setdefault(key, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            for key, s in list(self.clients.items()):
                if websocket in s:
                    s.remove(websocket)
                    if not s:
                        del self.clients[key]

    async def send(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict, session_id: str | None = None):
        key = session_id or "all"
        async with self.lock:
            sockets = list(self.clients.get(key, set()))
        for ws in sockets:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                # best-effort
                pass


broadcaster = Broadcaster()
