from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4

from ..database import get_pool

router = APIRouter()


class CreateSessionRequest(BaseModel):
    team_id: UUID | None = None
    project_id: str = "default"
    token_budget: int = 10000
    task_total: int | None = None


@router.post("/sessions")
async def create_session(req: CreateSessionRequest, pool=Depends(get_pool)):
    sid = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sessions(session_id, team_id, project_id, token_budget, task_total) VALUES($1,$2,$3,$4,$5)",
            str(sid),
            str(req.team_id) if req.team_id else None,
            req.project_id,
            req.token_budget,
            req.task_total,
        )
    return {"session_id": str(sid)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: UUID, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE session_id = $1", str(session_id))
        if not row:
            raise HTTPException(status_code=404, detail="session not found")
        return dict(row)


    class PatchBudgetRequest(BaseModel):
        token_budget: int | None = None
        tokens_spent: int | None = None


    @router.patch("/sessions/{session_id}/budget")
    async def patch_session_budget(session_id: UUID, payload: PatchBudgetRequest, pool=Depends(get_pool)):
        updates = []
        params = []
        idx = 1
        if payload.token_budget is not None:
            updates.append(f"token_budget = ${idx}")
            params.append(payload.token_budget)
            idx += 1
        if payload.tokens_spent is not None:
            updates.append(f"tokens_spent = ${idx}")
            params.append(payload.tokens_spent)
            idx += 1
        if not updates:
            return {"session_id": str(session_id)}
        q = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ${idx}"
        params.append(str(session_id))
        async with pool.acquire() as conn:
            await conn.execute(q, *params)
        return {"session_id": str(session_id)}
