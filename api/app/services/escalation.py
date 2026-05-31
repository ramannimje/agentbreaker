"""Escalation webhook service: post alerts to team webhook with retries."""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def post_webhook(url: str, payload: dict, timeout: int = 10) -> None:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


async def escalate_if_configured(team_row: dict, alert_payload: dict) -> None:
    webhook = team_row.get("escalation_webhook")
    if not webhook:
        logger.info("No escalation webhook configured for team %s", team_row.get("team_id"))
        return
    # Build Slack-compatible payload
    payload = {
        "text": f"🚨 AgentBreaker alert: {alert_payload.get('breach_type')}",
        "attachments": [
            {"title": f"Session {alert_payload.get('session_id')}", "text": json.dumps(alert_payload, indent=2)}
        ],
    }
    try:
        await post_webhook(webhook, payload)
    except Exception as e:
        logger.exception("Failed to post escalation webhook: %s", e)
