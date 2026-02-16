from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConsentAuditLog(BaseModel):
    audit_id: str
    consent_id: str
    user_id: str
    action: str
    reason: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime
