from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from ..database import get_pool

router = APIRouter()


class AlertOut(BaseModel):
    alert_id: UUID
    session_id: UUID
    breach_type: str
    payload: dict
    created_at: str
    acknowledged_at: str | None = None


@router.get("/alerts")
async def list_alerts(team_id: UUID | None = None, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        if team_id:
            rows = await conn.fetch("SELECT a.* FROM alerts a JOIN sessions s ON a.session_id = s.session_id WHERE s.team_id = $1 ORDER BY a.created_at DESC", str(team_id))
        else:
            rows = await conn.fetch("SELECT * FROM alerts ORDER BY created_at DESC")
        return [dict(r) for r in rows]


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge(alert_id: UUID, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        res = await conn.execute("UPDATE alerts SET acknowledged_at = now() WHERE alert_id = $1", str(alert_id))
        if res is None:
            raise HTTPException(status_code=404, detail="alert not found")
    return {"ok": True}
