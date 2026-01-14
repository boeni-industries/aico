from __future__ import annotations

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

    granted_at: str
    revoked_at: Optional[str] = None

    created_at: str
    updated_at: str
