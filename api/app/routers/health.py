from fastapi import APIRouter, Depends

from ..database import get_pool

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(pool=Depends(get_pool)):
    # quick db ping
    async with pool.acquire() as conn:
        await conn.fetchrow("SELECT 1")
    return {"ready": True}
