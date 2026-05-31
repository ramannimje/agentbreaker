from fastapi import FastAPI

from .config import settings
from .database import init_db, close_db
from .routers import sessions, health, alerts, events, teams, traces
from .websocket import broadcaster
from fastapi import WebSocket


def create_app() -> FastAPI:
    app = FastAPI(title="AgentBreaker API")

    @app.on_event("startup")
    async def startup():
        await init_db()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()

    app.include_router(sessions.router)
    app.include_router(teams.router)
    app.include_router(traces.router)
    app.include_router(events.router)
    app.include_router(alerts.router)
    app.include_router(health.router)

    @app.websocket("/ws/sessions/{session_id}")
    async def ws_session(websocket: WebSocket, session_id: str):
        await broadcaster.connect(websocket, session_id=session_id)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            await broadcaster.disconnect(websocket)

    @app.websocket("/ws/sessions")
    async def ws_all(websocket: WebSocket):
        await broadcaster.connect(websocket, session_id=None)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            await broadcaster.disconnect(websocket)

    return app


app = create_app()
