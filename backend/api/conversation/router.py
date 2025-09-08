"""
AICO Conversation API Router

Provides REST endpoints for conversation management and integrates with
the message bus for real-time conversation processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_conversation_pb2 import ConversationContext, Context, RecentHistory
from aico.proto.aico_conversation_pb2 import ResponseRequest, ResponseParameters
from google.protobuf.timestamp_pb2 import Timestamp

from .dependencies import get_current_user, verify_thread_access, get_message_bus_client
from .schemas import (
    ConversationStartRequest, ConversationMessageRequest, ConversationResponse,
    ConversationStatus, ConversationHealthResponse, WebSocketAIResponse,
    WebSocketError, WebSocketMessageType, MessageType
)
from .exceptions import (
    ConversationNotFoundException, InvalidThreadException, ThreadAccessDeniedException,
    MessageProcessingException, WebSocketAuthenticationException, MessageBusConnectionException
)

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend", "api.conversation")
security = HTTPBearer()

# Active WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}


@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: ConversationStartRequest,
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client)
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
        raise MessageProcessingException(
            message=request.initial_message or "[no initial message]",
            user_id=current_user.user_uuid,
            processing_error=str(e)
        )

@router.post("/message", response_model=ConversationResponse)
async def send_message(
    request: ConversationMessageRequest,
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client),
    thread_access = Depends(verify_thread_access)
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
        
        # Create conversation message protobuf
        conv_message = ConversationMessage()
        conv_message.timestamp.GetCurrentTime()
        conv_message.source = current_user.user_uuid
        
        # Set message content
        conv_message.message.text = request.message
        # Convert schema enum to protobuf enum
        if request.message_type == MessageType.USER_INPUT:
            conv_message.message.type = Message.MessageType.USER_INPUT
        elif request.message_type == MessageType.SYSTEM:
            conv_message.message.type = Message.MessageType.SYSTEM
        else:
            conv_message.message.type = Message.MessageType.USER_INPUT
            
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
        raise MessageProcessingException(
            message=request.message,
            thread_id=request.thread_id,
            user_id=current_user.user_uuid,
            processing_error=str(e)
        )

@router.get("/status/{thread_id}", response_model=ConversationStatus)
async def get_conversation_status(
    thread_id: str,
    current_user = Depends(get_current_user),
    thread_access = Depends(verify_thread_access)
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
            context={"status": "active"},
            user_id=current_user.user_uuid
        )
        
    except Exception as e:
        logger.error(f"Failed to get conversation status: {e}", extra={
            "user_id": current_user.user_uuid,
            "thread_id": thread_id,
            "error": str(e)
        })
        raise ConversationNotFoundException(thread_id=thread_id, user_id=current_user.user_uuid)

@router.websocket("/ws/{thread_id}")
async def conversation_websocket(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time conversation updates
    
    Provides real-time delivery of AI responses and conversation events
    for the specified thread ID.
    """
    # TODO: Add WebSocket authentication
    # For now, accept connection without auth (security risk)
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
                        # Create structured WebSocket response
                        ai_response = WebSocketAIResponse(
                            thread_id=thread_id,
                            message_id=str(uuid.uuid4()),
                            message=message.message.text,
                            confidence=getattr(message, 'confidence', None),
                            processing_time_ms=getattr(message, 'processing_time_ms', None)
                        )
                        
                        await websocket.send_json(ai_response.dict())
                        
                        logger.info(f"Sent AI response via WebSocket", extra={
                            "thread_id": thread_id,
                            "connection_id": connection_id
                        })
            except Exception as e:
                logger.error(f"Error handling response: {e}", extra={
                    "thread_id": thread_id,
                    "connection_id": connection_id
                })
                # Send error to client
                error_response = WebSocketError(
                    error_code="RESPONSE_PROCESSING_ERROR",
                    error_message=str(e),
                    thread_id=thread_id
                )
                try:
                    await websocket.send_json(error_response.dict())
                except:
                    pass
        
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
        raise WebSocketConnectionException(
            connection_error=str(e),
            thread_id=thread_id
        )
    
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

@router.get("/health", response_model=ConversationHealthResponse)
async def conversation_health():
    """Health check endpoint for conversation API"""
    return ConversationHealthResponse(
        status="healthy",
        active_connections=len(active_connections),
        active_threads=len(set(conn_id.split('_')[0] for conn_id in active_connections.keys()))
    )
