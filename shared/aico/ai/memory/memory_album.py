"""
Memory Album Store

Manages user-curated memories in user_memories table.
Shared between backend and CLI for consistent memory management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import uuid

from aico.core.logging import get_logger

logger = get_logger("shared.ai.memory.memory_album")


class MemoryAlbumStore:
    """
    Manages user-curated memories in user_memories table.
    Shared between backend and CLI for consistent memory management.
    Uses UnitOfWork pattern for PostgreSQL access.
    """
    
    def __init__(self):
        """
        Initialize MemoryAlbumStore.
        No longer takes db_connection - uses UnitOfWork pattern.
        """
        pass
    
    async def store_user_curated_fact(
        self,
        user_id: str,
        conversation_id: str,
        message_id: Optional[str],
        content: str,
        fact_type: str,
        category: str,
        content_type: str = "message",
        user_note: Optional[str] = None,
        tags: Optional[List[str]] = None,
        emotional_tone: Optional[str] = None,
        memory_type: str = "fact",
        conversation_title: Optional[str] = None,
        conversation_summary: Optional[str] = None,
        turn_range: Optional[str] = None,
        key_moments: Optional[List[str]] = None,
    ) -> str:
        """
        Store a user-curated fact (Memory Album entry).
        
        Args:
            user_id: User identifier
            conversation_id: Source conversation identifier
            message_id: Source message identifier
            content: The remembered text
            fact_type: Type of fact (identity, preference, relationship, temporal)
            category: Category (personal_info, preferences, relationships, etc.)
            user_note: Optional user annotation
            tags: Optional list of user-defined tags
            emotional_tone: Optional emotional tone (joyful, reflective, etc.)
            memory_type: Type of memory (fact, insight, moment, milestone, wisdom)
        
        Returns:
            fact_id: The ID of the stored fact
        """
        
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.ams_service import AMSService
        
        fact_id = f"fact_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            ams_service = AMSService(uow)
            
            memory_data = {
                # Core identity fields expected by AMSUserMemory
                'fact_id': fact_id,
                'user_id': user_id,
                'fact_type': fact_type,
                'category': category,
                'confidence': 1.0,  # User-curated = 100% confidence
                'is_immutable': False,
                # Validity window – for user-curated memories we treat them as valid from now
                'valid_from': now,
                'valid_until': None,
                # Content and extraction metadata
                'content': content,
                'entities_json': None,
                'extraction_method': 'user_curated',
                'source_conversation_id': conversation_id,
                'source_message_id': message_id,
                # Timestamps
                'created_at': now,
                'updated_at': now,
                # User-facing metadata
                'user_note': user_note,
                'tags_json': {'tags': tags} if tags else None,
                'is_favorite': False,
                'revisit_count': 0,
                'last_revisited': None,
                'emotional_tone': emotional_tone,
                'memory_type': memory_type,
                'content_type': content_type,
                'conversation_title': conversation_title,
                'conversation_summary': conversation_summary,
                'turn_range': turn_range,
                'key_moments_json': {'items': key_moments} if key_moments else None,
                'temporal_metadata': None,
                'language': None,
            }
            
            await ams_service.create_user_memory(memory_data)
        
        logger.info(f"Stored user-curated fact: {fact_id}", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "category": category,
        })
        
        return fact_id
    
    async def get_user_curated_facts(
        self,
        user_id: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user-curated facts (Memory Album entries).
        
        Args:
            user_id: User identifier
            category: Optional filter by category
            start_date: Optional filter by start date
            end_date: Optional filter by end date
            favorites_only: Only return favorited memories
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of user-curated facts as dictionaries
        """
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.ams_service import AMSService
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            # Build filters for repository
            filters = {
                'user_id': user_id,
                'extraction_method': 'user_curated'
            }
            
            if category:
                filters['category'] = category
            
            if start_date:
                filters['created_at_gte'] = start_date
            
            if end_date:
                filters['created_at_lte'] = end_date
            
            if favorites_only:
                filters['is_favorite'] = True
            
            # Get memories directly via repository
            memories = await uow.ams_user_memories.list(
                filters=filters,
                limit=limit,
                offset=offset
            )
            
            # Convert to dict format
            return [
                {
                    'fact_id': m.fact_id,
                    'user_id': m.user_id,
                    'content': m.content,
                    'category': m.category,
                    'fact_type': m.fact_type,
                    'user_note': m.user_note,
                    'tags_json': m.tags_json,
                    'is_favorite': m.is_favorite,
                    'emotional_tone': m.emotional_tone,
                    'memory_type': m.memory_type,
                    'source_conversation_id': m.source_conversation_id,
                    'source_message_id': m.source_message_id,
                    'created_at': m.created_at,
                    'updated_at': m.updated_at
                }
                for m in memories
            ]
    
    async def update_fact_metadata(
        self,
        fact_id: str,
        user_id: str,
        user_note: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
    ) -> bool:
        """
        Update Memory Album metadata for a fact.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
            user_note: Optional new user note
            tags: Optional new tags list
            is_favorite: Optional favorite status
        
        Returns:
            True if update succeeded, False otherwise
        """
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.ams_service import AMSService
        
        if user_note is None and tags is None and is_favorite is None:
            return False
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            ams_service = AMSService(uow)
            
            update_data = {}
            if user_note is not None:
                update_data['user_note'] = user_note
            if tags is not None:
                update_data['tags'] = tags
            if is_favorite is not None:
                update_data['is_favorite'] = is_favorite
            
            success = await ams_service.update_user_memory(
                memory_id=fact_id,
                user_id=user_id,
                update_data=update_data
            )
            
            return success
    
    async def record_revisit(self, fact_id: str, user_id: str) -> bool:
        """
        Increment revisit count when user views a memory.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
        
        Returns:
            True if update succeeded, False otherwise
        """
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.ams_service import AMSService
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            ams_service = AMSService(uow)
            
            success = await ams_service.record_memory_revisit(
                memory_id=fact_id,
                user_id=user_id
            )
            
            return success
    
    async def delete_fact(self, fact_id: str, user_id: str) -> bool:
        """
        Delete a user-curated fact.
        
        Args:
            fact_id: Fact identifier
            user_id: User identifier (for verification)
        
        Returns:
            True if deletion succeeded, False otherwise
        """
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.ams_service import AMSService
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            ams_service = AMSService(uow)
            
            success = await ams_service.delete_user_memory(
                memory_id=fact_id,
                user_id=user_id
            )
            
            if success:
                logger.info(f"Deleted user-curated fact: {fact_id}", extra={
                    "user_id": user_id,
                    "fact_id": fact_id,
                })
            
            return success
