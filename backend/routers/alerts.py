import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from db.database import get_conn
from models.alert import (
    AlertConfigBase, AlertConfigUpdate, AlertConfigResponse,
    Alert, AlertStats
)
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config", response_model=AlertConfigResponse)
async def get_alert_config(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Get alert configuration for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow(
        "SELECT * FROM alert_config WHERE tenant_id = $1",
        tenant_id
    )
    
    if not row:
        # Create default config
        row = await conn.fetchrow("""
            INSERT INTO alert_config (tenant_id) VALUES ($1)
            RETURNING *
        """, tenant_id)
    
    return AlertConfigResponse(**dict(row))


@router.put("/config", response_model=AlertConfigResponse)
async def update_alert_config(
    config: AlertConfigUpdate,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Update alert configuration for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    # Build update query
    updates = []
    params = []
    idx = 1
    
    for field, value in config.model_dump(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = ${idx}")
            params.append(value)
            idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    updates.append("updated_at = NOW()")
    params.append(tenant_id)
    
    query = f"""
        UPDATE alert_config 
        SET {', '.join(updates)} 
        WHERE tenant_id = ${idx} 
        RETURNING *
    """
    
    row = await conn.fetchrow(query, *params)
    
    if not row:
        # Create config if not exists
        row = await conn.fetchrow("""
            INSERT INTO alert_config (tenant_id) VALUES ($1)
            RETURNING *
        """, tenant_id)
    
    return AlertConfigResponse(**dict(row))


@router.get("", response_model=list[Alert])
async def list_alerts(
    limit: int = 50,
    unread_only: bool = False,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """List alerts for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    query = "SELECT * FROM alerts WHERE tenant_id = $1"
    params = [tenant_id]
    
    if unread_only:
        query += " AND is_read = FALSE"
    
    query += " ORDER BY created_at DESC LIMIT $2"
    params.append(limit)
    
    rows = await conn.fetch(query, *params)
    return [Alert(**dict(r)) for r in rows]


@router.get("/stats", response_model=AlertStats)
async def get_alert_stats(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Get alert statistics for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_alerts,
            COUNT(*) FILTER (WHERE is_read = FALSE) as unread_alerts,
            COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
            COUNT(*) FILTER (WHERE severity = 'warning') as warning_alerts,
            MAX(created_at) as last_alert_at
        FROM alerts 
        WHERE tenant_id = $1
    """, tenant_id)
    
    return AlertStats(
        total_alerts=row["total_alerts"] or 0,
        unread_alerts=row["unread_alerts"] or 0,
        critical_alerts=row["critical_alerts"] or 0,
        warning_alerts=row["warning_alerts"] or 0,
        last_alert_at=row["last_alert_at"]
    )


@router.put("/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Mark an alert as read."""
    tenant_id = current_user["tenant_id"]
    
    result = await conn.execute(
        "UPDATE alerts SET is_read = TRUE WHERE id = $1 AND tenant_id = $2",
        alert_id, tenant_id
    )
    
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    return {"status": "ok"}


@router.put("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Mark an alert as resolved."""
    tenant_id = current_user["tenant_id"]
    
    result = await conn.execute(
        "UPDATE alerts SET is_resolved = TRUE, resolved_at = NOW() WHERE id = $1 AND tenant_id = $2",
        alert_id, tenant_id
    )
    
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    return {"status": "ok"}


@router.post("/check")
async def check_alerts(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Manually trigger alert check for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    # Get alert config
    config = await conn.fetchrow(
        "SELECT * FROM alert_config WHERE tenant_id = $1",
        tenant_id
    )
    
    if not config or not config["is_enabled"]:
        return {"status": "disabled", "alerts_created": 0}
    
    alerts_created = 0
    
    # Check bounce rate
    bounce_rate = await _check_bounce_rate(conn, tenant_id, config)
    if bounce_rate is not None:
        alerts_created += 1
    
    # Check complaint rate
    complaint_rate = await _check_complaint_rate(conn, tenant_id, config)
    if complaint_rate is not None:
        alerts_created += 1
    
    # Check sudden bounces
    sudden_bounce = await _check_sudden_bounce(conn, tenant_id, config)
    if sudden_bounce is not None:
        alerts_created += 1
    
    # Check blocked count
    blocked_count = await _check_blocked_count(conn, tenant_id, config)
    if blocked_count is not None:
        alerts_created += 1
    
    return {"status": "checked", "alerts_created": alerts_created}


async def _check_bounce_rate(conn, tenant_id: int, config) -> bool:
    """Check if bounce rate exceeds threshold."""
    window_hours = config["bounce_rate_window_hours"]
    threshold = config["bounce_rate_threshold"]
    
    row = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as total,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as bounces
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 hour' * $2
    """, tenant_id, window_hours)
    
    total = row["total"] or 0
    bounces = row["bounces"] or 0
    
    if total == 0:
        return False
    
    rate = (bounces / total) * 100
    
    if rate >= threshold:
        await _create_alert(
            conn, tenant_id,
            alert_type="bounce_rate",
            severity="critical" if rate >= threshold * 1.5 else "warning",
            title="Bounce rate elevado",
            message=f"El bounce rate es {rate:.1f}% (umbral: {threshold}%) en las últimas {window_hours}h",
            current_value=rate,
            threshold_value=threshold
        )
        return True
    
    return False


async def _check_complaint_rate(conn, tenant_id: int, config) -> bool:
    """Check if complaint rate exceeds threshold."""
    window_hours = config["complaint_rate_window_hours"]
    threshold = config["complaint_rate_threshold"]
    
    row = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as total,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as complaints
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 hour' * $2
    """, tenant_id, window_hours)
    
    total = row["total"] or 0
    complaints = row["complaints"] or 0
    
    if total == 0:
        return False
    
    rate = (complaints / total) * 100
    
    if rate >= threshold:
        await _create_alert(
            conn, tenant_id,
            alert_type="complaint_rate",
            severity="critical",
            title="Complaint rate elevado",
            message=f"El complaint rate es {rate:.2f}% (umbral: {threshold}%) en las últimas {window_hours}h",
            current_value=rate,
            threshold_value=threshold
        )
        return True
    
    return False


async def _check_sudden_bounce(conn, tenant_id: int, config) -> bool:
    """Check for sudden spike in bounces."""
    window_minutes = config["sudden_bounce_window_minutes"]
    threshold = config["sudden_bounce_count"]
    
    row = await conn.fetchrow("""
        SELECT COUNT(DISTINCT ee.email_send_id) as bounces
        FROM email_events ee
        WHERE ee.tenant_id = $1 
        AND LOWER(ee.event_type) = 'bounce'
        AND ee.created_at >= NOW() - INTERVAL '1 minute' * $2
    """, tenant_id, window_minutes)
    
    bounces = row["bounces"] or 0
    
    if bounces >= threshold:
        await _create_alert(
            conn, tenant_id,
            alert_type="sudden_bounce",
            severity="critical",
            title="Pico de bounces detectado",
            message=f"{bounces} bounces en los últimos {window_minutes} minutos (umbral: {threshold})",
            current_value=bounces,
            threshold_value=threshold
        )
        return True
    
    return False


async def _check_blocked_count(conn, tenant_id: int, config) -> bool:
    """Check for new blocked addresses."""
    window_hours = config["blocked_window_hours"]
    threshold = config["blocked_count_threshold"]
    
    row = await conn.fetchrow("""
        SELECT COUNT(*) as blocked
        FROM email_block
        WHERE tenant_id = $1 
        AND created_at >= NOW() - INTERVAL '1 hour' * $2
    """, tenant_id, window_hours)
    
    blocked = row["blocked"] or 0
    
    if blocked >= threshold:
        await _create_alert(
            conn, tenant_id,
            alert_type="blocked_count",
            severity="warning",
            title="Muchas direcciones bloqueadas",
            message=f"{blocked} direcciones bloqueadas en las últimas {window_hours}h (umbral: {threshold})",
            current_value=blocked,
            threshold_value=threshold
        )
        return True
    
    return False


async def _create_alert(
    conn, tenant_id: int,
    alert_type: str, severity: str, title: str, message: str,
    current_value: float, threshold_value: float
):
    """Create a new alert if not already exists recently."""
    # Check if similar alert exists in last hour
    existing = await conn.fetchval("""
        SELECT id FROM alerts 
        WHERE tenant_id = $1 
        AND alert_type = $2 
        AND created_at >= NOW() - INTERVAL '1 hour'
    """, tenant_id, alert_type)
    
    if existing:
        return  # Don't create duplicate
    
    await conn.execute("""
        INSERT INTO alerts (tenant_id, alert_type, severity, title, message, current_value, threshold_value)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    """, tenant_id, alert_type, severity, title, message, current_value, threshold_value)
    
    logger.warning("Alert created for tenant %d: %s - %s", tenant_id, alert_type, title)
