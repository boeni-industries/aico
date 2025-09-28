"""
AICO Conversation API Router

Provides REST endpoints for conversation management and integrates with
the message bus for real-time conversation processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query, Request
from fastapi.security import HTTPBearer

from aico.core.logging import get_logger
from backend.api.conversation.dependencies import get_message_bus_client
from backend.api.conversation.dependencies import get_current_user
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_conversation_pb2 import ConversationContext, Context, RecentHistory
from aico.proto.aico_conversation_pb2 import ResponseRequest, ResponseParameters
from google.protobuf.timestamp_pb2 import Timestamp

# Thread access verification removed - Enhanced Semantic Memory handles access automatically
from backend.api.conversation.schemas import (
    ConversationResponse,
    MessageSendRequest, MessageResponse,
    ConversationListResponse, MessageHistoryResponse,
    UnifiedMessageRequest, UnifiedMessageResponse,
    HealthResponse
)
from backend.api.conversation.exceptions import (
    ConversationNotFoundException, InvalidConversationException,
    MessageProcessingException, WebSocketAuthenticationException, MessageBusConnectionException
)

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend", "api.conversation")
security = HTTPBearer()

# Active WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}


# Unified endpoint with automatic thread management

@router.post("/messages", response_model=UnifiedMessageResponse)
async def send_message_with_auto_thread(
    request: UnifiedMessageRequest,
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client)
):
    """Send message with lazy thread resolution via context assembly"""
    try:
        user_id = current_user['user_uuid']
        
        # INDUSTRY STANDARD: conversation_id pattern (user_id + session)
        # This follows LangGraph, Azure AI Foundry, and OpenAI Assistant API patterns
        import time
        session_timestamp = int(time.time())
        conversation_id = f"{user_id}_{session_timestamp}"
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Simple message storage - semantic memory handles continuity (ASYNC - non-blocking)
        try:
            from aico.ai import ai_registry
            memory_processor = ai_registry.get("memory")
            if memory_processor:
                from aico.ai.base import ProcessingContext
                store_context = ProcessingContext(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message_content=request.message,
                    message_type="user_input",
                    turn_number=1,
                    conversation_phase="active"
                )
                # RE-ENABLED - Fire-and-forget background processing - don't block API response
                import asyncio
                asyncio.create_task(memory_processor.process(store_context))
                logger.debug(f"Memory processing started in background for {conversation_id}")
        except Exception as e:
            logger.warning(f"Memory processing failed to start: {e} - continuing without memory storage")
        
        # Create conversation message for message bus
        from google.protobuf.timestamp_pb2 import Timestamp
        
        proto_timestamp = Timestamp()
        proto_timestamp.FromDatetime(timestamp)
        
        conv_message = ConversationMessage(
            timestamp=proto_timestamp,
            source="conversation_api",
            message_id=message_id,
            user_id=user_id
        )
        
        # Update message content
        conv_message.message.text = request.message
        conv_message.message.type = conv_message.message.MessageType.USER_INPUT
        conv_message.message.conversation_id = conversation_id
        conv_message.message.turn_number = 1  # TODO: Track actual turn numbers
        
        # Publish to conversation input topic (ConversationEngine will handle)
        await bus_client.publish("conversation/user/input/v1", conv_message)
        
        # Wait for ConversationEngine to process and get the AI response synchronously
        import asyncio
        
        response_received = asyncio.Event()
        ai_response = "No response received"
        response_conversation_id = None
        
        async def handle_ai_response(envelope):
            try:
                nonlocal ai_response
                logger.debug(f"[API_GATEWAY] Received AI response envelope: {type(envelope)}")
                
                # Extract ConversationMessage from envelope
                conversation_message = ConversationMessage()
                envelope.any_payload.Unpack(conversation_message)
                
                logger.debug(f"[API_GATEWAY] Extracted ConversationMessage: {type(conversation_message)}")
                # Check if this response is for our specific message
                logger.debug(f"[API_GATEWAY] Response message_id: {conversation_message.message_id}, Expected: {message_id}")
                if conversation_message.message_id == message_id:
                    ai_response = conversation_message.message.text
                    logger.info(f"[API_GATEWAY] ✅ AI response extracted for message_id {message_id}: '{ai_response[:100]}...'")
                    response_received.set()
                else:
                    logger.debug(f"[API_GATEWAY] Message ID mismatch (got: {conversation_message.message_id}, expected: {message_id}), ignoring response")
                    
            except Exception as e:
                logger.error(f"Error handling AI response: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Subscribe to AI response topic
        await bus_client.subscribe("conversation/ai/response/v1", handle_ai_response)
        
        # Wait for response with timeout (allow for unoptimized LLM processing)
        try:
            logger.info(f"🔍 [CONVERSATION_TIMEOUT] Waiting for response with 15s timeout for request: {message_id}")
            await asyncio.wait_for(response_received.wait(), timeout=15.0)
            logger.info(f"🔍 [CONVERSATION_TIMEOUT] ✅ Response received within timeout for request: {message_id}")
        except asyncio.TimeoutError:
            logger.error(f"🔍 [CONVERSATION_TIMEOUT] ❌ 15-SECOND TIMEOUT for request: {message_id}")
            ai_response = "Request timed out - please try again"
        finally:
            # Unsubscribe from the topic
            try:
                await bus_client.unsubscribe("conversation/ai/response/v1")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")
        
        
        # Return response with actual AI reply
        response_data = UnifiedMessageResponse(
            success=True,
            message_id=message_id,
            conversation_id=conversation_id,
            conversation_action="conversation_started",
            conversation_reasoning="Conversation continuity handled via enhanced semantic memory",
            status="completed",
            ai_response=ai_response,
            timestamp=timestamp.isoformat()
        )
        
        return response_data
    except Exception as e:
        logger.error(f"Failed to send message with auto-thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


# User-scoped endpoints - no thread management needed with semantic memory

@router.get("/messages", response_model=MessageHistoryResponse)
async def get_my_messages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Messages per page"),
    since: Optional[datetime] = Query(None, description="Show messages after this timestamp"),
    current_user = Depends(get_current_user)
):
    """
    Get my message history (user-scoped)
    
    Returns paginated message history for the authenticated user.
    Semantic memory provides context continuity without explicit thread management.
    """
    try:
        user_id = current_user['user_uuid']
        
        # TODO: Retrieve user's messages from semantic memory system
        # This would query the working memory and semantic memory stores
        # for messages belonging to this user, with time-based pagination
        
        return MessageHistoryResponse(
            success=True,
            messages=[],
            conversation_id=f"user_{user_id}",  # User-scoped identifier
            total_count=0,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to get user message history: {e}", extra={
            "user_id": current_user.get('user_uuid', 'unknown'),
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve message history"
        )


@router.get("/status")
async def get_my_conversation_status(
    current_user = Depends(get_current_user)
):
    """
    Get my conversation status (user-scoped)
    
    Returns conversation activity and status for the authenticated user.
    Semantic memory provides context without explicit thread management.
    """
    try:
        user_id = current_user['user_uuid']
        
        logger.info(f"Getting conversation status for user: {user_id}")
        
        # TODO: Get user's conversation status from semantic memory system
        # This would query working memory and semantic memory for user activity
        
        return {
            "success": True,
            "user_id": user_id,
            "active_conversations": 0,  # From semantic memory
            "total_messages": 0,       # From working memory
            "last_activity": None,     # From recent messages
            "status": "ready"
        }
        
    except Exception as e:
        logger.error(f"Failed to get user conversation status: {e}", extra={
            "user_id": current_user['user_uuid'],
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation status"
        )


@router.websocket("/ws")
async def my_conversation_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time conversation updates (user-scoped)
    
    Provides real-time delivery of AI responses and conversation events
    for the authenticated user. No thread management needed.
    """
    # TODO: Add WebSocket authentication to get user_id
    # For now, accept connection without auth (security risk)
    await websocket.accept()
    connection_id = f"user_{uuid.uuid4()}"  # User-scoped connection
    active_connections[connection_id] = websocket
    
    logger.info(f"WebSocket connection established", extra={
        "connection_id": connection_id
    })
    
    try:
        # Create message bus client to listen for responses
        bus_client = MessageBusClient(f"conversation_ws_{connection_id}")
        await bus_client.connect()
        
        # Subscribe to conversation responses for this user
        async def response_handler(topic: str, message: Any):
            """Handle incoming conversation responses"""
            try:
                # TODO: Filter by user_id instead of conversation_id once WebSocket auth is implemented
                if hasattr(message, 'message') and hasattr(message.message, 'text'):
                    # Create structured WebSocket response
                    ai_response = WebSocketAIResponse(
                        conversation_id=f"user_conversation_{connection_id}",
                        message_id=str(uuid.uuid4()),
                        message=message.message.text,
                        confidence=getattr(message, 'confidence', None),
                        processing_time_ms=getattr(message, 'processing_time_ms', None)
                    )
                    
                    await websocket.send_json(ai_response.dict())
                    
                    logger.info(f"Sent AI response via WebSocket", extra={
                        "connection_id": connection_id
                    })
            except Exception as e:
                logger.error(f"Error handling response: {e}", extra={
                    "connection_id": connection_id
                })
                # Send error to client
                error_response = WebSocketError(
                    error_code="RESPONSE_PROCESSING_ERROR",
                    error_message=str(e),
                    conversation_id=f"user_conversation_{connection_id}"
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
                    "connection_id": connection_id
                })
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}", extra={
            "connection_id": connection_id
        })
        raise WebSocketConnectionException(
            connection_error=str(e),
            connection_id=connection_id
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
            "connection_id": connection_id
        })


@router.post("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for conversation service"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


# Legacy endpoint support (deprecated)
@router.post("/start", response_model=UnifiedMessageResponse, deprecated=True)
async def start_conversation_legacy(
    request: UnifiedMessageRequest,
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client)
):
    """Legacy start endpoint - redirects to unified messages endpoint"""
    logger.warning("Using deprecated /start endpoint - use /messages instead")
    return await send_message_with_auto_thread(request, current_user, bus_client)
