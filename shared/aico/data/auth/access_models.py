from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuthAccessPolicy(BaseModel):
    uuid: str
    user_uuid: str
    resource_type: str
    resource_uuid: Optional[str] = None
    permission: str
    is_active: bool = True
    created_at: Optional[datetime] = None
