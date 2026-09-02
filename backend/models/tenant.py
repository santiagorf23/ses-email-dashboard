from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TenantBase(BaseModel):
    name: str
    slug: str
    plan: str = "free"
    aws_region: str = "us-east-1"


class TenantCreate(TenantBase):
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    aws_region: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_sns_topic_arn: Optional[str] = None


class TenantResponse(TenantBase):
    id: int
    plan_limits: Optional[Any] = None
    aws_sns_topic_arn: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantStats(BaseModel):
    tenant_id: int
    tenant_name: str
    total_emails: int
    total_events: int
    total_blocked: int
