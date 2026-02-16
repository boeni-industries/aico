from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ConsentRecord(BaseModel):
    consent_id: str
    user_id: str
    consent_scope: str
    decision: str

    context_json: Optional[Dict[str, Any]] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
