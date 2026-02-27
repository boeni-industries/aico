from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OutboxEvent(BaseModel):
    event_id: str
    tenant_id: str
    subject: str
    payload_bytes: bytes

    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None

    available_at: datetime | None = None
    created_at: datetime | None = None
    sent_at: datetime | None = None
