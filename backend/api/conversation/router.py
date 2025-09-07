"""
AICO Conversation API Router

Provides REST endpoints for conversation management and integrates with
the message bus for real-time conversation processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_conversation_pb2 import ConversationContext, Context, RecentHistory
from aico.proto.aico_conversation_pb2 import ResponseRequest, ResponseParameters
from google.protobuf.timestamp_pb2 import Timestamp

from ..dependencies import verify_user_token, get_current_user

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend", "api.conversation")
security = HTTPBearer()

# Active WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}

# Pydantic models for API requests/responses
class ConversationStartRequest(BaseModel):
    """Request to start a new conversation"""
    initial_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ConversationMessageRequest(BaseModel):
    """Request to send a message in conversation"""
    thread_id: str = Field(..., description="Conversation thread ID")
    message: str = Field(..., description="User message content")
    message_type: str = Field(default="user_input", description="Message type")

class ConversationResponse(BaseModel):
    """Response from conversation API"""
    success: bool
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None

class ConversationStatus(BaseModel):
    """Status of a conversation thread"""
    thread_id: str
    active: bool
    message_count: int
    last_activity: datetime
    context: Optional[Dict[str, Any]] = None

@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: ConversationStartRequest,
    current_user = Depends(get_current_user)
):
    """
    Start a new conversation thread
    
    Creates a new conversation thread and optionally processes an initial message.
    Returns the thread ID for subsequent message exchanges.
    """
    try:
        # Generate new thread ID
        thread_id = str(uuid.uuid4())
        
        logger.info(f"Starting new conversation thread: {thread_id}", extra={
            "user_id": current_user.user_uuid,
            "thread_id": thread_id
        })
        
        # Create message bus client for this conversation
        bus_client = MessageBusClient(f"conversation_api_{thread_id}")
        await bus_client.connect()
        
        # If initial message provided, process it
        response_text = None
        message_id = None
        
        if request.initial_message:
            message_id = str(uuid.uuid4())
            
            # Create conversation message protobuf
            conv_message = ConversationMessage()
            conv_message.timestamp.GetCurrentTime()
            conv_message.source = current_user.user_uuid
            
            # Set message content
            conv_message.message.text = request.initial_message
            conv_message.message.type = Message.MessageType.USER_INPUT
            conv_message.message.thread_id = thread_id
            conv_message.message.turn_number = 1
            
            # Set message analysis
            conv_message.analysis.intent = "conversation_start"
            conv_message.analysis.urgency = MessageAnalysis.Urgency.MEDIUM
            conv_message.analysis.requires_response = True
            
            # Publish to message bus
            await bus_client.publish(
                AICOTopics.CONVERSATION_USER_INPUT,
                conv_message
            )
            
            logger.info(f"Published initial message to conversation bus", extra={
                "thread_id": thread_id,
                "message_id": message_id,
                "topic": AICOTopics.CONVERSATION_USER_INPUT
            })
            
            # For now, return acknowledgment (real response will come via WebSocket)
            response_text = "Message received and processing started"
        
        await bus_client.disconnect()
        
        return ConversationResponse(
            success=True,
            thread_id=thread_id,
            message_id=message_id,
            response=response_text
        )
        
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}", extra={
            "user_id": getattr(current_user, 'user_uuid', 'unknown'),
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to start conversation: {str(e)}")

@router.post("/message", response_model=ConversationResponse)
async def send_message(
    request: ConversationMessageRequest,
    current_user = Depends(get_current_user)
):
    """
    Send a message in an existing conversation thread
    
    Processes the user message through the conversation engine and
    returns acknowledgment. Real-time response delivered via WebSocket.
    """
    try:
        message_id = str(uuid.uuid4())
        
        logger.info(f"Processing message in thread: {request.thread_id}", extra={
            "user_id": current_user.user_uuid,
            "thread_id": request.thread_id,
            "message_id": message_id
        })
        
        # Create message bus client
        bus_client = MessageBusClient(f"conversation_api_{request.thread_id}")
        await bus_client.connect()
        
        # Create conversation message protobuf
        conv_message = ConversationMessage()
        conv_message.timestamp.GetCurrentTime()
        conv_message.source = current_user.user_uuid
        
        # Set message content
        conv_message.message.text = request.message
        conv_message.message.type = getattr(Message.MessageType, request.message_type.upper(), Message.MessageType.USER_INPUT)
        conv_message.message.thread_id = request.thread_id
        conv_message.message.turn_number = 0  # Will be set by conversation engine
        
        # Set message analysis (basic for now)
        conv_message.analysis.intent = "user_message"
        conv_message.analysis.urgency = MessageAnalysis.Urgency.MEDIUM
        conv_message.analysis.requires_response = True
        
        # Publish to message bus
        await bus_client.publish(
            AICOTopics.CONVERSATION_USER_INPUT,
            conv_message
        )
        
        await bus_client.disconnect()
        
        logger.info(f"Published message to conversation bus", extra={
            "thread_id": request.thread_id,
            "message_id": message_id,
            "topic": AICOTopics.CONVERSATION_USER_INPUT
        })
        
        return ConversationResponse(
            success=True,
            thread_id=request.thread_id,
            message_id=message_id,
            response="Message received and processing started"
        )
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}", extra={
            "user_id": current_user.user_uuid,
            "thread_id": request.thread_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/status/{thread_id}", response_model=ConversationStatus)
async def get_conversation_status(
    thread_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get status of a conversation thread
    
    Returns current status, message count, and context information
    for the specified conversation thread.
    """
    try:
        # For now, return basic status (would query conversation engine in full implementation)
        return ConversationStatus(
            thread_id=thread_id,
            active=True,
            message_count=0,  # Would be retrieved from conversation engine
            last_activity=datetime.utcnow(),
            context={"status": "active", "user_id": current_user.user_uuid}
        )
        
    except Exception as e:
        logger.error(f"Failed to get conversation status: {e}", extra={
            "user_id": current_user.user_uuid,
            "thread_id": thread_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get conversation status: {str(e)}")

@router.websocket("/ws/{thread_id}")
async def conversation_websocket(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time conversation updates
    
    Provides real-time delivery of AI responses and conversation events
    for the specified thread ID.
    """
    await websocket.accept()
    connection_id = f"{thread_id}_{uuid.uuid4()}"
    active_connections[connection_id] = websocket
    
    logger.info(f"WebSocket connection established", extra={
        "thread_id": thread_id,
        "connection_id": connection_id
    })
    
    try:
        # Create message bus client to listen for responses
        bus_client = MessageBusClient(f"conversation_ws_{connection_id}")
        await bus_client.connect()
        
        # Subscribe to conversation responses for this thread
        async def response_handler(topic: str, message: Any):
            """Handle incoming conversation responses"""
            try:
                if hasattr(message, 'message') and hasattr(message.message, 'thread_id'):
                    if message.message.thread_id == thread_id:
                        # Send response to WebSocket client
                        response_data = {
                            "type": "ai_response",
                            "thread_id": thread_id,
                            "message": message.message.text,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_json(response_data)
                        
                        logger.info(f"Sent AI response via WebSocket", extra={
                            "thread_id": thread_id,
                            "connection_id": connection_id
                        })
            except Exception as e:
                logger.error(f"Error handling response: {e}", extra={
                    "thread_id": thread_id,
                    "connection_id": connection_id
                })
        
        # Subscribe to AI responses
        await bus_client.subscribe(AICOTopics.CONVERSATION_AI_RESPONSE, response_handler)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (heartbeat, etc.)
                data = await websocket.receive_json()
                
                if data.get("type") == "heartbeat":
                    await websocket.send_json({"type": "heartbeat_ack"})
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}", extra={
                    "thread_id": thread_id,
                    "connection_id": connection_id
                })
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}", extra={
            "thread_id": thread_id,
            "connection_id": connection_id
        })
    
    finally:
        # Cleanup
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        try:
            if 'bus_client' in locals():
                await bus_client.disconnect()
        except:
            pass
        
        logger.info(f"WebSocket connection closed", extra={
            "thread_id": thread_id,
            "connection_id": connection_id
        })

@router.get("/health")
async def conversation_health():
    """Health check endpoint for conversation API"""
    return {
        "status": "healthy",
        "active_connections": len(active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }
