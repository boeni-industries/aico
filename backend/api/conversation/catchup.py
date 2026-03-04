"""
Conversation Catch-up Endpoint

Provides deterministic message replay using turn_number for ordering.
Critical for reliable client reconnection and message synchronization.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow
from backend.api.dependencies import get_current_user
from backend.api.conversation.schemas import CatchupMessage
from backend.api.pagination import PaginatedResponse
from backend.api.errors import raise_api_error, error_responses
from aico.core.logging import get_logger

logger = get_logger("backend.api.conversation.catchup")

router = APIRouter()


@router.get(
    "/conversations/{conversation_id}/messages/catchup",
    response_model=PaginatedResponse[CatchupMessage],
    responses=error_responses(401, 403, 404, 500),
)
async def catchup_messages(
    conversation_id: str,
    after_turn: int = Query(0, ge=0, description="Get messages after this turn number"),
    limit: int = Query(100, ge=1, le=500, description="Maximum messages to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Get messages after a specific turn number for catch-up/replay.
    
    Uses turn_number for deterministic ordering, avoiding timestamp-based
    race conditions. Essential for reliable message synchronization when
    clients reconnect or need to replay conversation history.
    
    **Ordering Guarantee**: Messages are always returned in turn_number ASC order,
    ensuring deterministic replay regardless of timestamp collisions.
    
    **Use Cases**:
    - Client reconnection after network interruption
    - Loading conversation history in chunks
    - Synchronizing multiple clients viewing same conversation
    - Debugging message ordering issues
    
    **Example**:
    ```
    GET /conversations/{id}/messages/catchup?after_turn=5&limit=50
    
    Returns messages with turn_number > 5, ordered by turn_number ASC
    ```
    """
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    
    try:
        async with uow:
            # Verify conversation exists and user has access
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
                    message="You don't have access to this conversation",
                )
            
            # Get messages after turn number with deterministic ordering
            messages = await uow.conversation_messages.list_after_turn(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                after_turn=after_turn,
                limit=limit,
            )
            
            # Get total count for pagination metadata
            total = await uow.conversation_messages.count_by_conversation(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
            )
            
            # Convert to response schema
            items = [
                CatchupMessage(
                    message_id=msg.message_id,
                    conversation_id=msg.conversation_id,
                    actor_type=msg.actor_type,
                    message_type=msg.message_type,
                    content=msg.content,
                    turn_number=msg.turn_number,
                    created_at=msg.created_at,
                    metadata=msg.metadata_json,
                )
                for msg in messages
            ]
            
            logger.info(
                f"Catchup query: conversation={conversation_id}, after_turn={after_turn}, "
                f"returned={len(items)}, total={total}",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "after_turn": after_turn,
                    "returned_count": len(items),
                }
            )
            
            return PaginatedResponse[CatchupMessage](
                items=items,
                total=total,
                limit=limit,
                offset=after_turn,  # offset represents the turn number we're starting after
            )
            
    except Exception as e:
        logger.error(f"Catchup query failed: {e}", exc_info=True)
        raise_api_error(
            status_code=500,
            error_code="catchup_failed",
            message="Failed to retrieve messages",
            details={"error": str(e)}
        )
