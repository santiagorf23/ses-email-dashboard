"""
MailPulse — SES Dashboard
middleware/plan_enforcement.py

Plan-based feature enforcement middleware.
Checks tenant plan limits before allowing certain operations.
"""
import logging
from functools import wraps
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Plan limits
PLAN_LIMITS = {
    "free": {
        "emails": 100,
        "domains": 1,
        "alerts": True,
        "reports": False,
        "ab_testing": False,
        "heatmap": False,
        "webhooks": False,
        "api_access": False,
        "pdf_export": False,
    },
    "starter": {
        "emails": 1000,
        "domains": 3,
        "alerts": True,
        "reports": True,
        "ab_testing": True,
        "heatmap": True,
        "webhooks": False,
        "api_access": False,
        "pdf_export": True,
    },
    "pro": {
        "emails": 10000,
        "domains": 999,
        "alerts": True,
        "reports": True,
        "ab_testing": True,
        "heatmap": True,
        "webhooks": True,
        "api_access": True,
        "pdf_export": True,
    },
}


def get_plan_limits(plan_name: str) -> dict:
    """Get limits for a plan."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])


def get_tenant_plan(conn, tenant_id: int) -> str:
    """Get the current plan for a tenant."""
    import asyncio
    if asyncio.iscoroutine(conn):
        raise ValueError("get_tenant_plan requires a connection, not a coroutine")

    row = conn.fetchrow(
        """SELECT plan_name FROM subscriptions 
           WHERE tenant_id = $1 AND status = 'active'
           ORDER BY created_at DESC LIMIT 1""",
        tenant_id,
    )
    if not row:
        return "free"
    return row["plan_name"] or "free"


async def get_tenant_plan_async(tenant_id: int) -> str:
    """Async version: get the current plan for a tenant."""
    from db.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT plan_name FROM subscriptions 
               WHERE tenant_id = $1 AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            tenant_id,
        )
    if not row:
        return "free"
    return row["plan_name"] or "free"


class PlanEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces plan limits on specific routes."""

    # Routes that require specific plan features
    FEATURE_ROUTES = {
        "/api/reports": "reports",
        "/api/reports/pdf": "pdf_export",
        "/api/reports/export": "reports",
        "/api/ab-tests": "ab_testing",
        "/api/heatmap": "heatmap",
        "/api/webhooks/outbound": "webhooks",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip auth and health endpoints
        skip_paths = ["/api/auth/login", "/api/health", "/api/auth/register"]
        if request.url.path in skip_paths:
            return await call_next(request)

        # Check if route requires a specific feature
        required_feature = None
        for prefix, feature in self.FEATURE_ROUTES.items():
            if request.url.path.startswith(prefix):
                required_feature = feature
                break

        if not required_feature:
            return await call_next(request)

        # Get tenant_id from request state (set by TenantMiddleware)
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # Check plan
        plan = await get_tenant_plan_async(tenant_id)
        limits = get_plan_limits(plan)

        if not limits.get(required_feature, False):
            return HTTPException(
                status_code=403,
                detail=f"Feature '{required_feature}' requires a paid plan. Current plan: {plan}",
            )

        return await call_next(request)


def require_plan_feature(feature: str):
    """Decorator to require a specific plan feature for an endpoint."""
    async def decorator(request: Request):
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return  # Let auth handle it

        plan = await get_tenant_plan_async(tenant_id)
        limits = get_plan_limits(plan)

        if not limits.get(feature, False):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' requires a paid plan. Current plan: {plan}",
            )

    return decorator
