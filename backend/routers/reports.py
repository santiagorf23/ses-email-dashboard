import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from db.database import get_conn
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class DomainReport(BaseModel):
    domain: str
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_complaints: int
    total_opened: int
    delivery_rate: float
    bounce_rate: float
    complaint_rate: float
    open_rate: float
    reputation_score: int  # 0-100
    reputation_label: str  # excellent, good, fair, poor


class TrendDataPoint(BaseModel):
    date: str
    sent: int
    delivered: int
    bounced: int
    complaints: int
    opened: int
    delivery_rate: float
    bounce_rate: float
    complaint_rate: float


class DeliverabilityReport(BaseModel):
    period_days: int
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_complaints: int
    total_opened: int
    overall_delivery_rate: float
    overall_bounce_rate: float
    overall_complaint_rate: float
    overall_open_rate: float
    domains: list[DomainReport]
    trends: list[TrendDataPoint]


@router.get("", response_model=DeliverabilityReport)
async def get_deliverability_report(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get deliverability report for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    # Get overall stats
    overall = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as total_sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as total_delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as total_bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as total_complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as total_opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
    """, tenant_id, days)
    
    total_sent = overall["total_sent"] or 0
    total_delivered = overall["total_delivered"] or 0
    total_bounced = overall["total_bounced"] or 0
    total_complaints = overall["total_complaints"] or 0
    total_opened = overall["total_opened"] or 0
    
    # Get domain breakdown
    domain_rows = await conn.fetch("""
        SELECT 
            SPLIT_PART(es.email_from, '@', 2) as domain,
            COUNT(DISTINCT es.id) as total_sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as total_delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as total_bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as total_complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as total_opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY SPLIT_PART(es.email_from, '@', 2)
        ORDER BY total_sent DESC
    """, tenant_id, days)
    
    domains = []
    for row in domain_rows:
        d = dict(row)
        d_sent = d["total_sent"] or 0
        d_delivered = d["total_delivered"] or 0
        d_bounced = d["total_bounced"] or 0
        d_complaints = d["total_complaints"] or 0
        d_opened = d["total_opened"] or 0
        
        delivery_rate = (d_delivered / d_sent * 100) if d_sent > 0 else 0
        bounce_rate = (d_bounced / d_sent * 100) if d_sent > 0 else 0
        complaint_rate = (d_complaints / d_sent * 100) if d_sent > 0 else 0
        open_rate = (d_opened / d_delivered * 100) if d_delivered > 0 else 0
        
        # Calculate reputation score (0-100)
        score = _calculate_reputation_score(delivery_rate, bounce_rate, complaint_rate, open_rate)
        label = _get_reputation_label(score)
        
        domains.append(DomainReport(
            domain=d["domain"],
            total_sent=d_sent,
            total_delivered=d_delivered,
            total_bounced=d_bounced,
            total_complaints=d_complaints,
            total_opened=d_opened,
            delivery_rate=round(delivery_rate, 2),
            bounce_rate=round(bounce_rate, 2),
            complaint_rate=round(complaint_rate, 2),
            open_rate=round(open_rate, 2),
            reputation_score=score,
            reputation_label=label
        ))
    
    # Get daily trends
    trend_rows = await conn.fetch("""
        SELECT 
            DATE(es.created_at) as date,
            COUNT(DISTINCT es.id) as sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY DATE(es.created_at)
        ORDER BY date ASC
    """, tenant_id, days)
    
    trends = []
    for row in trend_rows:
        t = dict(row)
        t_sent = t["sent"] or 0
        t_delivered = t["delivered"] or 0
        t_bounced = t["bounced"] or 0
        t_complaints = t["complaints"] or 0
        t_opened = t["opened"] or 0
        
        trends.append(TrendDataPoint(
            date=str(t["date"]),
            sent=t_sent,
            delivered=t_delivered,
            bounced=t_bounced,
            complaints=t_complaints,
            opened=t_opened,
            delivery_rate=round((t_delivered / t_sent * 100) if t_sent > 0 else 0, 2),
            bounce_rate=round((t_bounced / t_sent * 100) if t_sent > 0 else 0, 2),
            complaint_rate=round((t_complaints / t_sent * 100) if t_sent > 0 else 0, 2)
        ))
    
    return DeliverabilityReport(
        period_days=days,
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_bounced=total_bounced,
        total_complaints=total_complaints,
        total_opened=total_opened,
        overall_delivery_rate=round((total_delivered / total_sent * 100) if total_sent > 0 else 0, 2),
        overall_bounce_rate=round((total_bounced / total_sent * 100) if total_sent > 0 else 0, 2),
        overall_complaint_rate=round((total_complaints / total_sent * 100) if total_sent > 0 else 0, 2),
        overall_open_rate=round((total_opened / total_delivered * 100) if total_delivered > 0 else 0, 2),
        domains=domains,
        trends=trends
    )


@router.get("/domains", response_model=list[DomainReport])
async def get_domain_reports(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get per-domain deliverability reports."""
    tenant_id = current_user["tenant_id"]
    
    rows = await conn.fetch("""
        SELECT 
            SPLIT_PART(es.email_from, '@', 2) as domain,
            COUNT(DISTINCT es.id) as total_sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'delivery' THEN ee.email_send_id END) as total_delivered,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'bounce' THEN ee.email_send_id END) as total_bounced,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'complaint' THEN ee.email_send_id END) as total_complaints,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as total_opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY SPLIT_PART(es.email_from, '@', 2)
        ORDER BY total_sent DESC
    """, tenant_id, days)
    
    results = []
    for row in rows:
        d = dict(row)
        d_sent = d["total_sent"] or 0
        d_delivered = d["total_delivered"] or 0
        d_bounced = d["total_bounced"] or 0
        d_complaints = d["total_complaints"] or 0
        d_opened = d["total_opened"] or 0
        
        delivery_rate = (d_delivered / d_sent * 100) if d_sent > 0 else 0
        bounce_rate = (d_bounced / d_sent * 100) if d_sent > 0 else 0
        complaint_rate = (d_complaints / d_sent * 100) if d_sent > 0 else 0
        open_rate = (d_opened / d_delivered * 100) if d_delivered > 0 else 0
        
        score = _calculate_reputation_score(delivery_rate, bounce_rate, complaint_rate, open_rate)
        label = _get_reputation_label(score)
        
        results.append(DomainReport(
            domain=d["domain"],
            total_sent=d_sent,
            total_delivered=d_delivered,
            total_bounced=d_bounced,
            total_complaints=d_complaints,
            total_opened=d_opened,
            delivery_rate=round(delivery_rate, 2),
            bounce_rate=round(bounce_rate, 2),
            complaint_rate=round(complaint_rate, 2),
            open_rate=round(open_rate, 2),
            reputation_score=score,
            reputation_label=label
        ))
    
    return results


def _calculate_reputation_score(delivery_rate: float, bounce_rate: float, complaint_rate: float, open_rate: float) -> int:
    """Calculate reputation score (0-100) based on key metrics."""
    score = 100
    
    # Deduct for high bounce rate
    if bounce_rate > 10:
        score -= 40
    elif bounce_rate > 5:
        score -= 25
    elif bounce_rate > 2:
        score -= 10
    elif bounce_rate > 1:
        score -= 5
    
    # Deduct for high complaint rate (very sensitive)
    if complaint_rate > 0.5:
        score -= 40
    elif complaint_rate > 0.1:
        score -= 20
    elif complaint_rate > 0.05:
        score -= 10
    
    # Bonus for good open rate
    if open_rate > 20:
        score += 5
    elif open_rate > 10:
        score += 2
    
    # Deduct for very low delivery rate
    if delivery_rate < 90:
        score -= 15
    elif delivery_rate < 95:
        score -= 5
    
    return max(0, min(100, score))


def _get_reputation_label(score: int) -> str:
    """Get reputation label from score."""
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "fair"
    else:
        return "poor"
