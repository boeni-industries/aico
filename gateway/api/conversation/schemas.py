from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ConversationResponse(BaseModel):
    success: bool
    conversation_id: str
    status: str
    created_at: datetime
    message_count: int = 0
    metadata: Optional[dict[str, Any]] = None


class MessageResponse(BaseModel):
    success: bool
    message_id: str
    conversation_id: str
    status: str
    timestamp: datetime
    metadata: Optional[dict[str, Any]] = None


class CatchupMessage(BaseModel):
    message_id: str
    conversation_id: str
    actor_type: str
    message_type: str
    content: str
    turn_number: int
    created_at: datetime
    metadata: Optional[dict[str, Any]] = None


class ConversationStatus(BaseModel):
    conversation_id: str
    active: bool
    message_count: int
    last_activity: str
    context: Optional[dict[str, Any]] = None
    user_id: str


class ConversationListResponse(BaseModel):
    success: bool
    conversations: list[dict[str, Any]]
    total_count: int
    page: int = 1
    page_size: int = 20


class MessageHistoryResponse(BaseModel):
    success: bool
    conversation_id: str
    messages: list[dict[str, Any]]
    total_count: int
    page: int = 1
    page_size: int = 50


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class UnifiedMessageRequest(BaseModel):
    message: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    context: Optional[dict[str, Any]] = Field(None, description="Context")
    metadata: Optional[dict[str, Any]] = Field(None, description="Metadata")
    client_id: Optional[str] = Field(None, description="Client ID")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Message cannot be empty")
        if len(value) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return value.strip()


class UnifiedMessageResponse(BaseModel):
    success: bool
    message_id: str
    conversation_id: str
    conversation_action: str
    conversation_reasoning: str
    status: str
    timestamp: datetime
    ai_response: Optional[str] = None


class WebSocketMessageType(str, Enum):
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    AI_RESPONSE = "ai_response"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class ConversationListItem(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0


class ConversationPageResponse(BaseModel):
    items: list[ConversationListItem]
    total: int
    limit: int
    offset: int


class ConversationDetail(BaseModel):
    tenant_id: str
    conversation_id: str
    user_id: str
    agent_id: Optional[str] = None
    title: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
