"""
Memory Album API Router

REST API endpoints for user-curated memories (Memory Album feature).
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from aico.core.logging import get_logger
from aico.ai.memory.facts import FactStore
from aico.feedback.events import FeedbackEventStore
from aico.feedback.types import FeedbackEventType, ActionCategory
from backend.core.lifecycle_manager import get_database
from backend.api.conversation.dependencies import get_current_user
from .schemas import (
    RememberRequest, UpdateMemoryRequest,
    MemoryResponse, MemoryListResponse, RememberResponse
)
import json
import time

router = APIRouter()
logger = get_logger("backend", "api.memory_album")


@router.post("/remember", response_model=RememberResponse, status_code=status.HTTP_201_CREATED)
async def remember_message(
    request: RememberRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    User clicks 'Remember This' on a message.
    Performs dual storage: fact in facts_metadata + feedback event in feedback_events.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        # Initialize stores with encrypted DB connection
        fact_store = FactStore(db)
        feedback_store = FeedbackEventStore(db)
        
        # 1. Store the fact (memory content)
        fact_id = await fact_store.store_user_curated_fact(
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
        
        fact_store = FactStore(db)
        
        # Query user-curated facts
        facts = await fact_store.get_user_curated_facts(
            user_id=user_uuid,
            category=category,
            favorites_only=favorites_only,
            limit=limit,
            offset=offset,
        )
        
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
    db = Depends(get_database)
):
    """
    Update memory metadata (notes, tags, favorites).
    Used when user edits memory in the UI.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        fact_store = FactStore(db)
        
        # Update the fact metadata
        success = await fact_store.update_fact_metadata(
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
        
        # Retrieve updated fact
        facts = await fact_store.get_user_curated_facts(
            user_id=user_uuid,
            limit=1,
            offset=0,
        )
        
        # Find the updated fact
        updated_fact = next((f for f in facts if f['fact_id'] == fact_id), None)
        if not updated_fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found after update"
            )
        
        # Parse JSON fields
        tags = None
        if updated_fact.get('tags_json'):
            try:
                tags = json.loads(updated_fact['tags_json'])
            except:
                tags = []
        
        key_moments = None
        if updated_fact.get('key_moments_json'):
            try:
                key_moments = json.loads(updated_fact['key_moments_json'])
            except:
                key_moments = []
        
        logger.info(f"Memory updated: {fact_id}", extra={
            "user_uuid": user_uuid,
            "fact_id": fact_id,
        })
        
        return MemoryResponse(
            fact_id=updated_fact['fact_id'],
            content=updated_fact['content'],
            content_type=updated_fact.get('content_type', 'message'),
            category=updated_fact['category'],
            fact_type=updated_fact['fact_type'],
            user_note=updated_fact.get('user_note'),
            tags=tags,
            is_favorite=bool(updated_fact.get('is_favorite', 0)),
            emotional_tone=updated_fact.get('emotional_tone'),
            memory_type=updated_fact.get('memory_type'),
            source_conversation_id=updated_fact['source_conversation_id'],
            source_message_id=updated_fact.get('source_message_id'),
            revisit_count=updated_fact.get('revisit_count', 0),
            last_revisited=updated_fact.get('last_revisited'),
            created_at=updated_fact['created_at'],
            updated_at=updated_fact['updated_at'],
            conversation_title=updated_fact.get('conversation_title'),
            conversation_summary=updated_fact.get('conversation_summary'),
            turn_range=updated_fact.get('turn_range'),
            key_moments=key_moments,
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
    db = Depends(get_database)
):
    """
    Delete a memory from the album.
    """
    try:
        user_uuid = current_user['user_uuid']
        
        fact_store = FactStore(db)
        
        # Delete the fact
        success = await fact_store.delete_fact(
            fact_id=fact_id,
            user_id=user_uuid,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found or access denied"
            )
        
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
