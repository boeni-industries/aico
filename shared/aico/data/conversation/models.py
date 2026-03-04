from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class Conversation(BaseModel):
    tenant_id: str
    conversation_id: str
    user_id: str

    agent_id: Optional[str] = None
    title: Optional[str] = None
    status: str = "active"

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationMessage(BaseModel):
    message_id: str
    tenant_id: str
    conversation_id: str
    user_id: str

    agent_id: Optional[str] = None

    actor_type: str
    actor_id: Optional[str] = None
    message_type: str
    content: str

    metadata_json: Optional[dict[str, Any]] = None
    correlation_id: Optional[str] = None
    request_id: str
    turn_number: int

    created_at: Optional[datetime] = None

