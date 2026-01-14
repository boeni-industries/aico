"""
AMSUserMemoriesRepository - PostgreSQL implementation

Handles CRUD operations for AMS user memories.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.models import AMSUserMemory
from aico.data.tables import ams_user_memories
from aico.data.repositories.base import Repository


class PostgresAMSUserMemoriesRepository(Repository[AMSUserMemory]):
    """PostgreSQL implementation of AMS user memories repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AMSUserMemory) -> AMSUserMemory:
        """Create a new user memory."""
        stmt = ams_user_memories.insert().values(
            fact_id=entity.fact_id,
            user_id=entity.user_id,
            fact_type=entity.fact_type,
            category=entity.category,
            confidence=entity.confidence,
            is_immutable=entity.is_immutable,
            valid_from=entity.valid_from,
            valid_until=entity.valid_until,
            content=entity.content,
            entities_json=entity.entities_json,
            extraction_method=entity.extraction_method,
            source_conversation_id=entity.source_conversation_id,
            source_message_id=entity.source_message_id,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
            user_note=entity.user_note,
            tags_json=entity.tags_json,
            is_favorite=entity.is_favorite,
            revisit_count=entity.revisit_count,
            last_revisited=entity.last_revisited,
            emotional_tone=entity.emotional_tone,
            memory_type=entity.memory_type,
            content_type=entity.content_type,
            conversation_title=entity.conversation_title,
            conversation_summary=entity.conversation_summary,
            turn_range=entity.turn_range,
            key_moments_json=entity.key_moments_json,
            temporal_metadata=entity.temporal_metadata,
            language=entity.language,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AMSUserMemory]:
        """Get user memory by ID."""
        stmt = select(ams_user_memories).where(ams_user_memories.c.fact_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AMSUserMemory(
            fact_id=row.fact_id,
            user_id=row.user_id,
            fact_type=row.fact_type,
            category=row.category,
            confidence=row.confidence,
            is_immutable=row.is_immutable,
            valid_from=row.valid_from,
            valid_until=row.valid_until,
            content=row.content,
            entities_json=row.entities_json,
            extraction_method=row.extraction_method,
            source_conversation_id=row.source_conversation_id,
            source_message_id=row.source_message_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            user_note=row.user_note,
            tags_json=row.tags_json,
            is_favorite=row.is_favorite,
            revisit_count=row.revisit_count,
            last_revisited=row.last_revisited,
            emotional_tone=row.emotional_tone,
            memory_type=row.memory_type,
            content_type=row.content_type,
            conversation_title=row.conversation_title,
            conversation_summary=row.conversation_summary,
            turn_range=row.turn_range,
            key_moments_json=row.key_moments_json,
            temporal_metadata=row.temporal_metadata,
            language=row.language,
        )
    
    async def update(self, entity: AMSUserMemory) -> AMSUserMemory:
        """Update an existing user memory."""
        stmt = (
            update(ams_user_memories)
            .where(ams_user_memories.c.fact_id == entity.fact_id)
            .values(
                confidence=entity.confidence,
                valid_until=entity.valid_until,
                content=entity.content,
                user_note=entity.user_note,
                tags_json=entity.tags_json,
                is_favorite=entity.is_favorite,
                revisit_count=entity.revisit_count,
                last_revisited=entity.last_revisited,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user memory."""
        stmt = delete(ams_user_memories).where(ams_user_memories.c.fact_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AMSUserMemory]:
        """List user memories with optional filters."""
        stmt = select(ams_user_memories)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_user_memories.c.user_id == filters['user_id'])
            if 'category' in filters:
                conditions.append(ams_user_memories.c.category == filters['category'])
            if 'fact_type' in filters:
                conditions.append(ams_user_memories.c.fact_type == filters['fact_type'])
            if 'is_favorite' in filters:
                conditions.append(ams_user_memories.c.is_favorite == filters['is_favorite'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_user_memories.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AMSUserMemory(
                fact_id=row.fact_id,
                user_id=row.user_id,
                fact_type=row.fact_type,
                category=row.category,
                confidence=row.confidence,
                is_immutable=row.is_immutable,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                content=row.content,
                entities_json=row.entities_json,
                extraction_method=row.extraction_method,
                source_conversation_id=row.source_conversation_id,
                source_message_id=row.source_message_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                user_note=row.user_note,
                tags_json=row.tags_json,
                is_favorite=row.is_favorite,
                revisit_count=row.revisit_count,
                last_revisited=row.last_revisited,
                emotional_tone=row.emotional_tone,
                memory_type=row.memory_type,
                content_type=row.content_type,
                conversation_title=row.conversation_title,
                conversation_summary=row.conversation_summary,
                turn_range=row.turn_range,
                key_moments_json=row.key_moments_json,
                temporal_metadata=row.temporal_metadata,
                language=row.language,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user memories with optional filters."""
        stmt = select(func.count()).select_from(ams_user_memories)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_user_memories.c.user_id == filters['user_id'])
            if 'category' in filters:
                conditions.append(ams_user_memories.c.category == filters['category'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_favorites_for_user(self, user_id: str, limit: int = 50) -> List[AMSUserMemory]:
        """Get favorite memories for a user."""
        stmt = select(ams_user_memories).where(
            and_(
                ams_user_memories.c.user_id == user_id,
                ams_user_memories.c.is_favorite == True
            )
        ).order_by(ams_user_memories.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AMSUserMemory(
                fact_id=row.fact_id,
                user_id=row.user_id,
                fact_type=row.fact_type,
                category=row.category,
                confidence=row.confidence,
                is_immutable=row.is_immutable,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                content=row.content,
                entities_json=row.entities_json,
                extraction_method=row.extraction_method,
                source_conversation_id=row.source_conversation_id,
                source_message_id=row.source_message_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                user_note=row.user_note,
                tags_json=row.tags_json,
                is_favorite=row.is_favorite,
                revisit_count=row.revisit_count,
                last_revisited=row.last_revisited,
                emotional_tone=row.emotional_tone,
                memory_type=row.memory_type,
                content_type=row.content_type,
                conversation_title=row.conversation_title,
                conversation_summary=row.conversation_summary,
                turn_range=row.turn_range,
                key_moments_json=row.key_moments_json,
                temporal_metadata=row.temporal_metadata,
                language=row.language,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_category(self, user_id: str, category: str, limit: int = 50) -> List[AMSUserMemory]:
        """Get memories by category for a user."""
        stmt = select(ams_user_memories).where(
            and_(
                ams_user_memories.c.user_id == user_id,
                ams_user_memories.c.category == category
            )
        ).order_by(ams_user_memories.c.confidence.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AMSUserMemory(
                fact_id=row.fact_id,
                user_id=row.user_id,
                fact_type=row.fact_type,
                category=row.category,
                confidence=row.confidence,
                is_immutable=row.is_immutable,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                content=row.content,
                entities_json=row.entities_json,
                extraction_method=row.extraction_method,
                source_conversation_id=row.source_conversation_id,
                source_message_id=row.source_message_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                user_note=row.user_note,
                tags_json=row.tags_json,
                is_favorite=row.is_favorite,
                revisit_count=row.revisit_count,
                last_revisited=row.last_revisited,
                emotional_tone=row.emotional_tone,
                memory_type=row.memory_type,
                content_type=row.content_type,
                conversation_title=row.conversation_title,
                conversation_summary=row.conversation_summary,
                turn_range=row.turn_range,
                key_moments_json=row.key_moments_json,
                temporal_metadata=row.temporal_metadata,
                language=row.language,
            )
            for row in result.fetchall()
        ]
