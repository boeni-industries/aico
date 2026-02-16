from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class AMSConsolidationState(BaseModel):
    id: str
    state_json: Dict[str, Any]
    updated_at: Optional[datetime] = None
