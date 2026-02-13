"""
EmotionHistoryRepository - PostgreSQL implementation

Handles CRUD operations for emotion history.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.emotion.models import EmotionHistory
from aico.data.tables import emotion_history
from aico.data.repositories.base import Repository


class PostgresEmotionHistoryRepository(Repository[EmotionHistory]):
    """PostgreSQL implementation of emotion history repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EmotionHistory) -> EmotionHistory:
        """Create a new emotion history entry."""
        stmt = emotion_history.insert().values(
            user_id=entity.user_id,
            timestamp=entity.timestamp,
            feeling=entity.feeling,
            valence=entity.valence,
            arousal=entity.arousal,
            intensity=entity.intensity,
            created_at=entity.created_at or datetime.now(UTC),
        ).returning(emotion_history.c.id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        entity.id = row.id
        return entity
    
    async def get_by_id(self, entity_id: int) -> Optional[EmotionHistory]:
        """Get emotion history by ID."""
        stmt = select(emotion_history).where(emotion_history.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EmotionHistory(
            id=row.id,
            user_id=row.user_id,
            timestamp=row.timestamp,
            feeling=row.feeling,
            valence=row.valence,
            arousal=row.arousal,
            intensity=row.intensity,
            created_at=row.created_at,
        )
    
    async def update(self, entity: EmotionHistory) -> EmotionHistory:
        """Update an existing emotion history entry."""
        stmt = (
            update(emotion_history)
            .where(emotion_history.c.id == entity.id)
            .values(
                feeling=entity.feeling,
                valence=entity.valence,
                arousal=entity.arousal,
                intensity=entity.intensity,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: int) -> bool:
        """Delete an emotion history entry."""
        stmt = delete(emotion_history).where(emotion_history.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EmotionHistory]:
        """List emotion history with optional filters."""
        stmt = select(emotion_history)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(emotion_history.c.user_id == filters['user_id'])
            if 'feeling' in filters:
                conditions.append(emotion_history.c.feeling == filters['feeling'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(emotion_history.c.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EmotionHistory(
                id=row.id,
                user_id=row.user_id,
                timestamp=row.timestamp,
                feeling=row.feeling,
                valence=row.valence,
                arousal=row.arousal,
                intensity=row.intensity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count emotion history entries with optional filters."""
        stmt = select(func.count()).select_from(emotion_history)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(emotion_history.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_recent_for_user(self, user_id: str, limit: int = 50) -> List[EmotionHistory]:
        """Get recent emotion history for a user."""
        stmt = select(emotion_history).where(
            emotion_history.c.user_id == user_id
        ).order_by(emotion_history.c.timestamp.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            EmotionHistory(
                id=row.id,
                user_id=row.user_id,
                timestamp=row.timestamp,
                feeling=row.feeling,
                valence=row.valence,
                arousal=row.arousal,
                intensity=row.intensity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_feeling(self, user_id: str, feeling: str, limit: int = 50) -> List[EmotionHistory]:
        """Get emotion history by feeling type for a user."""
        stmt = select(emotion_history).where(
            and_(
                emotion_history.c.user_id == user_id,
                emotion_history.c.feeling == feeling
            )
        ).order_by(emotion_history.c.timestamp.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            EmotionHistory(
                id=row.id,
                user_id=row.user_id,
                timestamp=row.timestamp,
                feeling=row.feeling,
                valence=row.valence,
                arousal=row.arousal,
                intensity=row.intensity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
