"""
Memory Album API Router

REST API endpoints for user-curated memories (Memory Album feature).
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from aico.core.logging import get_logger
from aico.ai.memory.memory_album import MemoryAlbumStore
from aico.feedback.events import FeedbackEventStore
from aico.feedback.types import FeedbackEventType, ActionCategory
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork
from backend.api.conversation.dependencies import get_current_user
from .schemas import (
    RememberRequest, UpdateMemoryRequest,
    MemoryResponse, MemoryListResponse, RememberResponse
)
import json
import time

router = APIRouter()
logger = get_logger("backend.api.memory_album")


@router.post("/remember", response_model=RememberResponse, status_code=status.HTTP_201_CREATED)
async def remember_message(
    request: RememberRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    User clicks 'Remember This' on a message.
    Performs dual storage: memory in user_memories + feedback event in feedback_events.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        # Initialize stores with encrypted DB connection
        memory_store = MemoryAlbumStore(db)
        feedback_store = FeedbackEventStore(db)
        
        # 1. Store the fact (memory content)
        fact_id = await memory_store.store_user_curated_fact(
            user_id=user_uuid,
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            content=request.content,
            fact_type=request.fact_type,
            category=request.category,
            content_type=request.content_type,
            user_note=request.user_note,
            tags=request.tags,
            emotional_tone=request.emotional_tone,
            memory_type=request.memory_type,
            conversation_title=request.conversation_title,
            conversation_summary=request.conversation_summary,
            turn_range=request.turn_range,
            key_moments=request.key_moments,
        )
        
        # 2. Record the feedback event (user action)
        await feedback_store.record_event(
            user_uuid=user_uuid,
            conversation_id=request.conversation_id,
            event_type=FeedbackEventType.ACTION,
            event_category=ActionCategory.REMEMBER.value,
            payload={
                "message_id": request.message_id,
                "fact_id": fact_id,
                "content_preview": request.content[:50],
                "fact_category": request.category,
                "action_timestamp": int(time.time()),
            },
            message_id=request.message_id,
        )
        
        logger.info(f"Memory saved: {fact_id}", extra={
            "user_uuid": user_uuid,
            "conversation_id": request.conversation_id,
            "category": request.category,
        })
        
        return RememberResponse(
            success=True,
            fact_id=fact_id,
            message="Memory saved to your album ✨"
        )
        
    except Exception as e:
        logger.error(f"Failed to save memory: {e}", extra={
            "user_uuid": current_user.get('user_uuid'),
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}"
        )


@router.get("", response_model=MemoryListResponse)
async def get_memories(
    category: Optional[str] = None,
    favorites_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get user's memory album entries with optional filters.
    Used by the 'Memories' page in the UI.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        memory_store = MemoryAlbumStore(db)
        
        # Query user-curated facts with user profile information
        facts = await memory_store.get_user_curated_facts(
            user_id=user_uuid,
            category=category,
            favorites_only=favorites_only,
            limit=limit,
            offset=offset,
        )
        
        # Enrich with user profile data
        enriched_facts = []
        for fact in facts:
            # Get user profile for this fact
            logger.debug(f"Looking up user profile for user_id: {fact.get('user_id')}")
            
            user_profile = await uow.users.get_by_id(fact['user_id'])
            
            fact_with_user = dict(fact)
            if user_profile:
                fact_with_user['user_uuid'] = user_profile.uuid
                fact_with_user['user_full_name'] = user_profile.full_name
                fact_with_user['user_nickname'] = user_profile.nickname
            else:
                logger.warning(f"No user profile found for user_id: {fact.get('user_id')}")
                
                fact_with_user['user_uuid'] = fact['user_id']
                fact_with_user['user_full_name'] = 'Unknown'
                fact_with_user['user_nickname'] = None
            
            enriched_facts.append(fact_with_user)
        
        facts = enriched_facts
        
        # Convert to response format
        memories = []
        for fact in facts:
            # Parse JSON fields
            tags = None
            if fact.get('tags_json'):
                try:
                    tags = json.loads(fact['tags_json'])
                except:
                    tags = []
            
            key_moments = None
            if fact.get('key_moments_json'):
                try:
                    key_moments = json.loads(fact['key_moments_json'])
                except:
                    key_moments = []
            
            memories.append(MemoryResponse(
                fact_id=fact['fact_id'],
                content=fact['content'],
                content_type=fact.get('content_type', 'message'),
                category=fact['category'],
                fact_type=fact['fact_type'],
                user_note=fact.get('user_note'),
                tags=tags,
                is_favorite=bool(fact.get('is_favorite', 0)),
                emotional_tone=fact.get('emotional_tone'),
                memory_type=fact.get('memory_type'),
                source_conversation_id=fact['source_conversation_id'],
                source_message_id=fact.get('source_message_id'),
                revisit_count=fact.get('revisit_count', 0),
                last_revisited=fact.get('last_revisited'),
                created_at=fact['created_at'],
                updated_at=fact['updated_at'],
                user_uuid=fact.get('user_uuid', fact['user_id']),
                user_full_name=fact.get('user_full_name', 'Unknown User'),
                user_nickname=fact.get('user_nickname'),
                conversation_title=fact.get('conversation_title'),
                conversation_summary=fact.get('conversation_summary'),
                turn_range=fact.get('turn_range'),
                key_moments=key_moments,
            ))
        
        logger.info(f"Retrieved {len(memories)} memories", extra={
            "user_uuid": user_uuid,
            "category": category,
            "favorites_only": favorites_only,
        })
        
        return MemoryListResponse(
            memories=memories,
            total=len(memories),
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve memories: {e}", extra={
            "user_uuid": current_user.get('user_uuid'),
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memories: {str(e)}"
        )


@router.patch("/{fact_id}", response_model=MemoryResponse)
async def update_memory(
    fact_id: str,
    request: UpdateMemoryRequest,
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    Update memory metadata (notes, tags, favorites).
    Used when user edits memory in the UI.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        memory_store = MemoryAlbumStore(uow)
        
        # Update the fact metadata
        success = await memory_store.update_fact_metadata(
            fact_id=fact_id,
            user_id=user_uuid,
            user_note=request.user_note,
            tags=request.tags,
            is_favorite=request.is_favorite,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found or access denied"
            )
        
        # Retrieve the specific updated fact from repository
        all_memories = await uow.ams_user_memories.list(
            filters={"fact_id": fact_id, "user_id": user_uuid, "extraction_method": "user_curated"},
            limit=1
        )
        
        row = all_memories[0] if all_memories else None
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found after update"
            )
        
        user_profile = await uow.users.get_by_id(user_uuid)
        
        return MemoryResponse(
            fact_id=row.fact_id,
            content=row.content,
            category=row.category,
            fact_type=row.fact_type,
            user_note=row.user_note,
            tags=json.loads(row.tags_json) if row.tags_json else [],
            is_favorite=bool(row.is_favorite),
            emotional_tone=row.emotional_tone,
            memory_type=row.memory_type,
            revisit_count=row.revisit_count,
            last_revisited=row.last_revisited,
            created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
            updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at),
            user_uuid=user_profile.uuid if user_profile else user_uuid,
            user_full_name=user_profile.full_name if user_profile else 'Unknown',
            user_nickname=user_profile.nickname if user_profile else None,
            content_type=row.content_type,
            conversation_title=row.conversation_title,
            conversation_summary=row.conversation_summary,
            turn_range=row.turn_range,
            key_moments=json.loads(row.key_moments_json) if row.key_moments_json else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update memory: {e}", extra={
            "user_uuid": current_user.get('user_uuid'),
            "fact_id": fact_id,
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    fact_id: str,
    current_user = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    Delete a memory from the album.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        # Delete the memory using repository
        # First verify it exists and belongs to user
        memories = await uow.ams_user_memories.list(
            filters={"fact_id": fact_id, "user_id": user_uuid},
            limit=1
        )
        
        if not memories:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found or access denied"
            )
        
        # Delete it
        await uow.ams_user_memories.delete(fact_id)
        await uow.commit()
        
        logger.info(f"Memory deleted: {fact_id}", extra={
            "user_uuid": user_uuid,
            "fact_id": fact_id,
        })
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}", extra={
            "user_uuid": current_user.get('user_uuid'),
            "fact_id": fact_id,
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )
