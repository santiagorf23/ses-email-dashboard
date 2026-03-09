from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import date
import json

from db.database import get_conn
from models.schemas import (
    PaginatedEmails, EmailDetail, EmailSummary,
    EmailEvent, StatsResponse, BlockedEmail
)
from routers.auth import get_current_user

router = APIRouter()


@router.get("", response_model=PaginatedEmails)
async def list_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    email_to: Optional[str] = None,
    subject: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    """Lista paginada de correos con filtros."""
    offset = (page - 1) * per_page

    conditions = []
    params = []
    idx = 1

    # Búsqueda por destinatario
    if email_to:
        conditions.append(f"es.email_to ILIKE ${idx}")
        params.append(f"%{email_to}%")
        idx += 1

    # Búsqueda por asunto
    if subject:
        conditions.append(f"es.subject ILIKE ${idx}")
        params.append(f"%{subject}%")
        idx += 1

    # Filtro por fecha inicio
    if date_from:
        conditions.append(f"es.created_at >= ${idx}")
        params.append(date_from)
        idx += 1

    # Filtro por fecha fin
    if date_to:
        conditions.append(f"es.created_at < (${idx}::date + INTERVAL '1 day')")
        params.append(date_to)
        idx += 1

    # Filtro por status — se deriva del último evento (case-insensitive)
    if status:
        status_map = {
            "delivered": "delivery",
            "bounce":    "bounce",
            "complaint": "complaint",
            "sent":      "send",
            "open":      "open",
            "click":     "click",
        }
        event_type = status_map.get(status.lower(), status.lower())
        # Se agrega como condición normal dentro del WHERE
        conditions.append(
            f"LOWER((SELECT event_type FROM email_events "
            f"WHERE email_send_id = es.id "
            f"ORDER BY created_at DESC LIMIT 1)) = '{event_type}'"
        )

    # Construir cláusula WHERE completa
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Contar total para paginación
    count_query = f"SELECT COUNT(*) FROM email_send es {where}"
    total = await conn.fetchval(count_query, *params)

    # Query principal
    data_query = f"""
        SELECT
            es.id,
            es.message_id,
            es.email_to,
            es.email_from,
            es.subject,
            es.created_at,
            es.has_attachments,
            COALESCE(
                LOWER(
                    (SELECT event_type FROM email_events
                     WHERE email_send_id = es.id
                     ORDER BY created_at DESC LIMIT 1)
                ),
                'send'
            ) AS status,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id
                AND LOWER(ee.event_type) = 'bounce'
            ) AS has_bounce,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id
                AND LOWER(ee.event_type) = 'complaint'
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

    return PaginatedEmails(
        items=items, total=total,
        page=page, per_page=per_page, pages=pages
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    """Estadísticas globales derivadas de los eventos."""
    row = await conn.fetchrow("""
        SELECT
            (SELECT COUNT(*) FROM email_send) AS total_sent,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE LOWER(event_type) = 'delivery')  AS total_delivered,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE LOWER(event_type) = 'bounce')    AS total_bounce,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE LOWER(event_type) = 'complaint') AS total_complaint,
            (SELECT COUNT(DISTINCT email_send_id) FROM email_events
             WHERE LOWER(event_type) = 'open')      AS total_open
    """)
    total = row["total_sent"] or 1
    return StatsResponse(
        total_sent=row["total_sent"],
        total_delivered=row["total_delivered"],
        total_bounce=row["total_bounce"],
        total_complaint=row["total_complaint"],
        total_open=row["total_open"],
        delivery_rate=round(row["total_delivered"] / total * 100, 2),
        bounce_rate=round(row["total_bounce"] / total * 100, 2),
    )


@router.get("/blocked", response_model=list[BlockedEmail])
async def list_blocked(
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    rows = await conn.fetch("""
        SELECT id, email, reason, created_at
        FROM email_block
        ORDER BY created_at DESC
        LIMIT 200
    """)
    return [BlockedEmail(**dict(r)) for r in rows]



@router.get("/search", response_model=PaginatedEmails)
async def search_emails(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    """Búsqueda por destinatario O asunto (OR)."""
    offset = (page - 1) * per_page
    term = f"%{q}%"

    count_query = """
        SELECT COUNT(*) FROM email_send es
        WHERE es.email_to ILIKE $1 OR es.subject ILIKE $1
    """
    total = await conn.fetchval(count_query, term)

    data_query = """
        SELECT
            es.id, es.message_id, es.email_to, es.email_from,
            es.subject, es.created_at, es.has_attachments,
            COALESCE(
                LOWER(
                    (SELECT event_type FROM email_events
                     WHERE email_send_id = es.id
                     ORDER BY created_at DESC LIMIT 1)
                ),
                'send'
            ) AS status,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id AND LOWER(ee.event_type) = 'bounce'
            ) AS has_bounce,
            EXISTS (
                SELECT 1 FROM email_events ee
                WHERE ee.email_send_id = es.id AND LOWER(ee.event_type) = 'complaint'
            ) AS has_complaint
        FROM email_send es
        WHERE es.email_to ILIKE $1 OR es.subject ILIKE $1
        ORDER BY es.created_at DESC
        LIMIT $2 OFFSET $3
    """
    rows = await conn.fetch(data_query, term, per_page, offset)
    items = [EmailSummary(**dict(r)) for r in rows]
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedEmails(
        items=items, total=total,
        page=page, per_page=per_page, pages=pages
    )

@router.get("/{email_id}", response_model=EmailDetail)
async def get_email(
    email_id: int,
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    row = await conn.fetchrow("""
        SELECT
            es.id, es.message_id, es.email_to, es.email_from,
            es.subject, es.content, es.mime_type, es.created_at,
            es.has_attachments, es.attachments,
            COALESCE(
                LOWER(
                    (SELECT event_type FROM email_events
                     WHERE email_send_id = es.id
                     ORDER BY created_at DESC LIMIT 1)
                ),
                'send'
            ) AS status
        FROM email_send es
        WHERE es.id = $1
    """, email_id)

    if not row:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    event_rows = await conn.fetch("""
        SELECT id, email_send_id, event_type, event_data, created_at
        FROM email_events
        WHERE email_send_id = $1
        ORDER BY created_at ASC
    """, email_id)

    events = []
    for er in event_rows:
        e = dict(er)
        if isinstance(e.get("event_data"), str):
            try:
                e["event_data"] = json.loads(e["event_data"])
            except Exception:
                pass
        events.append(EmailEvent(**e))

    detail = dict(row)
    if isinstance(detail.get("attachments"), str):
        try:
            detail["attachments"] = json.loads(detail["attachments"])
        except Exception:
            pass
    detail["events"] = events
    return EmailDetail(**detail)


@router.get("/{email_id}/events", response_model=list[EmailEvent])
async def get_email_events(
    email_id: int,
    conn=Depends(get_conn),
    _=Depends(get_current_user),
):
    rows = await conn.fetch("""
        SELECT id, email_send_id, event_type, event_data, created_at
        FROM email_events
        WHERE email_send_id = $1
        ORDER BY created_at ASC
    """, email_id)

    events = []
    for r in rows:
        e = dict(r)
        if isinstance(e.get("event_data"), str):
            try:
                e["event_data"] = json.loads(e["event_data"])
            except Exception:
                pass
        events.append(EmailEvent(**e))
    return events