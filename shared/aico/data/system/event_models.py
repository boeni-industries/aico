from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class SystemEvent(BaseModel):
    id: int = 0
    timestamp: datetime
    topic: str
    source: str
    message_type: str
    message_id: str

    priority: int = 1
    correlation_id: Optional[str] = None

    payload: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None

    created_at: Optional[datetime] = None
