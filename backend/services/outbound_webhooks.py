"""
MailPulse — SES Dashboard
services/outbound_webhooks.py

Outbound webhook system: register URLs, trigger on events.
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Event types that can trigger webhooks
VALID_EVENTS = [
    "alert.created",
    "alert.resolved",
    "report.generated",
    "email.bounce",
    "email.complaint",
    "subscription.changed",
]


async def trigger_webhooks(
    tenant_id: int,
    event_type: str,
    payload: dict,
    conn=None,
):
    """Trigger all outbound webhooks for a tenant matching the event type."""
    if conn:
        rows = await conn.fetch(
            """SELECT id, url, secret, events 
               FROM webhook_config 
               WHERE tenant_id = $1 AND is_enabled = TRUE""",
            tenant_id,
        )
    else:
        from db.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn2:
            rows = await conn2.fetch(
                """SELECT id, url, secret, events 
                   FROM webhook_config 
                   WHERE tenant_id = $1 AND is_enabled = TRUE""",
                tenant_id,
            )

    for row in rows:
        events = row["events"] or []
        if event_type not in events and "*" not in events:
            continue

        await _send_webhook(
            webhook_id=row["id"],
            tenant_id=tenant_id,
            url=row["url"],
            secret=row["secret"],
            event_type=event_type,
            payload=payload,
        )


async def _send_webhook(
    webhook_id: int,
    tenant_id: int,
    url: str,
    secret: Optional[str],
    event_type: str,
    payload: dict,
):
    """Send a single outbound webhook."""
    body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "data": payload,
    }
    body_bytes = json.dumps(body, default=str).encode()

    headers = {
        "Content-Type": "application/json",
        "X-MailPulse-Event": event_type,
        "X-MailPulse-Delivery": str(int(time.time())),
    }

    # HMAC signature if secret is set
    if secret:
        sig = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        headers["X-MailPulse-Signature"] = f"sha256={sig}"

    start = time.time()
    status_code = None
    error_msg = None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=body_bytes, headers=headers)
            status_code = resp.status_code
    except Exception as e:
        error_msg = str(e)
        logger.warning("Webhook failed: %s -> %s", url, error_msg)

    elapsed_ms = int((time.time() - start) * 1000)

    # Log result
    from db.database import get_pool
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO webhook_logs 
                   (tenant_id, webhook_config_id, event_type, url, status_code, response_time_ms, error_message)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                tenant_id, webhook_id, event_type, url, status_code, elapsed_ms, error_msg,
            )
            # Update config stats
            await conn.execute(
                """UPDATE webhook_config 
                   SET last_triggered_at = NOW(), last_status_code = $2,
                       fail_count = CASE WHEN $2 >= 400 OR $2 IS NULL THEN fail_count + 1 ELSE 0 END
                   WHERE id = $1""",
                webhook_id, status_code,
            )
    except Exception as e:
        logger.error("Failed to log webhook: %s", e)
