from __future__ import annotations

from datetime import datetime
from typing import Optional

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
