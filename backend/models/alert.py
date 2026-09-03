from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class AlertConfigBase(BaseModel):
    bounce_rate_threshold: float = 5.0
    bounce_rate_window_hours: int = 24
    sudden_bounce_count: int = 10
    sudden_bounce_window_minutes: int = 60
    complaint_rate_threshold: float = 0.1
    complaint_rate_window_hours: int = 24
    blocked_count_threshold: int = 5
    blocked_window_hours: int = 24
    notify_email: Optional[str] = None
    notify_slack_webhook: Optional[str] = None
    is_enabled: bool = True


class AlertConfigUpdate(BaseModel):
    bounce_rate_threshold: Optional[float] = None
    bounce_rate_window_hours: Optional[int] = None
    sudden_bounce_count: Optional[int] = None
    sudden_bounce_window_minutes: Optional[int] = None
    complaint_rate_threshold: Optional[float] = None
    complaint_rate_window_hours: Optional[int] = None
    blocked_count_threshold: Optional[int] = None
    blocked_window_hours: Optional[int] = None
    notify_email: Optional[str] = None
    notify_slack_webhook: Optional[str] = None
    is_enabled: Optional[bool] = None


class AlertConfigResponse(AlertConfigBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Alert(BaseModel):
    id: int
    tenant_id: int
    alert_type: str
    severity: str
    title: str
    message: str
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    total_alerts: int
    unread_alerts: int
    critical_alerts: int
    warning_alerts: int
    last_alert_at: Optional[datetime] = None
