"""
MailPulse — SES Dashboard
routers/outbound_webhooks.py

CRUD for outbound webhook configuration.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db.database import get_conn
from routers.auth import get_current_user
from services.outbound_webhooks import VALID_EVENTS

logger = logging.getLogger(__name__)
router = APIRouter()


class WebhookConfigCreate(BaseModel):
    url: str
    secret: Optional[str] = None
    events: list[str] = ["alert.created"]


class WebhookConfigUpdate(BaseModel):
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[list[str]] = None
    is_enabled: Optional[bool] = None


@router.get("")
async def list_webhooks(
    current_user: dict = Depends(get_current_user),
):
    """List outbound webhooks for current tenant."""
    tenant_id = current_user["tenant_id"]
    async for conn in get_conn():
        rows = await conn.fetch(
            """SELECT id, url, events, is_enabled, last_triggered_at, 
                      last_status_code, fail_count, created_at
               FROM webhook_config 
               WHERE tenant_id = $1 
               ORDER BY created_at DESC""",
            tenant_id,
        )
    return {"webhooks": [dict(r) for r in rows]}


@router.get("/events")
async def list_event_types():
    """List available webhook event types."""
    return {"events": VALID_EVENTS}


@router.post("")
async def create_webhook(
    config: WebhookConfigCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new outbound webhook."""
    tenant_id = current_user["tenant_id"]

    # Validate events
    invalid = [e for e in config.events if e not in VALID_EVENTS and e != "*"]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}")

    async for conn in get_conn():
        # Check limit (max 5 per tenant)
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM webhook_config WHERE tenant_id = $1",
            tenant_id,
        )
        if count >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 webhooks per tenant")

        row = await conn.fetchrow(
            """INSERT INTO webhook_config (tenant_id, url, secret, events)
               VALUES ($1, $2, $3, $4)
               RETURNING id, url, events, is_enabled, created_at""",
            tenant_id, config.url, config.secret, config.events,
        )

    return dict(row)


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: int,
    config: WebhookConfigUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an outbound webhook."""
    tenant_id = current_user["tenant_id"]

    updates = []
    params = []
    idx = 1

    if config.url is not None:
        updates.append(f"url = ${idx}")
        params.append(config.url)
        idx += 1
    if config.secret is not None:
        updates.append(f"secret = ${idx}")
        params.append(config.secret)
        idx += 1
    if config.events is not None:
        invalid = [e for e in config.events if e not in VALID_EVENTS and e != "*"]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}")
        updates.append(f"events = ${idx}")
        params.append(config.events)
        idx += 1
    if config.is_enabled is not None:
        updates.append(f"is_enabled = ${idx}")
        params.append(config.is_enabled)
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    params.extend([webhook_id, tenant_id])

    async for conn in get_conn():
        result = await conn.execute(
            f"""UPDATE webhook_config 
                SET {', '.join(updates)}
                WHERE id = ${idx} AND tenant_id = ${idx + 1}""",
            *params,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Webhook not found")

    return {"status": "ok"}


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete an outbound webhook."""
    tenant_id = current_user["tenant_id"]
    async for conn in get_conn():
        result = await conn.execute(
            "DELETE FROM webhook_config WHERE id = $1 AND tenant_id = $2",
            webhook_id, tenant_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "ok"}


@router.get("/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get logs for a specific webhook."""
    tenant_id = current_user["tenant_id"]
    async for conn in get_conn():
        rows = await conn.fetch(
            """SELECT event_type, url, status_code, response_time_ms, error_message, created_at
               FROM webhook_logs 
               WHERE webhook_config_id = $1 AND tenant_id = $2
               ORDER BY created_at DESC 
               LIMIT $3""",
            webhook_id, tenant_id, limit,
        )
    return {"logs": [dict(r) for r in rows]}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Send a test ping to a webhook."""
    tenant_id = current_user["tenant_id"]
    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT id, url, secret FROM webhook_config WHERE id = $1 AND tenant_id = $2",
            webhook_id, tenant_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")

    from services.outbound_webhooks import _send_webhook
    await _send_webhook(
        webhook_id=row["id"],
        tenant_id=tenant_id,
        url=row["url"],
        secret=row["secret"],
        event_type="test.ping",
        payload={"message": "MailPulse webhook test ping"},
    )

    return {"status": "sent"}
