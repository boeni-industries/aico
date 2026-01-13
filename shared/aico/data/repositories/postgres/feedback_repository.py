"""
FeedbackRepository - PostgreSQL implementation

Handles CRUD operations for AMS feedback.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.models import Feedback
from aico.data.tables import ams_feedback
from aico.data.repositories.base import Repository


class PostgresFeedbackRepository(Repository[Feedback]):
    """PostgreSQL implementation of feedback repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Feedback) -> Feedback:
        """Create a new feedback entry."""
        stmt = ams_feedback.insert().values(
            feedback_id=entity.feedback_id,
            user_id=entity.user_id,
            trajectory_id=entity.trajectory_id,
            feedback_type=entity.feedback_type,
            content=entity.content,
            rating=entity.rating,
            metadata_json=entity.metadata_json,
            created_at=entity.created_at or datetime.now(UTC),
            processed_at=entity.processed_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Feedback]:
        """Get feedback by ID."""
        stmt = select(ams_feedback).where(ams_feedback.c.feedback_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Feedback(
            feedback_id=row.feedback_id,
            user_id=row.user_id,
            trajectory_id=row.trajectory_id,
            feedback_type=row.feedback_type,
            content=row.content,
            rating=row.rating,
            metadata_json=row.metadata_json,
            created_at=row.created_at,
            processed_at=row.processed_at,
        )
    
    async def update(self, entity: Feedback) -> Feedback:
        """Update an existing feedback entry."""
        stmt = (
            update(ams_feedback)
            .where(ams_feedback.c.feedback_id == entity.feedback_id)
            .values(
                content=entity.content,
                rating=entity.rating,
                metadata_json=entity.metadata_json,
                processed_at=entity.processed_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a feedback entry."""
        stmt = delete(ams_feedback).where(ams_feedback.c.feedback_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Feedback]:
        """List feedback with optional filters."""
        stmt = select(ams_feedback)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_feedback.c.user_id == filters['user_id'])
            if 'trajectory_id' in filters:
                conditions.append(ams_feedback.c.trajectory_id == filters['trajectory_id'])
            if 'feedback_type' in filters:
                conditions.append(ams_feedback.c.feedback_type == filters['feedback_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_feedback.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Feedback(
                feedback_id=row.feedback_id,
                user_id=row.user_id,
                trajectory_id=row.trajectory_id,
                feedback_type=row.feedback_type,
                content=row.content,
                rating=row.rating,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                processed_at=row.processed_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count feedback with optional filters."""
        stmt = select(func.count()).select_from(ams_feedback)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_feedback.c.user_id == filters['user_id'])
            if 'feedback_type' in filters:
                conditions.append(ams_feedback.c.feedback_type == filters['feedback_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_unprocessed_feedback(self, user_id: Optional[str] = None) -> List[Feedback]:
        """Get all unprocessed feedback, optionally filtered by user."""
        conditions = [ams_feedback.c.processed_at.is_(None)]
        
        if user_id:
            conditions.append(ams_feedback.c.user_id == user_id)
        
        stmt = select(ams_feedback).where(
            and_(*conditions)
        ).order_by(ams_feedback.c.created_at.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            Feedback(
                feedback_id=row.feedback_id,
                user_id=row.user_id,
                trajectory_id=row.trajectory_id,
                feedback_type=row.feedback_type,
                content=row.content,
                rating=row.rating,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                processed_at=row.processed_at,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_processed(self, feedback_id: str) -> bool:
        """Mark feedback as processed."""
        stmt = (
            update(ams_feedback)
            .where(ams_feedback.c.feedback_id == feedback_id)
            .values(processed_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
