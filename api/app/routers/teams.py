from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID, uuid4

from ..database import get_pool

router = APIRouter()


class TeamIn(BaseModel):
    name: str
    default_budget: int | None = 100000
    velocity_multiplier: float | None = 2.0
    escalation_webhook: str | None = None


@router.post("/teams")
async def create_team(payload: TeamIn, pool=Depends(get_pool)):
    tid = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO teams(team_id, name, default_budget, velocity_multiplier, escalation_webhook) VALUES($1,$2,$3,$4,$5)",
            str(tid),
            payload.name,
            payload.default_budget,
            payload.velocity_multiplier,
            payload.escalation_webhook,
        )
    return {"team_id": str(tid)}


@router.get("/teams/{team_id}")
async def get_team(team_id: UUID, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM teams WHERE team_id = $1", str(team_id))
        if not row:
            raise HTTPException(status_code=404, detail="team not found")
        return dict(row)


@router.get("/teams")
async def list_teams(pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM teams ORDER BY name")
        return [dict(r) for r in rows]


@router.patch("/teams/{team_id}")
async def update_team(team_id: UUID, payload: TeamIn, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE teams SET name=$1, default_budget=$2, velocity_multiplier=$3, escalation_webhook=$4 WHERE team_id=$5",
            payload.name,
            payload.default_budget,
            payload.velocity_multiplier,
            payload.escalation_webhook,
            str(team_id),
        )
    return {"team_id": str(team_id)}


@router.delete("/teams/{team_id}")
async def delete_team(team_id: UUID, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM teams WHERE team_id = $1", str(team_id))
    return {"team_id": str(team_id)}
