from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class Tenant(BaseModel):
    tenant_id: str
    tenant_type: str
    display_name: str

    status: str = "active"
    primary_language: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TenantMembership(BaseModel):
    membership_id: str
    tenant_id: str
    user_id: str

    role: str = "member"
    created_at: Optional[datetime] = None
