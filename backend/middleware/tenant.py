import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
import os

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/api/health", "/api/auth/login", "/docs", "/openapi.json"]
        if request.url.path in public_paths or request.url.path.startswith("/docs"):
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                # Set tenant_id in request state for downstream use
                request.state.tenant_id = tenant_id
        except JWTError:
            pass  # Let auth middleware handle invalid tokens

        return await call_next(request)


def get_tenant_id(request: Request) -> int:
    """Extract tenant_id from request state."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not identified")
    return tenant_id
