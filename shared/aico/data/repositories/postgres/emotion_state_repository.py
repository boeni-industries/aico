"""
EmotionStateRepository - PostgreSQL implementation

Handles CRUD operations for emotion state.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.emotion.models import EmotionState
from aico.data.tables import emotion_state
from aico.data.repositories.base import Repository


class PostgresEmotionStateRepository(Repository[EmotionState]):
    """PostgreSQL implementation of emotion state repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EmotionState) -> EmotionState:
        """Create a new emotion state."""
        stmt = emotion_state.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            timestamp=entity.timestamp,
            subjective_feeling=entity.subjective_feeling,
            mood_valence=entity.mood_valence,
            mood_arousal=entity.mood_arousal,
            intensity=entity.intensity,
            warmth=entity.warmth,
            directness=entity.directness,
            formality=entity.formality,
            engagement=entity.engagement,
            closeness=entity.closeness,
            care_focus=entity.care_focus,
            updated_at=entity.updated_at or datetime.now(UTC).isoformat(),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: int) -> Optional[EmotionState]:
        """Get emotion state by ID."""
        stmt = select(emotion_state).where(emotion_state.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EmotionState(
            id=row.id,
            user_id=row.user_id,
            timestamp=row.timestamp,
            subjective_feeling=row.subjective_feeling,
            mood_valence=row.mood_valence,
            mood_arousal=row.mood_arousal,
            intensity=row.intensity,
            warmth=row.warmth,
            directness=row.directness,
            formality=row.formality,
            engagement=row.engagement,
            closeness=row.closeness,
            care_focus=row.care_focus,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: EmotionState) -> EmotionState:
        """Update an existing emotion state."""
        stmt = (
            update(emotion_state)
            .where(emotion_state.c.id == entity.id)
            .values(
                timestamp=entity.timestamp,
                subjective_feeling=entity.subjective_feeling,
                mood_valence=entity.mood_valence,
                mood_arousal=entity.mood_arousal,
                intensity=entity.intensity,
                warmth=entity.warmth,
                directness=entity.directness,
                formality=entity.formality,
                engagement=entity.engagement,
                closeness=entity.closeness,
                care_focus=entity.care_focus,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: int) -> bool:
        """Delete an emotion state."""
        stmt = delete(emotion_state).where(emotion_state.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EmotionState]:
        """List emotion states with optional filters."""
        stmt = select(emotion_state)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(emotion_state.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(emotion_state.c.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EmotionState(
                id=row.id,
                user_id=row.user_id,
                timestamp=row.timestamp,
                subjective_feeling=row.subjective_feeling,
                mood_valence=row.mood_valence,
                mood_arousal=row.mood_arousal,
                intensity=row.intensity,
                warmth=row.warmth,
                directness=row.directness,
                formality=row.formality,
                engagement=row.engagement,
                closeness=row.closeness,
                care_focus=row.care_focus,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count emotion states with optional filters."""
        stmt = select(func.count()).select_from(emotion_state)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(emotion_state.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_current_state(self) -> Optional[EmotionState]:
        """Get the current emotion state (id=1)."""
        return await self.get_by_id(1)
