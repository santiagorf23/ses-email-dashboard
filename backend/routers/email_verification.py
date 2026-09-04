import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from db.database import get_conn
from routers.auth import get_current_user
from services.email_verification import (
    verify_email, verify_bulk_emails, check_disposable_domain,
    add_disposable_domain, remove_disposable_domain,
    VerificationResult, BulkVerificationResult
)

logger = logging.getLogger(__name__)

router = APIRouter()


class EmailCheckRequest(BaseModel):
    """Request to verify a single email."""
    email: str


class BulkEmailCheckRequest(BaseModel):
    """Request to verify multiple emails."""
    emails: list[str]


class DisposableDomainRequest(BaseModel):
    """Request to add/remove disposable domain."""
    domain: str


@router.post("/verify", response_model=VerificationResult)
async def verify_single_email(
    request: EmailCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify a single email address."""
    result = verify_email(request.email)
    return result


@router.post("/verify-bulk", response_model=BulkVerificationResult)
async def verify_bulk(
    request: BulkEmailCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify multiple email addresses."""
    if len(request.emails) > 1000:
        raise HTTPException(status_code=400, detail="Máximo 1000 correos por consulta")
    
    result = verify_bulk_emails(request.emails)
    return result


@router.get("/disposable/check/{domain}")
async def check_disposable(
    domain: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if a domain is disposable."""
    is_disposable = check_disposable_domain(domain)
    return {"domain": domain, "is_disposable": is_disposable}


@router.post("/disposable/add")
async def add_disposable(
    request: DisposableDomainRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a domain to the disposable list."""
    add_disposable_domain(request.domain)
    return {"status": "added", "domain": request.domain}


@router.delete("/disposable/{domain}")
async def remove_disposable(
    domain: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a domain from the disposable list."""
    remove_disposable_domain(domain)
    return {"status": "removed", "domain": domain}


@router.get("/stats")
async def get_verification_stats(
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get verification statistics for the tenant."""
    tenant_id = current_user["tenant_id"]
    
    # Get stats from email_send table
    row = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_emails,
            COUNT(DISTINCT SPLIT_PART(email_from, '@', 2)) as unique_domains
        FROM email_send
        WHERE tenant_id = $1
    """, tenant_id)
    
    return {
        "total_emails": row["total_emails"] or 0,
        "unique_domains": row["unique_domains"] or 0
    }
