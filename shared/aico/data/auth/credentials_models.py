from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuthUserCredentials(BaseModel):
    uuid: str
    user_uuid: str
    password_hash: str

    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
