import logging
from fastapi import APIRouter, Depends, HTTPException
from db.database import get_conn
from models.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantStats
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[TenantResponse])
async def list_tenants(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """List all tenants (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    rows = await conn.fetch("SELECT * FROM tenants ORDER BY created_at DESC")
    return [TenantResponse(**dict(r)) for r in rows]


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Get current user's tenant."""
    tenant_id = current_user["tenant_id"]
    row = await conn.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return TenantResponse(**dict(row))


@router.get("/stats", response_model=TenantStats)
async def get_tenant_stats(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Get stats for current tenant."""
    tenant_id = current_user["tenant_id"]
    row = await conn.fetchrow("""
        SELECT
            (SELECT COUNT(*) FROM email_send WHERE tenant_id = $1) AS total_emails,
            (SELECT COUNT(*) FROM email_events WHERE tenant_id = $1) AS total_events,
            (SELECT COUNT(*) FROM email_block WHERE tenant_id = $1) AS total_blocked
    """, tenant_id)

    tenant = await conn.fetchrow("SELECT name FROM tenants WHERE id = $1", tenant_id)
    return TenantStats(
        tenant_id=tenant_id,
        tenant_name=tenant["name"] if tenant else "Unknown",
        total_emails=row["total_emails"],
        total_events=row["total_events"],
        total_blocked=row["total_blocked"]
    )


@router.post("", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Create a new tenant (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    # Check slug uniqueness
    existing = await conn.fetchrow("SELECT id FROM tenants WHERE slug = $1", tenant_data.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Slug ya existe")

    row = await conn.fetchrow("""
        INSERT INTO tenants (name, slug, plan, aws_region, aws_access_key_enc, aws_secret_key_enc)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
    """, tenant_data.name, tenant_data.slug, tenant_data.plan, tenant_data.aws_region,
         tenant_data.aws_access_key, tenant_data.aws_secret_key)

    return TenantResponse(**dict(row))


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: int, tenant_data: TenantUpdate, conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Update a tenant (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    # Build update query dynamically
    updates = []
    params = []
    idx = 1

    for field, value in tenant_data.model_dump(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = ${idx}")
            params.append(value)
            idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    updates.append(f"updated_at = NOW()")
    params.append(tenant_id)

    query = f"UPDATE tenants SET {', '.join(updates)} WHERE id = ${idx} RETURNING *"
    row = await conn.fetchrow(query, *params)

    if not row:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return TenantResponse(**dict(row))
