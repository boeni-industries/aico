from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class EthicsPolicyRule(BaseModel):
    rule_id: str
    rule_name: str
    target_type: str
    conditions_json: Dict[str, Any]
    effect: str

    user_message_template: Optional[str] = None

    priority: int = 100
    enabled: bool = True

    scope: str = "global"
    scope_id: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
