"""
LessonRepository - PostgreSQL implementation

Handles CRUD operations for agency lessons.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.models import Lesson
from aico.data.tables import agency_lessons
from aico.data.repositories.base import Repository


class PostgresLessonRepository(Repository[Lesson]):
    """PostgreSQL implementation of lesson repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Lesson) -> Lesson:
        """Create a new lesson."""
        stmt = agency_lessons.insert().values(
            lesson_id=entity.lesson_id,
            user_id=entity.user_id,
            lesson_type=entity.lesson_type,
            content=entity.content,
            confidence=entity.confidence,
            status=entity.status,
            source_data=entity.source_data,
            superseded_by=entity.superseded_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Lesson]:
        """Get lesson by ID."""
        stmt = select(agency_lessons).where(agency_lessons.c.lesson_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Lesson(
            lesson_id=row.lesson_id,
            user_id=row.user_id,
            lesson_type=row.lesson_type,
            content=row.content,
            confidence=row.confidence,
            status=row.status,
            source_data=row.source_data,
            superseded_by=row.superseded_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Lesson) -> Lesson:
        """Update an existing lesson."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == entity.lesson_id)
            .values(
                content=entity.content,
                confidence=entity.confidence,
                status=entity.status,
                source_data=entity.source_data,
                superseded_by=entity.superseded_by,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a lesson."""
        stmt = delete(agency_lessons).where(agency_lessons.c.lesson_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Lesson]:
        """List lessons with optional filters."""
        stmt = select(agency_lessons)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_lessons.c.user_id == filters['user_id'])
            if 'lesson_type' in filters:
                conditions.append(agency_lessons.c.lesson_type == filters['lesson_type'])
            if 'status' in filters:
                conditions.append(agency_lessons.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_lessons.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Lesson(
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                lesson_type=row.lesson_type,
                content=row.content,
                confidence=row.confidence,
                status=row.status,
                source_data=row.source_data,
                superseded_by=row.superseded_by,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count lessons with optional filters."""
        stmt = select(func.count()).select_from(agency_lessons)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_lessons.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_lessons.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_lessons_for_user(self, user_id: str, lesson_type: Optional[str] = None) -> List[Lesson]:
        """Get active lessons for a user, optionally filtered by type."""
        conditions = [
            agency_lessons.c.user_id == user_id,
            agency_lessons.c.status == 'active',
            agency_lessons.c.superseded_by.is_(None)
        ]
        
        if lesson_type:
            conditions.append(agency_lessons.c.lesson_type == lesson_type)
        
        stmt = select(agency_lessons).where(
            and_(*conditions)
        ).order_by(agency_lessons.c.confidence.desc(), agency_lessons.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Lesson(
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                lesson_type=row.lesson_type,
                content=row.content,
                confidence=row.confidence,
                status=row.status,
                source_data=row.source_data,
                superseded_by=row.superseded_by,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def supersede_lesson(self, old_lesson_id: str, new_lesson_id: str) -> bool:
        """Mark a lesson as superseded by a newer lesson."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == old_lesson_id)
            .values(
                superseded_by=new_lesson_id,
                status='superseded',
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def update_confidence(self, lesson_id: str, new_confidence: float) -> bool:
        """Update lesson confidence score."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == lesson_id)
            .values(
                confidence=new_confidence,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
