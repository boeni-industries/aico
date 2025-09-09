"""
Conversation API Schemas

Pydantic models for conversation API request/response validation and serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from enum import Enum
import uuid


class MessageType(str, Enum):
    """Message type enumeration"""
    USER_INPUT = "user_input"
    AI_RESPONSE = "ai_response"
    SYSTEM = "system"
    PROACTIVE = "proactive"


class ThreadCreateRequest(BaseModel):
    """Request schema for creating new conversation threads"""
    initial_message: Optional[str] = Field(None, description="Optional first message")
    context: Optional[Dict[str, Any]] = Field(None, description="Initial context metadata")
    thread_type: str = Field("conversation", description="Thread type for categorization")
    
    @validator('initial_message')
    def validate_initial_message(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Initial message cannot be empty if provided')
            if len(v) > 10000:  # 10KB limit
                raise ValueError('Initial message too long (max 10KB)')
            return v.strip()
        return v
    
    @validator('thread_type')
    def validate_thread_type(cls, v):
        valid_types = ['conversation', 'support', 'creative', 'technical']
        if v not in valid_types:
            raise ValueError(f'Invalid thread_type. Must be one of: {valid_types}')
        return v


class MessageSendRequest(BaseModel):
    """Request schema for sending messages to threads"""
    message: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 10000:  # 10KB limit
            raise ValueError('Message too long (max 10KB)')
        return v.strip()
    
    @validator('message_type')
    def validate_message_type(cls, v):
        valid_types = ['text', 'audio', 'image', 'multimodal']
        if v not in valid_types:
            raise ValueError(f'Invalid message_type. Must be one of: {valid_types}')
        return v


class ConversationStartRequest(BaseModel):
    """Request to start or continue a conversation"""
    message: str = Field(..., description="Message to send (required)")
    thread_id: Optional[str] = Field(None, description="Optional thread ID to continue existing conversation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for conversation")
    response_mode: Optional[str] = Field("text", description="Response mode: text, multimodal, proactive")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message content is required")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()
    
    @validator('thread_id')
    def validate_thread_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError("Invalid thread ID format")
        return v


class ConversationMessageRequest(BaseModel):
    """Request to send a message in conversation"""
    message: str = Field(..., description="User message content")
    message_type: MessageType = Field(MessageType.USER_INPUT, description="Message type")
    response_mode: Optional[str] = Field("text", description="Response mode: text, multimodal")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional message context")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message content is required")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()


class ThreadResponse(BaseModel):
    """Response schema for thread operations"""
    success: bool = Field(..., description="Operation success status")
    thread_id: str = Field(..., description="Thread identifier")
    status: str = Field(..., description="Thread status")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    message_count: int = Field(0, description="Number of messages in thread")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Thread metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageResponse(BaseModel):
    """Response schema for message operations"""
    success: bool = Field(..., description="Operation success status")
    message_id: str = Field(..., description="Message identifier")
    thread_id: str = Field(..., description="Thread identifier")
    status: str = Field(..., description="Message processing status")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationStatus(BaseModel):
    """Status of a conversation thread"""
    thread_id: str = Field(..., description="Conversation thread ID")
    active: bool = Field(..., description="Whether conversation is active")
    message_count: int = Field(..., description="Number of messages in conversation")
    last_activity: str = Field(..., description="Timestamp of last activity (ISO format)")
    context: Optional[Dict[str, Any]] = Field(None, description="Current conversation context")
    user_id: str = Field(..., description="Owner user ID")


class ConversationListRequest(BaseModel):
    """Request to list conversations"""
    limit: Optional[int] = Field(50, description="Number of conversations to return", ge=1, le=100)
    offset: Optional[int] = Field(0, description="Pagination offset", ge=0)
    active_only: Optional[bool] = Field(True, description="Only return active conversations")
    since: Optional[datetime] = Field(None, description="Show conversations after timestamp")


class ThreadListResponse(BaseModel):
    """Response schema for listing threads"""
    success: bool = Field(..., description="Operation success status")
    threads: List[Dict[str, Any]] = Field(..., description="List of thread summaries")
    total_count: int = Field(..., description="Total number of threads")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of threads per page")


class MessageHistoryResponse(BaseModel):
    """Response for message history retrieval"""
    success: bool
    thread_id: str
    messages: List[Dict[str, Any]]
    total_count: int
    page: int = 1
    page_size: int = 50


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class UnifiedMessageRequest(BaseModel):
    """Request for unified message endpoint with automatic thread resolution"""
    message: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for thread resolution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")


class UnifiedMessageResponse(BaseModel):
    """Response for unified message endpoint"""
    success: bool
    message_id: str
    thread_id: str
    thread_action: str  # "continued", "created", "reactivated"
    thread_reasoning: str
    status: str  # "processing", "queued", "error"
    timestamp: datetime
    ai_response: Optional[str] = Field(None, description="AI response to the message")


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
