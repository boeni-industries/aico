"""
Conversation API Schemas

Pydantic models for conversation API request/response validation and serialization.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class MessageType(str, Enum):
    """Message type enumeration"""
    USER_INPUT = "user_input"
    AI_RESPONSE = "ai_response"
    SYSTEM = "system"
    PROACTIVE = "proactive"


class ConversationStartRequest(BaseModel):
    """Request to start a new conversation"""
    initial_message: Optional[str] = Field(None, description="Optional initial message to start conversation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for conversation")
    response_mode: Optional[str] = Field("multimodal", description="Response mode: text_only, multimodal, proactive")
    
    @validator('initial_message')
    def validate_initial_message(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Initial message cannot be empty")
        if v is not None and len(v) > 10000:
            raise ValueError("Initial message too long (max 10000 characters)")
        return v


class ConversationMessageRequest(BaseModel):
    """Request to send a message in conversation"""
    thread_id: str = Field(..., description="Conversation thread ID")
    message: str = Field(..., description="User message content")
    message_type: MessageType = Field(MessageType.USER_INPUT, description="Message type")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional message context")
    
    @validator('thread_id')
    def validate_thread_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Thread ID is required")
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message content is required")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()


class ConversationResponse(BaseModel):
    """Response from conversation API"""
    success: bool = Field(..., description="Whether the operation succeeded")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")
    message_id: Optional[str] = Field(None, description="Generated message ID")
    response: Optional[str] = Field(None, description="Response message or acknowledgment")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ConversationStatus(BaseModel):
    """Status of a conversation thread"""
    thread_id: str = Field(..., description="Conversation thread ID")
    active: bool = Field(..., description="Whether conversation is active")
    message_count: int = Field(..., description="Number of messages in conversation")
    last_activity: datetime = Field(..., description="Timestamp of last activity")
    context: Optional[Dict[str, Any]] = Field(None, description="Current conversation context")
    user_id: str = Field(..., description="Owner user ID")


class ConversationListRequest(BaseModel):
    """Request to list conversations"""
    limit: Optional[int] = Field(50, description="Number of conversations to return", ge=1, le=100)
    offset: Optional[int] = Field(0, description="Pagination offset", ge=0)
    active_only: Optional[bool] = Field(True, description="Only return active conversations")
    since: Optional[datetime] = Field(None, description="Show conversations after timestamp")


class ConversationListResponse(BaseModel):
    """Response for conversation list"""
    conversations: List[ConversationStatus] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    has_more: bool = Field(..., description="Whether more conversations are available")


# WebSocket Message Schemas
class WebSocketMessageType(str, Enum):
    """WebSocket message types"""
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    AI_RESPONSE = "ai_response"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema"""
    type: WebSocketMessageType = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    data: Optional[Dict[str, Any]] = Field(None, description="Message payload")


class WebSocketAIResponse(WebSocketMessage):
    """AI response via WebSocket"""
    type: WebSocketMessageType = Field(WebSocketMessageType.AI_RESPONSE, description="Message type")
    thread_id: str = Field(..., description="Conversation thread ID")
    message_id: str = Field(..., description="AI message ID")
    message: str = Field(..., description="AI response text")
    confidence: Optional[float] = Field(None, description="Response confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class WebSocketError(WebSocketMessage):
    """Error message via WebSocket"""
    type: WebSocketMessageType = Field(WebSocketMessageType.ERROR, description="Message type")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    thread_id: Optional[str] = Field(None, description="Related thread ID if applicable")


class WebSocketStatusUpdate(WebSocketMessage):
    """Status update via WebSocket"""
    type: WebSocketMessageType = Field(WebSocketMessageType.STATUS_UPDATE, description="Message type")
    thread_id: str = Field(..., description="Conversation thread ID")
    status: str = Field(..., description="New status")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")


# Protobuf Conversion Schemas
class ProtobufConversationMessage(BaseModel):
    """Schema for converting to/from protobuf ConversationMessage"""
    timestamp: datetime = Field(..., description="Message timestamp")
    source: str = Field(..., description="Message source (user ID)")
    text: str = Field(..., description="Message text content")
    message_type: MessageType = Field(..., description="Message type")
    thread_id: str = Field(..., description="Conversation thread ID")
    turn_number: int = Field(..., description="Turn number in conversation")
    intent: Optional[str] = Field(None, description="Detected intent")
    urgency: Optional[str] = Field("medium", description="Message urgency level")
    requires_response: bool = Field(True, description="Whether message requires response")


class ConversationHealthResponse(BaseModel):
    """Health check response for conversation API"""
    status: str = Field(..., description="Service status")
    active_connections: int = Field(..., description="Number of active WebSocket connections")
    active_threads: int = Field(0, description="Number of active conversation threads")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field("1.0.0", description="API version")
