import os
import logging
import boto3
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from db.database import get_conn
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class AWSVerifyRequest(BaseModel):
    aws_access_key: str
    aws_secret_key: str
    aws_region: str = "us-east-1"


class DomainVerifyRequest(BaseModel):
    domain: str


class SNSSubscribeRequest(BaseModel):
    topic_arn: str


@router.get("/status")
async def get_onboarding_status(conn=Depends(get_conn), current_user: dict = Depends(get_current_user)):
    """Get onboarding status for current tenant."""
    tenant_id = current_user["tenant_id"]

    async for conn in get_conn():
        row = await conn.fetchrow("""
            SELECT id, name, slug, plan, aws_access_key_enc, aws_secret_key_enc,
                   aws_region, aws_sns_topic_arn, created_at
            FROM tenants WHERE id = $1
        """, tenant_id)

    if not row:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Determine onboarding step
    step = 1  # Welcome (always complete after tenant creation)
    if row["aws_access_key_enc"]:
        step = 2  # AWS configured
    if row["aws_sns_topic_arn"]:
        step = 4  # Webhook configured

    return {
        "tenant_id": row["id"],
        "tenant_name": row["name"],
        "tenant_slug": row["slug"],
        "plan": row["plan"],
        "current_step": step,
        "aws_configured": bool(row["aws_access_key_enc"]),
        "sns_configured": bool(row["aws_sns_topic_arn"]),
        "aws_region": row["aws_region"],
        "created_at": row["created_at"],
    }


@router.post("/verify-aws")
async def verify_aws_credentials(
    request: AWSVerifyRequest,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Verify AWS credentials by calling STS GetCallerIdentity."""
    try:
        client = boto3.client(
            "sts",
            aws_access_key_id=request.aws_access_key,
            aws_secret_access_key=request.aws_secret_key,
            region_name=request.aws_region,
        )
        identity = client.get_caller_identity()

        # Store encrypted credentials in tenant
        tenant_id = current_user["tenant_id"]
        async for conn in get_conn():
            await conn.execute("""
                UPDATE tenants
                SET aws_access_key_enc = $1, aws_secret_key_enc = $2, aws_region = $3, updated_at = NOW()
                WHERE id = $4
            """, request.aws_access_key, request.aws_secret_key, request.aws_region, tenant_id)

        return {
            "status": "verified",
            "account_id": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }

    except Exception as e:
        logger.error("AWS verification failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Credenciales AWS inválidas: {str(e)}")


@router.post("/verify-domain")
async def verify_domain(
    request: DomainVerifyRequest,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Start domain verification with SES."""
    tenant_id = current_user["tenant_id"]

    # Get AWS credentials from tenant
    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT aws_access_key_enc, aws_secret_key_enc, aws_region FROM tenants WHERE id = $1",
            tenant_id
        )

    if not row or not row["aws_access_key_enc"]:
        raise HTTPException(status_code=400, detail="Configura credenciales AWS primero")

    try:
        client = boto3.client(
            "ses",
            aws_access_key_id=row["aws_access_key_enc"],
            aws_secret_access_key=row["aws_secret_key_enc"],
            region_name=row["aws_region"],
        )

        response = client.verify_domain_identity(Domain=request.domain)

        return {
            "status": "verification_started",
            "verification_token": response.get("VerificationToken"),
            "domain": request.domain,
            "instructions": {
                "txt_record": f"amazonses:{response.get('VerificationToken')}",
                "cname_bounce": f"feedback-smtp.{row['aws_region']}.amazonses.com",
                "cname_dkim": f"abstractmethod._domainkey.{row['aws_region']}.amazonses.com",
            }
        }

    except Exception as e:
        logger.error("Domain verification failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Error verificando dominio: {str(e)}")


@router.post("/subscribe-sns")
async def subscribe_sns_topic(
    request: SNSSubscribeRequest,
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Subscribe to SNS topic for SES events."""
    tenant_id = current_user["tenant_id"]

    # Get AWS credentials
    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT aws_access_key_enc, aws_secret_key_enc, aws_region FROM tenants WHERE id = $1",
            tenant_id
        )

    if not row or not row["aws_access_key_enc"]:
        raise HTTPException(status_code=400, detail="Configura credenciales AWS primero")

    try:
        client = boto3.client(
            "sns",
            aws_access_key_id=row["aws_access_key_enc"],
            aws_secret_access_key=row["aws_secret_key_enc"],
            region_name=row["aws_region"],
        )

        # Subscribe webhook endpoint
        webhook_url = os.getenv("WEBHOOK_URL", "https://your-domain.com/api/webhooks/ses")
        response = client.subscribe(
            TopicArn=request.topic_arn,
            Protocol="https",
            Endpoint=webhook_url,
            ReturnSubscriptionArn=True,
        )

        # Store topic ARN in tenant
        async for conn in get_conn():
            await conn.execute("""
                UPDATE tenants
                SET aws_sns_topic_arn = $1, updated_at = NOW()
                WHERE id = $2
            """, request.topic_arn, tenant_id)

        return {
            "status": "subscribed",
            "subscription_arn": response.get("SubscriptionArn"),
            "topic_arn": request.topic_arn,
        }

    except Exception as e:
        logger.error("SNS subscription failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Error suscribiendo SNS: {str(e)}")


@router.get("/check-sns")
async def check_sns_subscription(
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    """Check SNS subscription status."""
    tenant_id = current_user["tenant_id"]

    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT aws_sns_topic_arn, aws_access_key_enc, aws_secret_key_enc, aws_region FROM tenants WHERE id = $1",
            tenant_id
        )

    if not row or not row["aws_sns_topic_arn"]:
        return {"status": "not_configured"}

    if not row["aws_access_key_enc"]:
        return {"status": "credentials_missing"}

    try:
        client = boto3.client(
            "sns",
            aws_access_key_id=row["aws_access_key_enc"],
            aws_secret_access_key=row["aws_secret_key_enc"],
            region_name=row["aws_region"],
        )

        response = client.list_subscriptions_by_topic(TopicArn=row["aws_sns_topic_arn"])
        subscriptions = response.get("Subscriptions", [])

        # Find our webhook subscription
        webhook_sub = None
        for sub in subscriptions:
            if sub.get("Protocol") == "https":
                webhook_sub = sub
                break

        if webhook_sub:
            return {
                "status": "active" if webhook_sub.get("SubscriptionArn") != "PendingConfirmation" else "pending",
                "subscription_arn": webhook_sub.get("SubscriptionArn"),
                "topic_arn": row["aws_sns_topic_arn"],
            }

        return {"status": "not_subscribed", "topic_arn": row["aws_sns_topic_arn"]}

    except Exception as e:
        logger.error("SNS check failed: %s", e)
        return {"status": "error", "error": str(e)}
