from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ConsentUserConsent(BaseModel):
    consent_id: str
    user_id: str
    consent_type: str
    scope: str
    scope_identifier: Optional[str] = None

    granted: int
    expires_at: Optional[str] = None
    inherited_from: Optional[str] = None

    granted_at: datetime
    revoked_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


class ConsentRecord(BaseModel):
    consent_id: str
    user_id: str
    consent_scope: str
    decision: str

    context_json: Optional[Dict[str, Any]] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ConsentAuditLog(BaseModel):
    audit_id: str
    consent_id: str
    user_id: str
    action: str
    reason: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime
