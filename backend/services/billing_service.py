"""
LemonSqueezy Billing Service
Maneja la integración con LemonSqueezy para pagos y suscripciones.
"""

import os
import hmac
import hashlib
import httpx
from typing import Optional

# Configuración de LemonSqueezy
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
LEMONSQUEEZY_API_URL = "https://api.lemonsqueezy.com/v1"

# Product IDs (configurar después de crear productos)
PRODUCTS = {
    "starter_monthly": os.getenv("LS_PRODUCT_STARTER_MONTHLY", ""),
    "starter_annual": os.getenv("LS_PRODUCT_STARTER_ANNUAL", ""),
    "pro_monthly": os.getenv("LS_PRODUCT_PRO_MONTHLY", ""),
    "pro_annual": os.getenv("LS_PRODUCT_PRO_ANNUAL", ""),
}

# Plan limits
PLAN_LIMITS = {
    "free": {"emails": 100, "domains": 1},
    "starter": {"emails": 1000, "domains": 3},
    "starter_annual": {"emails": 1000, "domains": 3},
    "pro": {"emails": 10000, "domains": 999},
    "pro_annual": {"emails": 10000, "domains": 999},
}


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verifica la firma del webhook de LemonSqueezy."""
    if not LEMONSQUEEZY_WEBHOOK_SECRET:
        return False
    
    expected = hmac.new(
        LEMONSQUEEZY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


async def create_checkout_url(
    email: str,
    plan: str,
    tenant_id: int,
    custom_data: Optional[dict] = None
) -> str:
    """
    Crea una URL de checkout de LemonSqueezy.
    
    Args:
        email: Email del usuario
        plan: Nombre del plan (starter_monthly, pro_annual, etc.)
        tenant_id: ID del tenant
        custom_data: Datos personalizados para el webhook
    
    Returns:
        URL de checkout
    """
    product_id = PRODUCTS.get(plan)
    if not product_id:
        raise ValueError(f"Plan no válido: {plan}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LEMONSQUEEZY_API_URL}/checkouts",
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.v1+json",
                "Content-Type": "application/json",
            },
            json={
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "checkout_data": {
                            "email": email,
                            "custom": {
                                "tenant_id": str(tenant_id),
                                **(custom_data or {})
                            }
                        },
                        "product_options": {
                            "redirect_url": f"https://app.getmailpulse.net/billing/success",
                        }
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": LEMONSQUEEZY_STORE_ID
                            }
                        },
                        "variant": {
                            "data": {
                                "type": "variants",
                                "id": product_id
                            }
                        }
                    }
                }
            }
        )
        
        if response.status_code == 201:
            return response.json()["data"]["attributes"]["url"]
        else:
            raise Exception(f"Error creating checkout: {response.text}")


async def get_subscription(lemonqueezy_id: str) -> dict:
    """Obtiene detalles de una suscripción de LemonSqueezy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LEMONSQUEEZY_API_URL}/subscriptions/{lemonqueezy_id}",
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.v1+json",
            }
        )
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            return None


async def cancel_subscription(lemonqueezy_id: str) -> bool:
    """Cancela una suscripción en LemonSqueezy."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{LEMONSQUEEZY_API_URL}/subscriptions/{lemonqueezy_id}",
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.v1+json",
            }
        )
        
        return response.status_code == 200


def get_plan_limits(plan_name: str) -> dict:
    """Retorna los límites del plan."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])


def is_paid_plan(plan_name: str) -> bool:
    """Verifica si el plan es de pago."""
    return plan_name in ["starter", "starter_annual", "pro", "pro_annual"]
