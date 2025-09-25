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
from backend.services.thread_manager_integration import get_aico_thread_manager
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_conversation_pb2 import ConversationContext, Context, RecentHistory
from aico.proto.aico_conversation_pb2 import ResponseRequest, ResponseParameters
from google.protobuf.timestamp_pb2 import Timestamp

from .dependencies import verify_thread_access
from backend.api.conversation.schemas import (
    ThreadCreateRequest, ThreadResponse,
    MessageSendRequest, MessageResponse,
    ThreadListResponse, MessageHistoryResponse,
    UnifiedMessageRequest, UnifiedMessageResponse,
    HealthResponse
)
from backend.api.conversation.exceptions import (
    ConversationNotFoundException, InvalidThreadException, ThreadAccessDeniedException,
    MessageProcessingException, WebSocketAuthenticationException, MessageBusConnectionException
)

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend", "api.conversation")
security = HTTPBearer()

# Active WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}


# Unified endpoint with automatic thread management
def get_service_container(request: Request):
    """Dependency to get the service container from FastAPI app state"""
    return request.app.state.service_container

@router.post("/messages", response_model=UnifiedMessageResponse)
async def send_message_with_auto_thread(
    request: UnifiedMessageRequest,
    current_user = Depends(get_current_user),
    thread_manager = Depends(get_aico_thread_manager),
    bus_client = Depends(get_message_bus_client),
    container = Depends(get_service_container)
):
    """Send message with automatic thread resolution (primary endpoint)"""
    try:
        user_id = current_user['user_uuid']
        
        # Automatic thread resolution
        thread_resolution = await thread_manager.resolve_thread_for_message(
            user_id=user_id,
            message=request.message,
            context=request.context
        )
        
        # Generate message ID and timestamp
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
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
        
        # Process message through message bus (proper architecture)
        logger.info(f"[DEBUG] Processing message via message bus for thread {thread_resolution.thread_id}")
        
        # Update the existing conv_message with proper content
        conv_message.message.text = request.message
        # Set message type using the enum value
        if request.message_type == "text" or not request.message_type:
            conv_message.message.type = conv_message.message.MessageType.USER_INPUT
        else:
            conv_message.message.type = conv_message.message.MessageType.USER_INPUT
        conv_message.message.thread_id = thread_resolution.thread_id
        conv_message.message.turn_number = 1  # TODO: Track actual turn numbers
        
        # Publish to conversation input topic (ConversationEngine will handle)
        await bus_client.publish("conversation/user/input/v1", conv_message)
        
        # Wait for ConversationEngine to process and get the AI response synchronously
        import asyncio
        
        response_received = asyncio.Event()
        ai_response = "No response received"
        response_thread_id = None
        
        async def handle_ai_response(envelope):
            try:
                nonlocal ai_response
                logger.debug(f"[API_GATEWAY] Received AI response envelope: {type(envelope)}")
                
                # Extract ConversationMessage from envelope
                conversation_message = ConversationMessage()
                envelope.any_payload.Unpack(conversation_message)
                
                logger.debug(f"[API_GATEWAY] Extracted ConversationMessage: {type(conversation_message)}")
                logger.debug(f"[API_GATEWAY] Response thread_id: {conversation_message.message.thread_id}, expected: {thread_resolution.thread_id}")
                
                # Check if this response is for our thread
                if conversation_message.message.thread_id == thread_resolution.thread_id:
                    ai_response = conversation_message.message.text
                    logger.info(f"[API_GATEWAY] ✅ AI response extracted: '{ai_response[:100]}...'")
                    response_received.set()
                else:
                    logger.debug(f"[API_GATEWAY] Thread ID mismatch, ignoring response")
                    
            except Exception as e:
                logger.error(f"Error handling AI response: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Subscribe to AI response topic
        await bus_client.subscribe("conversation/ai/response/v1", handle_ai_response)
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            ai_response = "Request timed out - please try again"
        finally:
            # Unsubscribe from the topic
            try:
                await bus_client.unsubscribe("conversation/ai/response/v1")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")
        
        logger.info(f"Auto-resolved message {message_id} to thread {thread_resolution.thread_id} (action: {thread_resolution.action})")
        
        # Return response with actual AI reply
        response_data = UnifiedMessageResponse(
            success=True,
            message_id=message_id,
            thread_id=thread_resolution.thread_id,
            thread_action=thread_resolution.action,
            thread_reasoning=thread_resolution.reasoning,
            status="completed",
            timestamp=timestamp,
            ai_response=ai_response
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to send message with auto-thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: ThreadCreateRequest,
    current_user = Depends(get_current_user),
    thread_manager = Depends(get_aico_thread_manager),
    bus_client = Depends(get_message_bus_client)
):
    """Create a new conversation thread explicitly (advanced endpoint)"""
    try:
        user_id = current_user['user_uuid']
        
        # Create explicit thread via ThreadManager
        thread_resolution = await thread_manager.create_explicit_thread(
            user_id=user_id,
            thread_type=request.thread_type,
            initial_message=request.initial_message,
            context=request.context
        )
        
        # If initial message provided, send it to the thread
        if request.initial_message:
            message_id = str(uuid.uuid4())
            
            proto_timestamp = Timestamp()
            proto_timestamp.FromDatetime(thread_resolution.created_at)
            
            conv_message = ConversationMessage(
                timestamp=proto_timestamp,
                source="conversation_api",
                message_id=message_id,
                user_id=user_id
            )
            
            # Publish to message bus for async processing
            await bus_client.publish(
                "conversation/user/input",
                conv_message
            )
            
            logger.info(f"Published initial message {message_id} to explicit thread {thread_resolution.thread_id}")
        
        return ThreadResponse(
            success=True,
            thread_id=thread_resolution.thread_id,
            status="created",
            created_at=thread_resolution.created_at,
            message_count=1 if request.initial_message else 0
        )
        
    except Exception as e:
        logger.error(f"Failed to create explicit thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread")


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def send_message_to_thread(
    thread_id: str,
    request: MessageSendRequest,
    current_user = Depends(get_current_user),
    thread_manager = Depends(get_aico_thread_manager),
    bus_client = Depends(get_message_bus_client)
):
    """Send a message to a specific thread (advanced endpoint)"""
    try:
        user_id = current_user['user_uuid']
        
        # Validate thread access
        if not await thread_manager.validate_thread_access(thread_id, user_id):
            raise HTTPException(status_code=403, detail="Thread access denied")
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        proto_timestamp = Timestamp()
        proto_timestamp.FromDatetime(timestamp)
        
        conv_message = ConversationMessage(
            timestamp=proto_timestamp,
            source="conversation_api",
            message_id=message_id,
            user_id=user_id
        )
        
        # Publish to message bus for async processing
        await bus_client.publish(
            "conversation/user/input",
            conv_message
        )
        
        logger.info(f"Published message {message_id} to explicit thread {thread_id}")
        
        return MessageResponse(
            success=True,
            message_id=message_id,
            thread_id=thread_id,
            status="processing",
            timestamp=timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message to thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    current_user = Depends(get_current_user),
    thread_manager = Depends(get_aico_thread_manager)
):
    """Get thread metadata and status"""
    try:
        user_id = current_user['user_uuid']
        
        # Validate thread access
        if not await thread_manager.validate_thread_access(thread_id, user_id):
            raise HTTPException(status_code=403, detail="Thread access denied")
        
        # Get thread info
        thread_info = await thread_manager.get_thread_info(thread_id, user_id)
        if not thread_info:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return ThreadResponse(
            success=True,
            thread_id=thread_info.thread_id,
            status=thread_info.status,
            created_at=datetime.utcnow(),  # TODO: Use actual creation time from thread_info
            message_count=thread_info.message_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread")


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    current_user = Depends(get_current_user),
    thread_manager = Depends(get_aico_thread_manager),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """List user's conversation threads"""
    try:
        user_id = current_user['user_uuid']
        
        # TODO: Implement actual thread listing via ThreadManager
        # For now, return empty list
        
        return ThreadListResponse(
            success=True,
            threads=[],
            total_count=0,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list threads for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list threads")


@router.get("/threads/{thread_id}/messages", response_model=MessageHistoryResponse)
async def get_message_history(
    thread_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Messages per page"),
    current_user = Depends(get_current_user)
):
    """
    Get message history for a thread
    
    Returns paginated message history with metadata.
    """
    try:
        # Validate thread ID format
        try:
            uuid.UUID(thread_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid thread ID format"
            )
        
        # TODO: Retrieve messages from database with pagination
        # For now, return mock data
        
        return MessageHistoryResponse(
            success=True,
            messages=[],
            thread_id=thread_id,
            total_count=0,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message history: {e}", extra={
            "user_id": current_user.get('user_uuid', 'unknown'),
            "thread_id": thread_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get message history: {str(e)}"
        )


@router.post("/status/{thread_id}")
async def get_conversation_status(
    thread_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get status of a conversation thread
    
    TODO: Implement real status logic by connecting to ConversationEngine service
    - Access conversation_threads from ConversationEngine via service container
    - Return actual message_count from thread.message_history
    - Return real conversation_phase, current_topic, turn_number
    - Return actual last_activity timestamp
    """
    try:
        logger.info(f"Getting status for thread: {thread_id}", extra={
            "user_id": current_user['user_uuid'],
            "thread_id": thread_id
        })
        
        # Return placeholder response indicating not implemented
        return {
            "success": True,
            "message": "Status endpoint logic not implemented yet.",
            "thread_id": thread_id,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to get conversation status: {e}", extra={
            "user_id": current_user['user_uuid'],
            "thread_id": thread_id,
            "error": str(e)
        })
        raise ConversationNotFoundException(thread_id=thread_id, user_id=current_user['user_uuid'])


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
    thread_manager = Depends(get_aico_thread_manager),
    bus_client = Depends(get_message_bus_client)
):
    """Legacy start endpoint - redirects to unified messages endpoint"""
    logger.warning("Using deprecated /start endpoint - use /messages instead")
    return await send_message_with_auto_thread(request, current_user, thread_manager, bus_client)
