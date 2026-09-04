import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from db.database import get_conn
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class ABTestBase(BaseModel):
    """Base model for A/B test."""
    name: str
    subject_a: str
    subject_b: str
    description: Optional[str] = None


class ABTestCreate(ABTestBase):
    """Create A/B test request."""
    pass


class ABTestResponse(ABTestBase):
    """A/B test response."""
    id: int
    tenant_id: int
    status: str  # draft, running, completed
    winner: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ABTestStats(BaseModel):
    """A/B test statistics."""
    test_id: int
    subject_a: str
    subject_b: str
    sent_a: int
    sent_b: int
    opened_a: int
    opened_b: int
    open_rate_a: float
    open_rate_b: float
    winner: Optional[str] = None
    confidence: float


@router.get("", response_model=list[ABTestResponse])
async def list_ab_tests(
    limit: int = 50,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """List A/B tests for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    rows = await conn.fetch("""
        SELECT * FROM ab_tests 
        WHERE tenant_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
    """, tenant_id, limit)
    
    return [ABTestResponse(**dict(r)) for r in rows]


@router.post("", response_model=ABTestResponse)
async def create_ab_test(
    test: ABTestCreate,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Create a new A/B test."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow("""
        INSERT INTO ab_tests (tenant_id, name, subject_a, subject_b, description, status)
        VALUES ($1, $2, $3, $4, $5, 'draft')
        RETURNING *
    """, tenant_id, test.name, test.subject_a, test.subject_b, test.description)
    
    return ABTestResponse(**dict(row))


@router.get("/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get A/B test by ID."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow("""
        SELECT * FROM ab_tests 
        WHERE id = $1 AND tenant_id = $2
    """, test_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    
    return ABTestResponse(**dict(row))


@router.put("/{test_id}/start")
async def start_ab_test(
    test_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Start an A/B test."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow("""
        UPDATE ab_tests 
        SET status = 'running', updated_at = NOW()
        WHERE id = $1 AND tenant_id = $2 AND status = 'draft'
        RETURNING *
    """, test_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Test no encontrado o ya iniciado")
    
    return {"status": "started", "test_id": test_id}


@router.put("/{test_id}/complete")
async def complete_ab_test(
    test_id: int,
    winner: Optional[str] = Query(None, regex="^(a|b)$"),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Complete an A/B test."""
    tenant_id = current_user["tenant_id"]
    
    row = await conn.fetchrow("""
        UPDATE ab_tests 
        SET status = 'completed', winner = $3, updated_at = NOW()
        WHERE id = $1 AND tenant_id = $2 AND status = 'running'
        RETURNING *
    """, test_id, tenant_id, winner)
    
    if not row:
        raise HTTPException(status_code=404, detail="Test no encontrado o ya completado")
    
    return {"status": "completed", "test_id": test_id, "winner": winner}


@router.get("/{test_id}/stats", response_model=ABTestStats)
async def get_ab_test_stats(
    test_id: int,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get A/B test statistics."""
    tenant_id = current_user["tenant_id"]
    
    # Get test info
    test = await conn.fetchrow("""
        SELECT * FROM ab_tests 
        WHERE id = $1 AND tenant_id = $2
    """, test_id, tenant_id)
    
    if not test:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    
    # Get stats for variant A
    stats_a = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.subject = $2
    """, tenant_id, test["subject_a"])
    
    # Get stats for variant B
    stats_b = await conn.fetchrow("""
        SELECT 
            COUNT(DISTINCT es.id) as sent,
            COUNT(DISTINCT CASE WHEN LOWER(ee.event_type) = 'open' THEN ee.email_send_id END) as opened
        FROM email_send es
        LEFT JOIN email_events ee ON es.id = ee.email_send_id AND ee.tenant_id = $1
        WHERE es.tenant_id = $1 
        AND es.subject = $2
    """, tenant_id, test["subject_b"])
    
    sent_a = stats_a["sent"] or 0
    sent_b = stats_b["sent"] or 0
    opened_a = stats_a["opened"] or 0
    opened_b = stats_b["opened"] or 0
    
    open_rate_a = (opened_a / sent_a * 100) if sent_a > 0 else 0
    open_rate_b = (opened_b / sent_b * 100) if sent_b > 0 else 0
    
    # Determine winner
    winner = None
    if open_rate_a > open_rate_b:
        winner = "a"
    elif open_rate_b > open_rate_a:
        winner = "b"
    
    # Calculate confidence (simplified)
    confidence = _calculate_confidence(open_rate_a, open_rate_b, sent_a, sent_b)
    
    return ABTestStats(
        test_id=test_id,
        subject_a=test["subject_a"],
        subject_b=test["subject_b"],
        sent_a=sent_a,
        sent_b=sent_b,
        opened_a=opened_a,
        opened_b=opened_b,
        open_rate_a=round(open_rate_a, 2),
        open_rate_b=round(open_rate_b, 2),
        winner=winner,
        confidence=round(confidence, 2)
    )


def _calculate_confidence(rate_a: float, rate_b: float, n_a: int, n_b: int) -> float:
    """Calculate statistical confidence (simplified Z-test)."""
    if n_a == 0 or n_b == 0:
        return 0.0
    
    # Pooled proportion
    p = (rate_a * n_a / 100 + rate_b * n_b / 100) / (n_a + n_b)
    
    # Standard error
    se = (p * (1 - p) * (1/n_a + 1/n_b)) ** 0.5
    
    if se == 0:
        return 100.0 if rate_a != rate_b else 0.0
    
    # Z-score
    z = abs(rate_a - rate_b) / 100 / se
    
    # Convert to confidence (approximation)
    # Z > 1.96 = 95% confidence
    confidence = min(100, (z / 1.96) * 95)
    
    return confidence
