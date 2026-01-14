from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Device(BaseModel):
    uuid: str
    device_name: str
    device_type: str
    platform: str

    last_seen: Optional[datetime] = None
    is_active: bool = True

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
