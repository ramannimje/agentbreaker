from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4

from ..database import get_pool
from ..services import escalation
from ..websocket import broadcaster
from ..metrics import TOOL_CALLS

router = APIRouter()


class ToolCallEvent(BaseModel):
    session_id: UUID
    tool_name: str
    args_hash: str
    tokens_used: int
    breach_type: str | None = None


@router.post("/events/tool_call")
async def tool_call_event(event: ToolCallEvent, background: BackgroundTasks, pool=Depends(get_pool)):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tool_call_log(session_id, tool_name, args_hash, tokens_used) VALUES($1,$2,$3,$4)",
            str(event.session_id),
            event.tool_name,
            event.args_hash,
            event.tokens_used,
        )
        # update tokens_spent atomically
        try:
            await conn.execute(
                "UPDATE sessions SET tokens_spent = tokens_spent + $1 WHERE session_id = $2",
                event.tokens_used,
                str(event.session_id),
            )
        except Exception:
            raise HTTPException(status_code=500, detail="failed to update session")

    # broadcast to websocket listeners
    payload = {
        "event": "burn_update",
        "session_id": str(event.session_id),
        "tokens_spent": event.tokens_used,  # clients should fetch full state
        "token_budget": None,
        "spend_ratio": None,
        "burn_rate_per_minute": None,
        "estimated_ttl_seconds": None,
        "status": "active",
    }
    await broadcaster.broadcast(payload, session_id=str(event.session_id))

    # update metrics
    try:
        TOOL_CALLS.inc()
    except Exception:
        pass

    # if there's a breach_type, create an alert and escalate
    if event.breach_type:
        alert_id = uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO alerts(alert_id, session_id, breach_type, payload) VALUES($1,$2,$3,$4)",
                str(alert_id),
                str(event.session_id),
                event.breach_type,
                {"tokens_used": event.tokens_used, "tool_name": event.tool_name},
            )
            # fetch team row for escalation
            team_row = await conn.fetchrow("SELECT team_id, escalation_webhook FROM teams WHERE team_id = (SELECT team_id FROM sessions WHERE session_id = $1)", str(event.session_id))
        if team_row:
            background.add_task(escalation.escalate_if_configured, dict(team_row), {"session_id": str(event.session_id), "breach_type": event.breach_type})

    return {"ok": True}
