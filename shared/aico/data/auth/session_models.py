from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuthSession(BaseModel):
    uuid: str
    user_uuid: str
    device_uuid: str
    jwt_token_hash: str
    expires_at: datetime
    created_at: datetime | None = None
    is_active: bool = True
    session_type: str | None = None
