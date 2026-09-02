import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any
from db.database import get_conn
from services.sns_parser import parse_sns_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting for webhooks (AWS SNS)
_webhook_requests: dict[str, list[float]] = {}
WEBHOOK_RATE_LIMIT = 100  # per minute
WEBHOOK_RATE_WINDOW = 60

# In-memory webhook log (for development; use DB in production)
webhook_logs: list[dict] = []


def _check_webhook_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip not in _webhook_requests:
        _webhook_requests[ip] = []
    
    # Clean old entries
    _webhook_requests[ip] = [t for t in _webhook_requests[ip] if now - t < WEBHOOK_RATE_WINDOW]
    
    if len(_webhook_requests[ip]) >= WEBHOOK_RATE_LIMIT:
        logger.warning("Webhook rate limit exceeded for IP: %s", ip)
        return False
    
    _webhook_requests[ip].append(now)
    return True


@router.post("/ses")
async def receive_ses_webhook(request: Request):
    """Receive SES event notifications via SNS."""
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limiting
    if not _check_webhook_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Log webhook
    webhook_logs.append({
        "ip": client_ip,
        "type": body.get("Type", "unknown"),
        "message_id": body.get("MessageId"),
        "timestamp": time.time(),
    })
    
    # Handle subscription confirmation
    if body.get("Type") == "SubscriptionConfirmation":
        logger.info("SNS Subscription Confirmation: %s", body.get("SubscribeURL"))
        return {
            "status": "subscription_confirmation",
            "subscribe_url": body.get("SubscribeURL"),
        }
    
    # Handle notification
    if body.get("Type") == "Notification":
        # TODO: Get tenant_id from AWS config or topic ARN
        # For now, use default tenant
        tenant_id = 1
        
        event = parse_sns_message(body, tenant_id)
        
        if event:
            logger.info(
                "SES event received: type=%s message_id=%s to=%s",
                event.event_type, event.message_id, event.email_to
            )
            
            # Store event in database
            async for conn in get_conn():
                # Find the email_send record
                email_send_id = await conn.fetchval(
                    "SELECT id FROM email_send WHERE message_id = $1 AND tenant_id = $2",
                    event.message_id, event.tenant_id
                )
                
                if email_send_id:
                    import json
                    await conn.execute("""
                        INSERT INTO email_events (email_send_id, event_type, event_data, tenant_id)
                        VALUES ($1, $2, $3::jsonb, $4)
                    """, email_send_id, event.event_type, json.dumps(event.event_data), event.tenant_id)
                    
                    logger.info("Event stored: email_send_id=%d type=%s", email_send_id, event.event_type)
                else:
                    logger.warning("Email not found for message_id: %s", event.message_id)
            
            return {"status": "processed", "event_type": event.event_type}
        
        return {"status": "ignored", "reason": "could_not_parse"}
    
    return {"status": "unknown_type", "type": body.get("Type")}


@router.get("/ses")
async def confirm_sns_subscription(request: Request):
    """Handle SNS subscription confirmation via GET."""
    # AWS sends a GET request to confirm subscription
    return {"status": "confirmed"}


@router.get("/logs")
async def get_webhook_logs(limit: int = 50):
    """Get recent webhook logs (for debugging)."""
    return {"logs": webhook_logs[-limit:]}
