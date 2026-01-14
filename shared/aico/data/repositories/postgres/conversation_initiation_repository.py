"""
ConversationInitiationRepository - PostgreSQL implementation

Handles CRUD operations for conversation initiations.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.conversation.models import ConversationInitiation
from aico.data.tables import conversation_initiations
from aico.data.repositories.base import Repository


class PostgresConversationInitiationRepository(Repository[ConversationInitiation]):
    """PostgreSQL implementation of conversation initiation repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ConversationInitiation) -> ConversationInitiation:
        """Create a new conversation initiation."""
        stmt = conversation_initiations.insert().values(
            initiation_id=entity.initiation_id,
            user_id=entity.user_id,
            conversation_id=entity.conversation_id,
            trigger_source=entity.trigger_source,
            trigger_reason=entity.trigger_reason,
            question=entity.question,
            context=entity.context,
            urgency=entity.urgency,
            expected_answer_type=entity.expected_answer_type,
            initiated_at=entity.initiated_at,
            resolved_at=entity.resolved_at,
            resolution_status=entity.resolution_status,
            user_response_time=entity.user_response_time,
            engagement_score=entity.engagement_score,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ConversationInitiation]:
        """Get conversation initiation by ID."""
        stmt = select(conversation_initiations).where(
            conversation_initiations.c.initiation_id == entity_id
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ConversationInitiation(
            initiation_id=row.initiation_id,
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            trigger_source=row.trigger_source,
            trigger_reason=row.trigger_reason,
            question=row.question,
            context=row.context,
            urgency=row.urgency,
            expected_answer_type=row.expected_answer_type,
            initiated_at=row.initiated_at,
            resolved_at=row.resolved_at,
            resolution_status=row.resolution_status,
            user_response_time=row.user_response_time,
            engagement_score=row.engagement_score,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: ConversationInitiation) -> ConversationInitiation:
        """Update an existing conversation initiation."""
        stmt = (
            update(conversation_initiations)
            .where(conversation_initiations.c.initiation_id == entity.initiation_id)
            .values(
                resolved_at=entity.resolved_at,
                resolution_status=entity.resolution_status,
                user_response_time=entity.user_response_time,
                engagement_score=entity.engagement_score,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a conversation initiation."""
        stmt = delete(conversation_initiations).where(
            conversation_initiations.c.initiation_id == entity_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ConversationInitiation]:
        """List conversation initiations with optional filters."""
        stmt = select(conversation_initiations)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(conversation_initiations.c.user_id == filters['user_id'])
            if 'conversation_id' in filters:
                conditions.append(conversation_initiations.c.conversation_id == filters['conversation_id'])
            if 'resolution_status' in filters:
                conditions.append(conversation_initiations.c.resolution_status == filters['resolution_status'])
            if 'trigger_source' in filters:
                conditions.append(conversation_initiations.c.trigger_source == filters['trigger_source'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(conversation_initiations.c.initiated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ConversationInitiation(
                initiation_id=row.initiation_id,
                user_id=row.user_id,
                conversation_id=row.conversation_id,
                trigger_source=row.trigger_source,
                trigger_reason=row.trigger_reason,
                question=row.question,
                context=row.context,
                urgency=row.urgency,
                expected_answer_type=row.expected_answer_type,
                initiated_at=row.initiated_at,
                resolved_at=row.resolved_at,
                resolution_status=row.resolution_status,
                user_response_time=row.user_response_time,
                engagement_score=row.engagement_score,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count conversation initiations with optional filters."""
        stmt = select(func.count()).select_from(conversation_initiations)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(conversation_initiations.c.user_id == filters['user_id'])
            if 'resolution_status' in filters:
                conditions.append(conversation_initiations.c.resolution_status == filters['resolution_status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_pending_for_user(self, user_id: str) -> List[ConversationInitiation]:
        """Get all pending initiations for a user."""
        stmt = select(conversation_initiations).where(
            and_(
                conversation_initiations.c.user_id == user_id,
                conversation_initiations.c.resolution_status == 'pending'
            )
        ).order_by(conversation_initiations.c.initiated_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ConversationInitiation(
                initiation_id=row.initiation_id,
                user_id=row.user_id,
                conversation_id=row.conversation_id,
                trigger_source=row.trigger_source,
                trigger_reason=row.trigger_reason,
                question=row.question,
                context=row.context,
                urgency=row.urgency,
                expected_answer_type=row.expected_answer_type,
                initiated_at=row.initiated_at,
                resolved_at=row.resolved_at,
                resolution_status=row.resolution_status,
                user_response_time=row.user_response_time,
                engagement_score=row.engagement_score,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def resolve_initiation(self, initiation_id: str, engagement_score: Optional[float] = None) -> bool:
        """Mark an initiation as resolved."""
        values = {
            'resolved_at': datetime.now(UTC),
            'resolution_status': 'resolved',
            'updated_at': datetime.now(UTC),
        }
        
        if engagement_score is not None:
            values['engagement_score'] = engagement_score
        
        stmt = (
            update(conversation_initiations)
            .where(conversation_initiations.c.initiation_id == initiation_id)
            .values(**values)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
