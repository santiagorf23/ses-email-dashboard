import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from db.database import get_conn
from routers.auth import get_current_user
from services.ses_send import (
    get_ses_service, init_ses_service,
    SendEmailRequest, SendEmailResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SESConfigRequest(BaseModel):
    """Request to configure SES."""
    aws_access_key_id: str
    aws_secret_access_key: str
    region: str = "us-east-1"
    source_email: str


class SendEmailAPIRequest(BaseModel):
    """API request to send email."""
    to: list[str]
    subject: str
    html_body: str
    text_body: Optional[str] = None
    reply_to: Optional[str] = None


@router.post("/configure")
async def configure_ses(
    config: SESConfigRequest,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Configure SES for current tenant."""
    tenant_id = current_user["tenant_id"]
    
    # Store configuration (in production, encrypt these values)
    await conn.execute("""
        UPDATE tenants 
        SET ses_config = $1, updated_at = NOW()
        WHERE id = $2
    """, {
        "aws_access_key_id": config.aws_access_key_id,
        "aws_secret_access_key": config.aws_secret_access_key,
        "region": config.region,
        "source_email": config.source_email
    }, tenant_id)
    
    # Initialize SES service
    init_ses_service(config.aws_access_key_id, config.aws_secret_access_key, config.region)
    
    return {"status": "configured", "region": config.region, "source": config.source_email}


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailAPIRequest,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Send email via SES."""
    tenant_id = current_user["tenant_id"]
    
    # Get SES config
    row = await conn.fetchrow("""
        SELECT ses_config FROM tenants WHERE id = $1
    """, tenant_id)
    
    if not row or not row["ses_config"]:
        raise HTTPException(status_code=400, detail="SES no está configurado. Usa POST /api/ses/configure primero.")
    
    config = row["ses_config"]
    
    # Initialize SES service if not already done
    ses = get_ses_service()
    if not ses:
        ses = init_ses_service(
            config["aws_access_key_id"],
            config["aws_secret_access_key"],
            config["region"]
        )
    
    # Send email
    try:
        result = ses.send_email(
            SendEmailRequest(
                to=request.to,
                subject=request.subject,
                html_body=request.html_body,
                text_body=request.text_body,
                reply_to=request.reply_to
            ),
            source=config["source_email"]
        )
        
        # Log email send
        await conn.execute("""
            INSERT INTO email_send (tenant_id, email_from, email_to, subject, message_id, status)
            VALUES ($1, $2, $3, $4, $5, 'sent')
        """, tenant_id, config["source_email"], ",".join(request.to), 
             request.subject, result.message_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")


@router.post("/verify")
async def verify_email(
    email: str,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Verify email identity with SES."""
    tenant_id = current_user["tenant_id"]
    
    # Get SES config
    row = await conn.fetchrow("""
        SELECT ses_config FROM tenants WHERE id = $1
    """, tenant_id)
    
    if not row or not row["ses_config"]:
        raise HTTPException(status_code=400, detail="SES no está configurado")
    
    config = row["ses_config"]
    
    # Initialize SES service
    ses = init_ses_service(
        config["aws_access_key_id"],
        config["aws_secret_access_key"],
        config["region"]
    )
    
    # Verify email
    success = ses.verify_email_identity(email)
    
    if success:
        return {"status": "verification_sent", "email": email}
    else:
        raise HTTPException(status_code=500, detail="Error al verificar email")


@router.get("/quota")
async def get_send_quota(
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get SES send quota."""
    tenant_id = current_user["tenant_id"]
    
    # Get SES config
    row = await conn.fetchrow("""
        SELECT ses_config FROM tenants WHERE id = $1
    """, tenant_id)
    
    if not row or not row["ses_config"]:
        raise HTTPException(status_code=400, detail="SES no está configurado")
    
    config = row["ses_config"]
    
    # Initialize SES service
    ses = init_ses_service(
        config["aws_access_key_id"],
        config["aws_secret_access_key"],
        config["region"]
    )
    
    # Get quota
    quota = ses.get_send_quota()
    
    return quota


@router.get("/statistics")
async def get_send_statistics(
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get SES send statistics."""
    tenant_id = current_user["tenant_id"]
    
    # Get SES config
    row = await conn.fetchrow("""
        SELECT ses_config FROM tenants WHERE id = $1
    """, tenant_id)
    
    if not row or not row["ses_config"]:
        raise HTTPException(status_code=400, detail="SES no está configurado")
    
    config = row["ses_config"]
    
    # Initialize SES service
    ses = init_ses_service(
        config["aws_access_key_id"],
        config["aws_secret_access_key"],
        config["region"]
    )
    
    # Get statistics
    stats = ses.get_send_statistics()
    
    return stats
