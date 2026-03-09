from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class EmailEvent(BaseModel):
    id: int
    email_send_id: int
    event_type: str
    event_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailSummary(BaseModel):
    id: int
    message_id: Optional[str] = None
    email_to: str
    email_from: Optional[str] = None
    subject: Optional[str] = None
    # status se deriva del último evento
    status: str = "sent"
    created_at: datetime
    has_bounce: bool = False
    has_complaint: bool = False
    has_attachments: bool = False

    class Config:
        from_attributes = True


class EmailDetail(BaseModel):
    id: int
    message_id: Optional[str] = None
    email_to: str
    email_from: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    mime_type: Optional[str] = "text/html"
    status: str = "sent"
    created_at: datetime
    has_attachments: bool = False
    attachments: Optional[Any] = None
    events: list[EmailEvent] = []

    class Config:
        from_attributes = True


class PaginatedEmails(BaseModel):
    items: list[EmailSummary]
    total: int
    page: int
    per_page: int
    pages: int


class BlockedEmail(BaseModel):
    id: int
    email: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_sent: int
    total_delivered: int
    total_bounce: int
    total_complaint: int
    total_open: int = 0
    delivery_rate: float
    bounce_rate: float