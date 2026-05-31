from fastapi import APIRouter, Depends

from ..database import get_pool

router = APIRouter()


@router.get("/sessions/{session_id}/trace")
async def get_trace(session_id: str, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT call_id, tool_name, args_hash, tokens_used, timestamp FROM tool_call_log WHERE session_id = $1 ORDER BY timestamp DESC",
            session_id,
        )
        return [dict(r) for r in rows]
