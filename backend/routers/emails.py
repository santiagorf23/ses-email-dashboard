import json
import logging
from typing import Optional, Any
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, Request

from db.database import get_conn
from models.schemas import (
    PaginatedEmails, EmailDetail, EmailSummary,
    EmailEvent, StatsResponse, BlockedEmail
)
from routers.auth import get_current_user
from middleware.tenant import get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_json_field(value: Any) -> Any:
    """Parsea un campo JSON de forma segura."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _parse_events(rows: list) -> list[EmailEvent]:
    """Convierte filas de eventos en modelos EmailEvent."""
    events = []
    for row in rows:
        e = dict(row)
        e["event_data"] = _parse_json_field(e.get("event_data"))
        events.append(EmailEvent(**e))
    return events


@router.get("", response_model=PaginatedEmails)
async def list_emails(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    email_to: Optional[str] = None,
    subject: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Lista paginada de correos con filtros (filtrado por tenant)."""
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * per_page

    conditions: list[str] = ["es.tenant_id = $1"]
    params: list[Any] = [tenant_id]
    idx = 2

    if email_to:
        conditions.append(f"es.email_to ILIKE ${idx}")
        params.append(f"%{email_to}%")
        idx += 1

    if subject:
        conditions.append(f"es.subject ILIKE ${idx}")
        params.append(f"%{subject}%")
        idx += 1

    if date_from:
        conditions.append(f"es.created_at >= ${idx}")
        params.append(date_from)
        idx += 1

    if date_to:
        conditions.append(f"es.created_at < (${idx}::date + INTERVAL '1 day')")
        params.append(date_to)
        idx += 1

    if status:
        status_map = {
            "delivered": "delivery", "bounce": "bounce", "complaint": "complaint",
            "sent": "send", "open": "open", "click": "click",
        }
        event_type = status_map.get(status.lower())
        if event_type is None:
            raise HTTPException(status_code=400, detail=f"Status no válido: {status}")
        conditions.append(
            f"LOWER((SELECT event_type FROM email_events "
            f"WHERE email_send_id = es.id AND tenant_id = $1 "
            f"ORDER BY created_at DESC LIMIT 1)) = ${idx}"
        )
        params.append(event_type)
        idx += 1

    where = "WHERE " + " AND ".join(conditions)

    count_query = f"SELECT COUNT(*) FROM email_send es {where}"
    total = await conn.fetchval(count_query, *params)

    data_query = f"""
        SELECT
            es.id, es.message_id, es.email_to, es.email_from, es.subject,
            es.created_at, FALSE AS has_attachments,
            COALESCE(
                LOWER(
                    (SELECT event_type FROM email_events
                     WHERE email_send_id = es.id AND tenant_id = $1
                     ORDER BY created_at DESC LIMIT 1)
                ), 'send'
            ) AS status,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id AND ee.tenant_id = $1 AND LOWER(ee.event_type) = 'bounce'
            ) AS has_bounce,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id AND ee.tenant_id = $1 AND LOWER(ee.event_type) = 'complaint'
            ) AS has_complaint
        FROM email_send es
        {where}
        ORDER BY es.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    params.extend([per_page, offset])
    rows = await conn.fetch(data_query, *params)

    items = [EmailSummary(**dict(r)) for r in rows]
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedEmails(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Estadísticas del tenant actual."""
    tenant_id = current_user["tenant_id"]
    row = await conn.fetchrow("""
        SELECT
            (SELECT COUNT(*) FROM email_send WHERE tenant_id = $1) AS total_sent,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE tenant_id = $1 AND LOWER(event_type) = 'delivery') AS total_delivered,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE tenant_id = $1 AND LOWER(event_type) = 'bounce') AS total_bounce,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE tenant_id = $1 AND LOWER(event_type) = 'complaint') AS total_complaint,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE tenant_id = $1 AND LOWER(event_type) = 'open') AS total_open
    """, tenant_id)
    total = row["total_sent"] or 1
    return StatsResponse(
        total_sent=row["total_sent"], total_delivered=row["total_delivered"],
        total_bounce=row["total_bounce"], total_complaint=row["total_complaint"],
        total_open=row["total_open"],
        delivery_rate=round(row["total_delivered"] / total * 100, 2),
        bounce_rate=round(row["total_bounce"] / total * 100, 2),
    )


@router.get("/blocked", response_model=list[BlockedEmail])
async def list_blocked(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    rows = await conn.fetch("""
        SELECT id, email, reason, created_at
        FROM email_block WHERE tenant_id = $1
        ORDER BY created_at DESC LIMIT 200
    """, tenant_id)
    return [BlockedEmail(**dict(r)) for r in rows]


@router.get("/search", response_model=PaginatedEmails)
async def search_emails(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Búsqueda por destinatario O asunto (filtrado por tenant)."""
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * per_page
    term = f"%{q}%"

    count_query = "SELECT COUNT(*) FROM email_send es WHERE es.tenant_id = $1 AND (es.email_to ILIKE $2 OR es.subject ILIKE $2)"
    total = await conn.fetchval(count_query, tenant_id, term)

    data_query = """
        SELECT es.id, es.message_id, es.email_to, es.email_from,
               es.subject, es.created_at, FALSE AS has_attachments,
               COALESCE(
                   LOWER((SELECT event_type FROM email_events
                    WHERE email_send_id = es.id AND tenant_id = $1
                    ORDER BY created_at DESC LIMIT 1)), 'send'
               ) AS status,
               EXISTS (SELECT 1 FROM email_events ee WHERE ee.email_send_id = es.id AND ee.tenant_id = $1 AND LOWER(ee.event_type) = 'bounce') AS has_bounce,
               EXISTS (SELECT 1 FROM email_events ee WHERE ee.email_send_id = es.id AND ee.tenant_id = $1 AND LOWER(ee.event_type) = 'complaint') AS has_complaint
        FROM email_send es
        WHERE es.tenant_id = $1 AND (es.email_to ILIKE $2 OR es.subject ILIKE $2)
        ORDER BY es.created_at DESC
        LIMIT $3 OFFSET $4
    """
    rows = await conn.fetch(data_query, tenant_id, term, per_page, offset)
    items = [EmailSummary(**dict(r)) for r in rows]
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    return PaginatedEmails(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/{email_id}", response_model=EmailDetail)
async def get_email(
    email_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user["tenant_id"]
    row = await conn.fetchrow("""
        SELECT es.id, es.message_id, es.email_to, es.email_from,
               es.subject, es.content, es.mime_type, es.created_at,
               FALSE AS has_attachments, NULL AS attachments,
               COALESCE(
                   LOWER((SELECT event_type FROM email_events
                    WHERE email_send_id = es.id AND tenant_id = $2
                    ORDER BY created_at DESC LIMIT 1)), 'send'
               ) AS status
        FROM email_send es
        WHERE es.id = $1 AND es.tenant_id = $2
    """, email_id, tenant_id)

    if not row:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    event_rows = await conn.fetch("""
        SELECT id, email_send_id, event_type, event_data, created_at
        FROM email_events
        WHERE email_send_id = $1 AND tenant_id = $2
        ORDER BY created_at ASC
    """, email_id, tenant_id)

    events = _parse_events(event_rows)
    detail = dict(row)
    detail["attachments"] = _parse_json_field(detail.get("attachments"))
    detail["events"] = events
    return EmailDetail(**detail)


@router.get("/{email_id}/events", response_model=list[EmailEvent])
async def get_email_events(
    email_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user["tenant_id"]
    rows = await conn.fetch("""
        SELECT id, email_send_id, event_type, event_data, created_at
        FROM email_events
        WHERE email_send_id = $1 AND tenant_id = $2
        ORDER BY created_at ASC
    """, email_id, tenant_id)
    return _parse_events(rows)
