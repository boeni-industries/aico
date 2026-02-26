"""
AICO Conversation API Router

Provides REST endpoints for conversation management and integrates with
the message bus for real-time conversation processing.
"""

import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
import json

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from backend.api.conversation.dependencies import get_message_bus_client
from backend.api.dependencies import authenticate_websocket, get_current_user
from backend.api.errors import error_responses, raise_api_error
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
    MessageProcessingException, WebSocketAuthenticationException, MessageBusConnectionException,
    ConversationTimeoutException
)

from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork


_conversation_config = None


def _get_conversation_timeout_seconds() -> float:
    global _conversation_config
    if _conversation_config is None:
        _conversation_config = ConfigurationManager()
        _conversation_config.initialize(lightweight=True)
    value = _conversation_config.get("conversation.response_timeout_seconds", 15.0)
    try:
        return float(value)
    except Exception:
        return 15.0

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend.api.conversation")
security = HTTPBearer()

# Active WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}

# Unified endpoint with automatic thread management
@router.post(
    "/messages",
    responses=error_responses(400, 401, 403, 408, 409, 422, 500),
)
async def send_message_with_auto_thread(
    request: UnifiedMessageRequest,
    raw_request: Request,
    stream: str = Query("false", description="Enable streaming response"),
    current_user = Depends(get_current_user),
    bus_client = Depends(get_message_bus_client)
):
    logger.debug(f"🔥 [API_ENDPOINT] /conversation/messages called with stream='{stream}'")
    """Send message with lazy thread resolution via context assembly. Supports streaming with ?stream=true"""
    try:
        logger.debug(f"🔍 [API_DEBUG] Received request with stream parameter: '{stream}' (type: {type(stream)})")
        user_id = current_user['user_uuid']
        tenant_id = current_user["tenant_id"]
        
        # INDUSTRY STANDARD: conversation_id pattern (user_id + session)
        # This follows LangGraph, Azure AI Foundry, and OpenAI Assistant API patterns
        # Use conversation_id from request if provided and valid, otherwise create new session
        request_conversation_id = getattr(request, 'conversation_id', None)
        logger.debug(f"🔍 [CONVERSATION_ID] Request conversation_id: '{request_conversation_id}'")
        
        if (hasattr(request, 'conversation_id') and 
            request.conversation_id and 
            request.conversation_id != 'default' and
            '_' in request.conversation_id):
            conversation_id = request.conversation_id
            logger.debug(f"🔍 [CONVERSATION_ID] ✅ Reusing existing conversation_id: '{conversation_id}'")
        else:
            # Create new conversation session (only for first message)
            import time
            session_timestamp = int(time.time())
            conversation_id = f"{user_id}_{session_timestamp}"
            logger.debug(f"🔍 [CONVERSATION_ID] ✅ Generated new conversation_id: '{conversation_id}'")
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC)

        request_id = raw_request.headers.get("Idempotency-Key") or message_id
        
        # Memory processing now handled by conversation engine - no duplicate background processing needed
        logger.debug(f"Memory processing will be handled by conversation engine for {conversation_id}")
        
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
        await bus_client.publish(
            AICOTopics.CONVERSATION_USER_INPUT,
            conv_message,
            correlation_id=message_id,
            attributes={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "request_id": request_id,
            },
        )
        
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
                    # Strip thinking tags from response (non-streaming path)
                    import re
                    raw_response = conversation_message.message.text
                    ai_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
                    logger.debug(f"[API_GATEWAY] ✅ AI response extracted for message_id {message_id}: '{ai_response[:100]}...'")
                    response_received.set()
                else:
                    logger.debug(f"[API_GATEWAY] Message ID mismatch (got: {conversation_message.message_id}, expected: {message_id}), ignoring response")
                    
            except Exception as e:
                logger.error(f"Error handling AI response: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Handle streaming vs non-streaming response
        # Convert string parameter to boolean
        stream_enabled = stream.lower() in ('true', '1', 'yes', 'on')
        logger.debug(f"🔍 [API_STREAMING] Stream parameter: '{stream}' -> {stream_enabled} for request {message_id}")
        if stream_enabled:
            logger.debug(f"🔍 [API_STREAMING] ✅ Taking streaming path for request {message_id}")

            # Return streaming response using event-driven approach
            async def stream_generator():
                logger.debug(f"🔍 [API_STREAMING] 🚀 Stream generator started for {message_id}")
                try:
                    # Send initial metadata
                    logger.debug(f"🔍 [API_STREAMING] 📤 Yielding metadata for {message_id}")
                    metadata = {
                        "type": "metadata",
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "timestamp": timestamp.isoformat()
                    }

                    # NOTE: Transport encryption for streaming is handled by EncryptionMiddleware.
                    yield json.dumps(metadata) + "\n"
                    
                    # Subscribe to streaming chunks from conversation engine
                    from aico.core.topics import AICOTopics
                    from aico.proto.aico_conversation_pb2 import StreamingResponse as StreamingResponseProto
                    
                    streaming_complete = asyncio.Event()
                    chunk_queue = asyncio.Queue()
                    
                    logger.info(f"🔍 [API_STREAMING] 🎯 About to subscribe to {AICOTopics.CONVERSATION_STREAM} for message_id={message_id}")
                    
                    async def handle_streaming_chunk(envelope):
                        try:
                            logger.info(f"🔍 [API_STREAMING] 📨 Received envelope for streaming")
                            # Extract StreamingResponse from protobuf envelope
                            streaming_chunk = StreamingResponseProto()
                            envelope.any_payload.Unpack(streaming_chunk)
                            
                            logger.info(f"🔍 [API_STREAMING] 📦 Chunk request_id={streaming_chunk.request_id}, expected={message_id}")
                            
                            # Only process chunks for our specific request
                            if streaming_chunk.request_id != message_id:
                                logger.info(f"🔍 [API_STREAMING] ⏭️ Skipping chunk (not for us)")
                                return  # Not for us, continue listening
                            
                            logger.info(f"🔍 [API_STREAMING] 📦 Received chunk for {message_id}: '{streaming_chunk.content}' (done: {streaming_chunk.done})")
                            
                            # Put chunk in queue for immediate processing
                            await chunk_queue.put({
                                "content": streaming_chunk.content,
                                "accumulated": streaming_chunk.accumulated_content,
                                "done": streaming_chunk.done,
                                "content_type": streaming_chunk.content_type  # Forward content_type from backend
                            })
                            
                            # If this is the final chunk, signal completion
                            if streaming_chunk.done:
                                streaming_complete.set()
                            
                        except Exception as e:
                            logger.error(f"Error processing streaming chunk: {e}")
                            await chunk_queue.put({
                                "type": "error",
                                "error": str(e)
                            })
                            streaming_complete.set()
                    
                    # Subscribe to conversation streaming topic
                    await bus_client.subscribe(AICOTopics.CONVERSATION_STREAM, handle_streaming_chunk)
                    
                    # Process chunks from queue as they arrive - truly event-driven
                    timeout_start = asyncio.get_event_loop().time()
                    logger.info(f"🔍 [API_STREAMING] 🎬 Starting streaming loop for {message_id}")
                    logger.info(f"🔍 [API_STREAMING] streaming_complete.is_set() = {streaming_complete.is_set()}")
                    logger.info(f"🔍 [API_STREAMING] chunk_queue.qsize() = {chunk_queue.qsize()}")
                    
                    chunk_count = 0
                    timeout_count = 0
                    while not streaming_complete.is_set():
                        try:
                            # Wait for chunk with short timeout to check completion
                            chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                            chunk_count += 1
                            logger.info(f"🔍 [API_STREAMING] 🎯 Got chunk #{chunk_count} from queue: {chunk}")
                            
                            if "type" in chunk and chunk["type"] == "error":
                                logger.info(f"🔍 [API_STREAMING] ❌ Yielding error chunk")
                                error_data = chunk
                                yield json.dumps(error_data) + "\n"
                            else:
                                logger.info(f"🔍 [API_STREAMING] ✅ Yielding content chunk: '{chunk['content'][:100]}...' (type: {chunk.get('content_type', 'response')})")
                                chunk_data = {
                                    "type": "chunk",
                                    "content": chunk["content"],
                                    "accumulated": chunk["accumulated"],
                                    "done": chunk["done"],
                                    "content_type": chunk.get("content_type", "response")  # Include content_type for frontend routing
                                }
                                # Include conversation_id and message_id in the final chunk
                                if chunk["done"]:
                                    chunk_data["conversation_id"] = conversation_id
                                    chunk_data["message_id"] = message_id  # Add message_id for feedback linking
                                    logger.info(f"🔍 [API_STREAMING] 📤 Sending final chunk with message_id: {message_id}")

                                # NOTE: Transport encryption for streaming is handled by EncryptionMiddleware.
                                yield json.dumps(chunk_data) + "\n"
                                
                        except asyncio.TimeoutError:
                            # No chunk received, continue waiting
                            timeout_count += 1
                            if timeout_count % 50 == 0:  # Log every 5 seconds
                                logger.info(f"🔍 [API_STREAMING] ⏱️ Still waiting for chunks... (timeout #{timeout_count}, elapsed: {asyncio.get_event_loop().time() - timeout_start:.1f}s)")
                    
                    # Log why loop exited
                    logger.info(f"🔍 [API_STREAMING] Loop exited: streaming_complete={streaming_complete.is_set()}, chunks_received={chunk_count}, timeouts={timeout_count}")
                    
                    # Unsubscribe
                    try:
                        await bus_client.unsubscribe(AICOTopics.CONVERSATION_STREAM)
                        logger.debug(f"🔍 [API_STREAMING] 🔌 Unsubscribed from streaming for {message_id}")
                    except Exception as e:
                        logger.error(f"Error unsubscribing from streaming: {e}")
                    
                    logger.debug(f"🔍 [API_STREAMING] 🏁 Stream generator completed for {message_id}")
                        
                except Exception as e:
                    logger.error(f"Stream generator error: {e}")
                    logger.debug(f"🔍 [API_STREAMING] ❌ Stream generator failed for {message_id}: {e}")
                    error_data = {
                        "type": "error",
                        "error": str(e)
                    }
                    yield json.dumps(error_data) + "\n"
            
            try:
                response = StreamingResponse(
                    stream_generator(),
                    media_type="application/x-ndjson",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Request-ID": message_id,
                        "X-Conversation-ID": conversation_id,
                    }
                )
                return response
            except Exception:
                raise
        else:
            # Non-streaming: Subscribe and wait for complete response
            await bus_client.subscribe(AICOTopics.CONVERSATION_AI_RESPONSE, handle_ai_response)
            
            # Wait for response with timeout (allow for unoptimized LLM processing)
            try:
                timeout_seconds = _get_conversation_timeout_seconds()
                logger.debug(f"🔍 [CONVERSATION_TIMEOUT] Waiting for response with {timeout_seconds}s timeout for request: {message_id}")
                await asyncio.wait_for(response_received.wait(), timeout=timeout_seconds)
                logger.debug(f"🔍 [CONVERSATION_TIMEOUT] ✅ Response received within timeout for request: {message_id}")
            except asyncio.TimeoutError:
                timeout_seconds = _get_conversation_timeout_seconds()
                logger.error(f"🔍 [CONVERSATION_TIMEOUT] ❌ TIMEOUT after {timeout_seconds}s for request: {message_id}")
                raise ConversationTimeoutException(
                    conversation_id=conversation_id,
                    timeout_seconds=int(timeout_seconds),
                    user_id=user_id,
                )
            finally:
                # Unsubscribe from the topic
                try:
                    await bus_client.unsubscribe(AICOTopics.CONVERSATION_AI_RESPONSE)
                except Exception as e:
                    logger.error(f"Error unsubscribing: {e}")
            
            # Return regular JSON response (existing logic)
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
    except ConversationException:
        # Let custom conversation exceptions map to their intended HTTP status codes
        # (e.g. ConversationTimeoutException -> 408) instead of being converted into 500s.
        raise
    except Exception as e:
        logger.error(f"Failed to send message with auto-thread: {e}")
        raise_api_error(
            status_code=500,
            error_code="CONVERSATION_MESSAGE_PROCESSING_FAILED",
            message="Failed to process message",
        )


# User-scoped endpoints - no thread management needed with semantic memory

@router.get(
    "/messages",
    response_model=MessageHistoryResponse,
    responses=error_responses(401, 500),
)
async def get_my_messages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Messages per page"),
    conversation_id: Optional[str] = Query(None, description="Filter by conversation ID"),
    since: Optional[datetime] = Query(None, description="Show messages after this timestamp"),
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Get my message history (user-scoped)
    
    Returns paginated message history for the authenticated user.
    Messages are retrieved from working memory (LMDB) with 24-hour retention.
    """
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]

        limit = page_size
        offset = (page - 1) * page_size

        filters: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
        if conversation_id:
            filters["conversation_id"] = conversation_id
        if since is not None:
            filters["created_after"] = since

        # Retrieve messages from Postgres source of truth
        messages = await uow.conversation_messages.list(filters=filters, limit=limit, offset=offset)
        total_count = await uow.conversation_messages.count(filters=filters)

        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg.message_id,
                "conversation_id": msg.conversation_id,
                "user_id": msg.user_id,
                "content": msg.content,
                "role": "assistant" if msg.actor_type in {"agent", "assistant"} else "user",
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "message_type": msg.message_type,
            })

        logger.debug(f"Retrieved {len(formatted_messages)} messages for user {user_id} (page {page})")

        return MessageHistoryResponse(
            success=True,
            messages=formatted_messages,
            conversation_id=conversation_id or f"user_{user_id}",
            total_count=total_count,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to get message history: {e}", extra={
            "conversation_id": conversation_id,
            "error": str(e)
        })
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise_api_error(
            status_code=500,
            error_code="CONVERSATION_MESSAGE_HISTORY_FAILED",
            message="Failed to retrieve message history",
        )
@router.get(
    "/status",
    responses=error_responses(401, 500),
)
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
        
        logger.debug(f"Getting conversation status for user: {user_id}")
        
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
        raise_api_error(
            status_code=500,
            error_code="CONVERSATION_STATUS_FAILED",
            message="Failed to retrieve conversation status",
        )


@router.websocket("/ws")
async def my_conversation_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time conversation updates (user-scoped)
    
    Provides real-time delivery of AI responses and conversation events
    for the authenticated user. No thread management needed.
    """
    try:
        user = authenticate_websocket(websocket=websocket)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    user_id = user["user_id"]
    connection_id = f"user_{user_id}_{uuid.uuid4()}"
    active_connections[connection_id] = websocket
    
    logger.debug(f"WebSocket connection established", extra={
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
                if hasattr(message, 'message') and hasattr(message.message, 'text'):
                    # Use message_id from backend if available, otherwise generate one
                    msg_id = getattr(message, 'message_id', None) or str(uuid.uuid4())
                    
                    # Create structured WebSocket response
                    ai_response = WebSocketAIResponse(
                        conversation_id=f"user_conversation_{user_id}",
                        message_id=msg_id,  # Use actual message_id from backend
                        message=message.message.text,
                        confidence=getattr(message, 'confidence', None),
                        processing_time_ms=getattr(message, 'processing_time_ms', None)
                    )
                    
                    await websocket.send_json(ai_response.dict())
                    
                    logger.debug(f"Sent AI response via WebSocket", extra={
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
                    conversation_id=f"user_conversation_{user_id}"
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
        
        logger.debug(f"WebSocket connection closed", extra={
            "connection_id": connection_id
        })


@router.post("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for conversation service"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
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
