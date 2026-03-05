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
    HealthResponse,
    ConversationDetail, ConversationListItem,
    ConversationUpdateRequest, CatchupMessage
)
from backend.api.pagination import PaginatedResponse
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

# Active WebSocket connections removed - now handled by API Gateway adapter

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
        conv_message.message.turn_number = 0  # Repository will update with actual turn number during persistence
        
        # Publish to conversation input topic (ConversationEngine will handle)
        logger.info(
            f"🔍 [GATEWAY_PUBLISH] Publishing user input to NATS topic={AICOTopics.CONVERSATION_USER_INPUT}, "
            f"tenant_id={tenant_id}, message_id={message_id}, conversation_id={conversation_id}"
        )
        await bus_client.publish(
            AICOTopics.CONVERSATION_USER_INPUT,
            conv_message,
            tenant_id=tenant_id,
            correlation_id=message_id,
            attributes={
                "user_id": user_id,
                "conversation_id": conversation_id,
                "request_id": request_id,
            },
        )
        logger.info(f"✅ [GATEWAY_PUBLISH] Successfully published to NATS")
        
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
                    await bus_client.subscribe(
                        AICOTopics.CONVERSATION_STREAM,
                        handle_streaming_chunk,
                        tenant_id=tenant_id,
                    )
                    
                    # Process chunks from queue as they arrive - truly event-driven
                    timeout_start = asyncio.get_event_loop().time()
                    logger.info(f"🔍 [API_STREAMING] 🎬 Starting streaming loop for {message_id}")
                    logger.info(f"🔍 [API_STREAMING] streaming_complete.is_set() = {streaming_complete.is_set()}")
                    logger.info(f"🔍 [API_STREAMING] chunk_queue.qsize() = {chunk_queue.qsize()}")
                    timeout_seconds = float(_get_conversation_timeout_seconds())
                    
                    chunk_count = 0
                    timeout_count = 0
                    warned_no_chunks = False
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
                            elapsed = asyncio.get_event_loop().time() - timeout_start

                            # Loud early warning: if core never emits any chunks, surface it quickly.
                            if not warned_no_chunks and chunk_count == 0 and elapsed >= 2.0:
                                warned_no_chunks = True
                                logger.error(
                                    "🔍 [API_STREAMING] ❌ No streaming chunks received after 2s. "
                                    "Likely core conversation engine not receiving input or not publishing CONVERSATION_STREAM.",
                                    extra={
                                        "message_id": message_id,
                                        "conversation_id": conversation_id,
                                        "tenant_id": tenant_id,
                                        "topic": str(AICOTopics.CONVERSATION_STREAM),
                                    },
                                )
                            if elapsed >= timeout_seconds:
                                logger.error(
                                    f"🔍 [API_STREAMING] ❌ TIMEOUT after {timeout_seconds}s waiting for streaming chunks for request: {message_id}"
                                )
                                error_data = {
                                    "type": "error",
                                    "error": f"Streaming timeout after {timeout_seconds}s",
                                    "message_id": message_id,
                                    "conversation_id": conversation_id,
                                }
                                yield json.dumps(error_data) + "\n"
                                streaming_complete.set()
                                break
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
    "/messages/catchup",
    response_model=MessageHistoryResponse,
    responses=error_responses(401, 404, 422, 500),
)
async def catchup_my_messages(
    conversation_id: Optional[str] = Query(None, description="Filter by conversation ID"),
    after_message_id: Optional[str] = Query(None, description="Return messages strictly after this message_id"),
    limit: int = Query(100, ge=1, le=500, description="Maximum messages to return"),
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """Catch up on messages after reconnect using Postgres as source of truth.

    Cursor semantics:
    - If `after_message_id` is provided, we look up its `created_at` in Postgres and
      return messages with `created_at` strictly greater than that timestamp.
    - Results are ordered ascending (oldest first) to support incremental replay.
    """
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]

        since_ts: Optional[datetime] = None
        if after_message_id:
            anchor = await uow.conversation_messages.get_by_id(after_message_id)
            if anchor is None:
                raise_api_error(
                    status_code=404,
                    error_code="CONVERSATION_MESSAGE_NOT_FOUND",
                    message="after_message_id not found",
                )
            if anchor.tenant_id != tenant_id or anchor.user_id != user_id:
                raise_api_error(
                    status_code=404,
                    error_code="CONVERSATION_MESSAGE_NOT_FOUND",
                    message="after_message_id not found",
                )
            if conversation_id and anchor.conversation_id != conversation_id:
                raise_api_error(
                    status_code=422,
                    error_code="CONVERSATION_MESSAGE_CURSOR_MISMATCH",
                    message="after_message_id does not belong to the provided conversation_id",
                )
            since_ts = anchor.created_at

        messages = await uow.conversation_messages.list_since(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            since=since_ts,
            limit=limit,
        )

        formatted_messages = []
        for msg in messages:
            formatted_messages.append(
                {
                    "id": msg.message_id,
                    "conversation_id": msg.conversation_id,
                    "user_id": msg.user_id,
                    "content": msg.content,
                    "role": "assistant" if msg.actor_type in {"agent", "assistant"} else "user",
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                    "message_type": msg.message_type,
                }
            )

        return MessageHistoryResponse(
            success=True,
            messages=formatted_messages,
            conversation_id=conversation_id or f"user_{user_id}",
            total_count=len(formatted_messages),
            page=1,
            page_size=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to catch up messages: {e}",
            extra={"conversation_id": conversation_id, "after_message_id": after_message_id},
        )
        raise_api_error(
            status_code=500,
            error_code="CONVERSATION_MESSAGE_CATCHUP_FAILED",
            message="Failed to catch up messages",
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


# WebSocket endpoint removed - now handled by API Gateway WebSocket adapter
# Clients should connect to ws://gateway:8772/ws and subscribe to "conversation.responses"


@router.post("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for conversation service"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        version="1.0.0"
    )


# ============================================================================
# Conversation Lifecycle Endpoints
# ============================================================================

@router.get(
    "/conversations",
    response_model=PaginatedResponse[ConversationListItem],
    responses=error_responses(401, 403, 500),
)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status: Optional[str] = Query(None, description="Filter by status (active, archived, deleted)"),
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    List conversations for the authenticated user.
    
    Returns paginated list of conversations with metadata.
    Supports filtering by status and pagination via limit/offset.
    
    Standard pagination contract:
    - Query params: limit (1-100), offset (>=0)
    - Response: {items: [...], total: N, limit: N, offset: N}
    """
    try:
        user_id = current_user['user_uuid']
        tenant_id = current_user["tenant_id"]
        
        # Query conversations from repository
        conversations = await uow.conversations.list_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        
        # Get total count for pagination
        total = await uow.conversations.count_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
        )
        
        # Get message counts for each conversation
        items = []
        for conv in conversations:
            message_count = await uow.conversation_messages.count_by_conversation(
                tenant_id=tenant_id,
                conversation_id=conv.conversation_id,
            )
            items.append(
                ConversationListItem(
                    conversation_id=conv.conversation_id,
                    title=conv.title,
                    status=conv.status,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=message_count,
                )
            )
        
        return PaginatedResponse[ConversationListItem](
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise_api_error(
            status_code=500,
            error_code="conversation_list_failed",
            message="Failed to retrieve conversations",
            details={"error": str(e)}
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    responses=error_responses(401, 403, 404, 500),
)
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Get detailed information about a specific conversation.
    
    Returns full conversation metadata including title, status, and timestamps.
    """
    try:
        user_id = current_user['user_uuid']
        tenant_id = current_user["tenant_id"]
        
        # Retrieve conversation
        conversation = await uow.conversations.get_by_key(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        
        if not conversation:
            raise_api_error(
                status_code=404,
                error_code="conversation_not_found",
                message=f"Conversation {conversation_id} not found",
            )
        
        # Verify user owns this conversation
        if conversation.user_id != user_id:
            raise_api_error(
                status_code=403,
                error_code="conversation_access_denied",
                message="You do not have access to this conversation",
            )
        
        return ConversationDetail(
            tenant_id=conversation.tenant_id,
            conversation_id=conversation.conversation_id,
            user_id=conversation.user_id,
            agent_id=conversation.agent_id,
            title=conversation.title,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}")
        raise_api_error(
            status_code=500,
            error_code="conversation_get_failed",
            message="Failed to retrieve conversation",
            details={"error": str(e)}
        )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    responses=error_responses(400, 401, 403, 404, 500),
)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Update conversation metadata (title, status).
    
    Allows updating conversation title and status transitions:
    - active → archived (hide from active list)
    - active → deleted (soft delete)
    - archived → active (restore)
    """
    try:
        user_id = current_user['user_uuid']
        tenant_id = current_user["tenant_id"]
        
        # Retrieve existing conversation
        conversation = await uow.conversations.get_by_key(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        
        if not conversation:
            raise_api_error(
                status_code=404,
                error_code="conversation_not_found",
                message=f"Conversation {conversation_id} not found",
            )
        
        # Verify user owns this conversation
        if conversation.user_id != user_id:
            raise_api_error(
                status_code=403,
                error_code="conversation_access_denied",
                message="You do not have access to this conversation",
            )
        
        # Validate at least one field is being updated
        if request.title is None and request.status is None:
            raise_api_error(
                status_code=400,
                error_code="no_updates_provided",
                message="At least one field (title or status) must be provided",
            )
        
        # Update conversation
        updated = await uow.conversations.touch(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_id=user_id,
            title=request.title if request.title is not None else conversation.title,
            status=request.status if request.status is not None else conversation.status,
        )
        
        await uow.commit()
        
        logger.info(
            f"Updated conversation {conversation_id}",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "updates": {"title": request.title, "status": request.status}
            }
        )
        
        return ConversationDetail(
            tenant_id=updated.tenant_id,
            conversation_id=updated.conversation_id,
            user_id=updated.user_id,
            agent_id=updated.agent_id,
            title=updated.title,
            status=updated.status,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation {conversation_id}: {e}")
        raise_api_error(
            status_code=500,
            error_code="conversation_update_failed",
            message="Failed to update conversation",
            details={"error": str(e)}
        )
