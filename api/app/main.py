from fastapi import FastAPI

from .config import settings
from .database import init_db, close_db
from .routers import sessions, health


def create_app() -> FastAPI:
    app = FastAPI(title="AgentBreaker API")

    @app.on_event("startup")
    async def startup():
        await init_db()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()

    app.include_router(sessions.router)
    app.include_router(health.router)

    return app


app = create_app()
