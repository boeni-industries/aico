from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from google.protobuf.timestamp_pb2 import Timestamp

from aico.common.errors import raise_api_error
from aico.common.postgres_dependencies import get_uow
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.data.uow import UnitOfWork
from aico.proto.aico_conversation_pb2 import ConversationMessage, StreamingResponse as StreamingResponseProto
from gateway.api.conversation.dependencies import get_message_bus_client
from gateway.api.conversation.exceptions import ConversationException, ConversationTimeoutException
from gateway.api.conversation.schemas import (
    CatchupMessage,
    ConversationDetail,
    ConversationListItem,
    ConversationPageResponse,
    ConversationStatus,
    ConversationUpdateRequest,
    HealthResponse,
    MessageHistoryResponse,
    UnifiedMessageRequest,
    UnifiedMessageResponse,
)
from gateway.api.dependencies import get_current_user

router = APIRouter()
logger = get_logger("gateway.api.conversation")


def _get_conversation_timeout_seconds() -> float:
    try:
        from aico.core.config import ConfigurationManager

        cfg = ConfigurationManager()
        cfg.initialize(lightweight=True)
        return float(cfg.get("conversation.response_timeout_seconds", 15.0))
    except Exception:
        return 15.0


@router.post("/messages")
async def send_message_with_auto_thread(
    request: UnifiedMessageRequest,
    raw_request: Request,
    stream: str = Query("false", description="Enable streaming response"),
    current_user=Depends(get_current_user),
    bus_client=Depends(get_message_bus_client),
):
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]
        request_conversation_id = getattr(request, "conversation_id", None)
        if request_conversation_id and request_conversation_id != "default" and "_" in request_conversation_id:
            conversation_id = request_conversation_id
        else:
            conversation_id = f"{user_id}_{int(time.time())}"
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        request_id = raw_request.headers.get("Idempotency-Key") or message_id

        proto_timestamp = Timestamp()
        proto_timestamp.FromDatetime(timestamp)
        conv_message = ConversationMessage(
            timestamp=proto_timestamp,
            source="conversation_api",
            message_id=message_id,
            user_id=user_id,
        )
        conv_message.message.text = request.message
        conv_message.message.type = conv_message.message.MessageType.USER_INPUT
        conv_message.message.conversation_id = conversation_id
        conv_message.message.turn_number = 0

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

        response_received = asyncio.Event()
        ai_response = "No response received"

        async def handle_ai_response(envelope):
            nonlocal ai_response
            try:
                conversation_message = ConversationMessage()
                envelope.any_payload.Unpack(conversation_message)
                if conversation_message.message_id != message_id:
                    return
                raw_response = conversation_message.message.text
                ai_response = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL).strip()
                response_received.set()
            except Exception as exc:
                logger.error("Error handling AI response", extra={"error": str(exc)})

        stream_enabled = stream.lower() in ("true", "1", "yes", "on")
        if stream_enabled:
            async def stream_generator():
                try:
                    metadata = {
                        "type": "metadata",
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "timestamp": timestamp.isoformat(),
                    }
                    yield json.dumps(metadata) + "\n"
                    streaming_complete = asyncio.Event()
                    chunk_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

                    async def handle_streaming_chunk(envelope):
                        try:
                            streaming_chunk = StreamingResponseProto()
                            envelope.any_payload.Unpack(streaming_chunk)
                            if streaming_chunk.request_id != message_id:
                                return
                            await chunk_queue.put(
                                {
                                    "content": streaming_chunk.content,
                                    "accumulated": streaming_chunk.accumulated_content,
                                    "done": streaming_chunk.done,
                                    "content_type": streaming_chunk.content_type,
                                    "message_id": getattr(streaming_chunk, "message_id", None),
                                }
                            )
                            if streaming_chunk.done:
                                streaming_complete.set()
                        except Exception as exc:
                            await chunk_queue.put({"type": "error", "error": str(exc)})
                            streaming_complete.set()

                    await bus_client.subscribe(AICOTopics.CONVERSATION_STREAM, handle_streaming_chunk, tenant_id=tenant_id)
                    try:
                        timeout_start = asyncio.get_event_loop().time()
                        timeout_seconds = float(_get_conversation_timeout_seconds())
                        chunk_count = 0
                        warned_no_chunks = False
                        while not streaming_complete.is_set():
                            try:
                                chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                                chunk_count += 1
                                if "type" in chunk and chunk["type"] == "error":
                                    yield json.dumps(chunk) + "\n"
                                else:
                                    chunk_data = {
                                        "type": "chunk",
                                        "content": chunk["content"],
                                        "accumulated": chunk["accumulated"],
                                        "done": chunk["done"],
                                        "content_type": chunk.get("content_type", "response"),
                                    }
                                    if chunk["done"]:
                                        chunk_data["conversation_id"] = conversation_id
                                        chunk_data["message_id"] = message_id
                                    yield json.dumps(chunk_data) + "\n"
                            except asyncio.TimeoutError:
                                elapsed = asyncio.get_event_loop().time() - timeout_start
                                if not warned_no_chunks and chunk_count == 0 and elapsed >= 2.0:
                                    warned_no_chunks = True
                                    logger.error(
                                        "No streaming chunks received after 2s",
                                        extra={
                                            "message_id": message_id,
                                            "conversation_id": conversation_id,
                                            "tenant_id": tenant_id,
                                            "topic": str(AICOTopics.CONVERSATION_STREAM),
                                        },
                                    )
                                if elapsed >= timeout_seconds:
                                    yield json.dumps(
                                        {
                                            "type": "error",
                                            "error": f"Streaming timeout after {timeout_seconds}s",
                                            "message_id": message_id,
                                            "conversation_id": conversation_id,
                                        }
                                    ) + "\n"
                                    streaming_complete.set()
                                    break
                    finally:
                        await bus_client.unsubscribe(AICOTopics.CONVERSATION_STREAM)
                except Exception as exc:
                    yield json.dumps({"type": "error", "error": str(exc)}) + "\n"

            return StreamingResponse(
                stream_generator(),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": message_id,
                    "X-Conversation-ID": conversation_id,
                },
            )

        await bus_client.subscribe(AICOTopics.CONVERSATION_AI_RESPONSE, handle_ai_response, tenant_id=tenant_id)
        try:
            timeout_seconds = _get_conversation_timeout_seconds()
            try:
                await asyncio.wait_for(response_received.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise ConversationTimeoutException(
                    conversation_id=conversation_id,
                    timeout_seconds=int(timeout_seconds),
                    user_id=user_id,
                )
        finally:
            await bus_client.unsubscribe(AICOTopics.CONVERSATION_AI_RESPONSE)

        return UnifiedMessageResponse(
            success=True,
            message_id=message_id,
            conversation_id=conversation_id,
            conversation_action="conversation_started",
            conversation_reasoning="Conversation continuity handled via enhanced semantic memory",
            status="completed",
            ai_response=ai_response,
            timestamp=timestamp,
        )
    except ConversationException:
        raise
    except Exception as exc:
        logger.error("Failed to process conversation message", extra={"error": str(exc)})
        raise_api_error(
            status_code=500,
            error_code="CONVERSATION_MESSAGE_PROCESSING_FAILED",
            message="Failed to process message",
            details={"error": str(exc)},
        )


@router.get("/messages", response_model=MessageHistoryResponse)
async def get_my_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    conversation_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    tenant_id = current_user["tenant_id"]
    filters: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
    if conversation_id:
        filters["conversation_id"] = conversation_id
    if since is not None:
        filters["created_after"] = since
    limit = page_size
    offset = (page - 1) * page_size
    messages = await uow.conversation_messages.list(filters=filters, limit=limit, offset=offset)
    total_count = await uow.conversation_messages.count(filters=filters)
    formatted_messages = [
        {
            "id": msg.message_id,
            "conversation_id": msg.conversation_id,
            "user_id": msg.user_id,
            "content": msg.content,
            "role": "assistant" if msg.actor_type in {"agent", "assistant"} else "user",
            "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            "message_type": msg.message_type,
        }
        for msg in messages
    ]
    return MessageHistoryResponse(
        success=True,
        conversation_id=conversation_id or f"user_{user_id}",
        messages=formatted_messages,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/messages/catchup")
async def catchup_my_messages(
    conversation_id: Optional[str] = Query(None),
    after_message_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    tenant_id = current_user["tenant_id"]
    since_ts: Optional[datetime] = None
    if after_message_id:
        anchor = await uow.conversation_messages.get_by_id(after_message_id)
        if anchor is None or anchor.tenant_id != tenant_id or anchor.user_id != user_id:
            raise_api_error(status_code=404, error_code="CONVERSATION_MESSAGE_NOT_FOUND", message="after_message_id not found")
        if conversation_id and anchor.conversation_id != conversation_id:
            raise_api_error(status_code=422, error_code="CONVERSATION_MESSAGE_CURSOR_MISMATCH", message="after_message_id does not belong to the provided conversation_id")
        since_ts = anchor.created_at
    messages = await uow.conversation_messages.list_since(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        since=since_ts,
        limit=limit,
    )
    formatted_messages = [
        CatchupMessage(
            message_id=msg.message_id,
            conversation_id=msg.conversation_id,
            actor_type=msg.actor_type,
            message_type=msg.message_type,
            content=msg.content,
            turn_number=msg.turn_number,
            created_at=msg.created_at,
            metadata=msg.metadata,
        ).model_dump(mode="json")
        for msg in messages
    ]
    return MessageHistoryResponse(
        success=True,
        conversation_id=conversation_id or f"user_{user_id}",
        messages=formatted_messages,
        total_count=len(formatted_messages),
        page=1,
        page_size=limit,
    )


@router.get("/status", response_model=ConversationStatus)
async def get_my_conversation_status(
    current_user=Depends(get_current_user),
):
    user_id = current_user["user_uuid"]
    return ConversationStatus(
        conversation_id=f"user_{user_id}",
        active=True,
        message_count=0,
        last_activity=datetime.now(timezone.utc).isoformat(),
        context=None,
        user_id=user_id,
    )


@router.post("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.now(timezone.utc), version="1.0.0")


@router.get("/conversations", response_model=ConversationPageResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]
        conversations = await uow.conversations.list_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        total = await uow.conversations.count_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
        )
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
        return ConversationPageResponse(items=items, total=total, limit=limit, offset=offset)
    except Exception as exc:
        logger.error("Failed to list conversations", extra={"error": str(exc)})
        raise_api_error(
            status_code=500,
            error_code="conversation_list_failed",
            message="Failed to retrieve conversations",
            details={"error": str(exc)},
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]
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
    except Exception as exc:
        logger.error("Failed to get conversation", extra={"conversation_id": conversation_id, "error": str(exc)})
        raise_api_error(
            status_code=500,
            error_code="conversation_get_failed",
            message="Failed to retrieve conversation",
            details={"error": str(exc)},
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    try:
        user_id = current_user["user_uuid"]
        tenant_id = current_user["tenant_id"]
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
        if conversation.user_id != user_id:
            raise_api_error(
                status_code=403,
                error_code="conversation_access_denied",
                message="You do not have access to this conversation",
            )
        if request.title is None and request.status is None:
            raise_api_error(
                status_code=400,
                error_code="no_updates_provided",
                message="At least one field (title or status) must be provided",
            )
        updated = await uow.conversations.touch(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_id=user_id,
            title=request.title if request.title is not None else conversation.title,
            status=request.status if request.status is not None else conversation.status,
        )
        await uow.commit()
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
    except Exception as exc:
        logger.error("Failed to update conversation", extra={"conversation_id": conversation_id, "error": str(exc)})
        raise_api_error(
            status_code=500,
            error_code="conversation_update_failed",
            message="Failed to update conversation",
            details={"error": str(exc)},
        )
