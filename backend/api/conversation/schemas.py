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


# ThreadCreateRequest removed - conversations are created implicitly with first message
# Semantic memory handles context continuity without explicit thread creation


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
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID to continue existing conversation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for conversation")
    response_mode: Optional[str] = Field("text", description="Response mode: text, multimodal, proactive")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message content is required")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if v is not None and len(v.strip()) > 255:
            raise ValueError("Conversation ID too long (max 255 characters)")
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


class ConversationResponse(BaseModel):
    """Response schema for conversation operations"""
    success: bool = Field(..., description="Operation success status")
    conversation_id: str = Field(..., description="Conversation identifier")
    status: str = Field(..., description="Conversation status")
    created_at: datetime = Field(..., description="Conversation creation timestamp")
    message_count: int = Field(0, description="Number of messages in conversation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Conversation metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageResponse(BaseModel):
    """Response schema for message operations"""
    success: bool = Field(..., description="Operation success status")
    message_id: str = Field(..., description="Message identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    status: str = Field(..., description="Message processing status")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationStatus(BaseModel):
    """Status of a conversation"""
    conversation_id: str = Field(..., description="Conversation ID")
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


class ConversationListResponse(BaseModel):
    """Response schema for listing conversations"""
    success: bool = Field(..., description="Operation success status")
    conversations: List[Dict[str, Any]] = Field(..., description="List of conversation summaries")
    total_count: int = Field(..., description="Total number of conversations")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of conversations per page")


class MessageHistoryResponse(BaseModel):
    """Response for message history retrieval"""
    success: bool
    conversation_id: str
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
    conversation_id: str
    conversation_action: str  # "continued", "created", "reactivated"
    conversation_reasoning: str
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
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="AI message ID")
    message: str = Field(..., description="AI response text")
    confidence: Optional[float] = Field(None, description="Response confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class WebSocketError(WebSocketMessage):
    """Error message via WebSocket"""
    type: WebSocketMessageType = Field(WebSocketMessageType.ERROR, description="Message type")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    conversation_id: Optional[str] = Field(None, description="Related conversation ID if applicable")


class WebSocketStatusUpdate(WebSocketMessage):
    """Status update via WebSocket"""
    type: WebSocketMessageType = Field(WebSocketMessageType.STATUS_UPDATE, description="Message type")
    conversation_id: str = Field(..., description="Conversation ID")
    status: str = Field(..., description="New status")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")


# Protobuf Conversion Schemas
class ProtobufConversationMessage(BaseModel):
    """Schema for converting to/from protobuf ConversationMessage"""
    timestamp: datetime = Field(..., description="Message timestamp")
    source: str = Field(..., description="Message source (user ID)")
    text: str = Field(..., description="Message text content")
    message_type: MessageType = Field(..., description="Message type")
    conversation_id: str = Field(..., description="Conversation ID")
    turn_number: int = Field(..., description="Turn number in conversation")
    intent: Optional[str] = Field(None, description="Detected intent")
    urgency: Optional[str] = Field("medium", description="Message urgency level")
    requires_response: bool = Field(True, description="Whether message requires response")


class ConversationHealthResponse(BaseModel):
    """Health check response for conversation API"""
    status: str = Field(..., description="Service status")
    active_connections: int = Field(..., description="Number of active WebSocket connections")
    active_conversations: int = Field(0, description="Number of active conversations")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field("1.0.0", description="API version")
