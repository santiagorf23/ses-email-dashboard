"""
Billing Router
Endpoints para gestión de suscripciones y pagos con LemonSqueezy.
"""

import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from db.database import get_conn
from routers.auth import get_current_user
from services.billing_service import (
    create_checkout_url,
    get_subscription,
    cancel_subscription,
    verify_webhook_signature,
    get_plan_limits,
    is_paid_plan,
    PRODUCTS
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str  # starter_monthly, starter_annual, pro_monthly, pro_annual


class SubscriptionResponse(BaseModel):
    plan_name: str
    status: str
    billing_cycle: str
    current_period_end: Optional[str]
    emails_limit: int
    domains_limit: int


# ─────────────────────────────────────────────────────────────
# GET /billing/plans - Listar planes disponibles
# ─────────────────────────────────────────────────────────────
@router.get("/plans")
async def list_plans():
    """Retorna los planes disponibles con sus precios."""
    return {
        "plans": [
            {
                "id": "starter_monthly",
                "name": "Starter",
                "price": 19,
                "interval": "monthly",
                "emails": 1000,
                "domains": 3,
                "features": [
                    "Real-time monitoring",
                    "Smart alerts (Email + Slack)",
                    "A/B testing",
                    "Engagement heatmap",
                    "PDF/CSV reports",
                    "Email support"
                ]
            },
            {
                "id": "starter_annual",
                "name": "Starter (Annual)",
                "price": 15,
                "interval": "yearly",
                "emails": 1000,
                "domains": 3,
                "features": [
                    "Same as Starter Monthly",
                    "Save 21% with annual billing"
                ]
            },
            {
                "id": "pro_monthly",
                "name": "Pro",
                "price": 49,
                "interval": "monthly",
                "emails": 10000,
                "domains": 999,
                "features": [
                    "Everything in Starter",
                    "Multi-tenant support",
                    "Full REST API",
                    "White-label reports",
                    "Bulk email verification",
                    "Priority support"
                ]
            },
            {
                "id": "pro_annual",
                "name": "Pro (Annual)",
                "price": 39,
                "interval": "yearly",
                "emails": 10000,
                "domains": 999,
                "features": [
                    "Same as Pro Monthly",
                    "Save 20% with annual billing"
                ]
            }
        ]
    }


# ─────────────────────────────────────────────────────────────
# POST /billing/checkout - Crear sesión de checkout
# ─────────────────────────────────────────────────────────────
@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Crea una URL de checkout de LemonSqueezy.
    El usuario será redirigido para completar el pago.
    """
    if request.plan not in PRODUCTS:
        raise HTTPException(status_code=400, detail="Plan no válido")
    
    try:
        checkout_url = await create_checkout_url(
            email=current_user["username"],
            plan=request.plan,
            tenant_id=current_user["tenant_id"]
        )
        
        return {"checkout_url": checkout_url}
    
    except Exception as e:
        logger.error(f"Error creating checkout: {e}")
        raise HTTPException(status_code=500, detail="Error al crear checkout")


# ─────────────────────────────────────────────────────────────
# GET /billing/subscription - Obtener suscripción actual
# ─────────────────────────────────────────────────────────────
@router.get("/subscription")
async def get_current_subscription(
    current_user: dict = Depends(get_current_user)
):
    """Retorna la suscripción actual del usuario."""
    async for conn in get_conn():
        row = await conn.fetchrow(
            """SELECT * FROM subscriptions 
               WHERE tenant_id = $1 
               ORDER BY created_at DESC LIMIT 1""",
            current_user["tenant_id"]
        )
    
    if not row:
        # Usuario sin suscripción = plan free
        limits = get_plan_limits("free")
        return SubscriptionResponse(
            plan_name="free",
            status="active",
            billing_cycle="monthly",
            current_period_end=None,
            emails_limit=limits["emails"],
            domains_limit=limits["domains"]
        )
    
    limits = get_plan_limits(row["plan_name"])
    return SubscriptionResponse(
        plan_name=row["plan_name"],
        status=row["status"],
        billing_cycle=row["billing_cycle"],
        current_period_end=str(row["current_period_end"]) if row["current_period_end"] else None,
        emails_limit=limits["emails"],
        domains_limit=limits["domains"]
    )


# ─────────────────────────────────────────────────────────────
# POST /billing/cancel - Cancelar suscripción
# ─────────────────────────────────────────────────────────────
@router.post("/cancel")
async def cancel_current_subscription(
    current_user: dict = Depends(get_current_user)
):
    """Cancela la suscripción actual del usuario."""
    async for conn in get_conn():
        row = await conn.fetchrow(
            """SELECT lemonqueezy_id FROM subscriptions 
               WHERE tenant_id = $1 AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            current_user["tenant_id"]
        )
    
    if not row or not row["lemonqueezy_id"]:
        raise HTTPException(status_code=404, detail="No hay suscripción activa")
    
    success = await cancel_subscription(row["lemonqueezy_id"])
    
    if success:
        # Actualizar en BD
        async for conn in get_conn():
            await conn.execute(
                """UPDATE subscriptions 
                   SET status = 'cancelled', updated_at = NOW()
                   WHERE lemonqueezy_id = $1""",
                row["lemonqueezy_id"]
            )
        
        return {"message": "Suscripción cancelada exitosamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al cancelar suscripción")


# ─────────────────────────────────────────────────────────────
# GET /billing/invoices - Obtener historial de facturas
# ─────────────────────────────────────────────────────────────
@router.get("/invoices")
async def list_invoices(
    current_user: dict = Depends(get_current_user)
):
    """Retorna el historial de facturas del usuario."""
    async for conn in get_conn():
        rows = await conn.fetch(
            """SELECT * FROM invoices 
               WHERE tenant_id = $1 
               ORDER BY created_at DESC
               LIMIT 12""",
            current_user["tenant_id"]
        )
    
    return {
        "invoices": [
            {
                "id": row["id"],
                "amount": float(row["amount"]),
                "currency": row["currency"],
                "status": row["status"],
                "invoice_url": row["invoice_url"],
                "created_at": str(row["created_at"])
            }
            for row in rows
        ]
    }


# ─────────────────────────────────────────────────────────────
# POST /webhooks/lemonsqueezy - Webhook de LemonSqueezy
# ─────────────────────────────────────────────────────────────
@router.post("/webhooks/lemonsqueezy")
async def lemonqueezy_webhook(request: Request):
    """
    Recibe eventos de LemonSqueezy.
    Procesa: subscription_created, subscription_updated, subscription_cancelled
    """
    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    
    # Verificar firma (opcional pero recomendado)
    # if not verify_webhook_signature(body, signature):
    #     return JSONResponse(status_code=401, content={"error": "Invalid signature"})
    
    try:
        import json
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    event_type = payload.get("meta", {}).get("event_name")
    data = payload.get("data", {})
    attributes = data.get("attributes", {})
    
    logger.info(f"LemonSqueezy webhook: {event_type}")
    
    if event_type == "subscription_created":
        await handle_subscription_created(attributes)
    elif event_type == "subscription_updated":
        await handle_subscription_updated(attributes)
    elif event_type == "subscription_cancelled":
        await handle_subscription_cancelled(attributes)
    elif event_type == "order_created":
        await handle_order_created(attributes)
    
    return JSONResponse(status_code=200, content={"status": "ok"})


async def handle_subscription_created(attributes: dict):
    """Maneja el evento subscription_created."""
    lemonqueezy_id = attributes.get("id")
    customer_email = attributes.get("customer_email")
    status = attributes.get("status")
    product_id = attributes.get("product_id")
    
    # Determinar plan basado en product_id
    plan_name = "free"
    for name, pid in PRODUCTS.items():
        if pid == product_id:
            plan_name = name.replace("_monthly", "").replace("_annual", "")
            break
    
    # Obtener tenant_id del custom data
    custom_data = attributes.get("custom_data", {})
    tenant_id = custom_data.get("tenant_id")
    
    if not tenant_id:
        # Buscar tenant por email
        async for conn in get_conn():
            row = await conn.fetchrow(
                "SELECT tenant_id FROM app_users WHERE email = $1",
                customer_email
            )
            if row:
                tenant_id = row["tenant_id"]
    
    if tenant_id:
        async for conn in get_conn():
            await conn.execute(
                """INSERT INTO subscriptions 
                   (tenant_id, lemonqueezy_id, plan_name, status, billing_cycle, created_at)
                   VALUES ($1, $2, $3, $4, $5, NOW())
                   ON CONFLICT (lemonqueezy_id) DO UPDATE
                   SET status = $4, updated_at = NOW()""",
                tenant_id, lemonqueezy_id, plan_name, status,
                "annual" if "_annual" in plan_name else "monthly"
            )
        
        logger.info(f"Subscription created: {lemonqueezy_id} for tenant {tenant_id}")


async def handle_subscription_updated(attributes: dict):
    """Maneja el evento subscription_updated."""
    lemonqueezy_id = attributes.get("id")
    status = attributes.get("status")
    
    async for conn in get_conn():
        await conn.execute(
            """UPDATE subscriptions 
               SET status = $2, updated_at = NOW()
               WHERE lemonqueezy_id = $1""",
            lemonqueezy_id, status
        )
    
    logger.info(f"Subscription updated: {lemonqueezy_id} -> {status}")


async def handle_subscription_cancelled(attributes: dict):
    """Maneja el evento subscription_cancelled."""
    lemonqueezy_id = attributes.get("id")
    
    async for conn in get_conn():
        await conn.execute(
            """UPDATE subscriptions 
               SET status = 'cancelled', updated_at = NOW()
               WHERE lemonqueezy_id = $1""",
            lemonqueezy_id
        )
    
    logger.info(f"Subscription cancelled: {lemonqueezy_id}")


async def handle_order_created(attributes: dict):
    """Maneja el evento order_created (facturas)."""
    order_id = attributes.get("id")
    total = attributes.get("total")
    status = attributes.get("status")
    invoice_url = attributes.get("urls", {}).get("invoice_url")
    
    # Obtener tenant_id
    customer_email = attributes.get("customer_email")
    
    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT tenant_id FROM app_users WHERE email = $1",
            customer_email
        )
    
    if row:
        async for conn in get_conn():
            await conn.execute(
                """INSERT INTO invoices 
                   (tenant_id, lemonqueezy_order_id, amount, status, invoice_url)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (lemonqueezy_order_id) DO NOTHING""",
                row["tenant_id"], order_id, total / 100, status, invoice_url
            )
        
        logger.info(f"Order created: {order_id} for tenant {row['tenant_id']}")
