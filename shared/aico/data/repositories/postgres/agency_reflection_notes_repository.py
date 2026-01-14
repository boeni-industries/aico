"""
AgencyReflectionNotesRepository - PostgreSQL implementation

Handles CRUD operations for agency reflection notes.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.models import AgencyReflectionNote
from aico.data.tables import agency_reflection_notes
from aico.data.repositories.base import Repository

import json

class PostgresAgencyReflectionNotesRepository(Repository[AgencyReflectionNote]):
    """PostgreSQL implementation of agency reflection notes repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyReflectionNote) -> AgencyReflectionNote:
        """Create a new reflection note."""
        stmt = agency_reflection_notes.insert().values(
            note_id=entity.note_id,
            user_id=entity.user_id,
            related_goal_id=entity.related_goal_id,
            related_plan_id=entity.related_plan_id,
            title=entity.title,
            content=entity.content,
            tags_json=json.dumps(entity.tags) if entity.tags else None,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AgencyReflectionNote]:
        """Get reflection note by ID."""
        stmt = select(agency_reflection_notes).where(agency_reflection_notes.c.note_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyReflectionNote(
            note_id=row.note_id,
            user_id=row.user_id,
            related_goal_id=row.related_goal_id,
            related_plan_id=row.related_plan_id,
            title=row.title,
            content=row.content,
            tags=json.loads(row.tags_json) if row.tags_json else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AgencyReflectionNote) -> AgencyReflectionNote:
        """Update an existing reflection note."""
        stmt = (
            update(agency_reflection_notes)
            .where(agency_reflection_notes.c.note_id == entity.note_id)
            .values(
                title=entity.title,
                content=entity.content,
                tags_json=json.dumps(entity.tags) if entity.tags else None,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a reflection note."""
        stmt = delete(agency_reflection_notes).where(agency_reflection_notes.c.note_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyReflectionNote]:
        """List reflection notes with optional filters."""
        stmt = select(agency_reflection_notes)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_reflection_notes.c.user_id == filters['user_id'])
            if 'related_goal_id' in filters:
                conditions.append(agency_reflection_notes.c.related_goal_id == filters['related_goal_id'])
            if 'related_plan_id' in filters:
                conditions.append(agency_reflection_notes.c.related_plan_id == filters['related_plan_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_reflection_notes.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyReflectionNote(
                note_id=row.note_id,
                user_id=row.user_id,
                related_goal_id=row.related_goal_id,
                related_plan_id=row.related_plan_id,
                title=row.title,
                content=row.content,
                tags_json=row.tags_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count reflection notes with optional filters."""
        stmt = select(func.count()).select_from(agency_reflection_notes)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_reflection_notes.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_notes_for_goal(self, goal_id: str, limit: int = 50) -> List[AgencyReflectionNote]:
        """Get all reflection notes for a specific goal."""
        stmt = select(agency_reflection_notes).where(
            agency_reflection_notes.c.related_goal_id == goal_id
        ).order_by(agency_reflection_notes.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyReflectionNote(
                note_id=row.note_id,
                user_id=row.user_id,
                related_goal_id=row.related_goal_id,
                related_plan_id=row.related_plan_id,
                title=row.title,
                content=row.content,
                tags_json=row.tags_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_recent_notes_for_user(self, user_id: str, limit: int = 20) -> List[AgencyReflectionNote]:
        """Get recent reflection notes for a user."""
        stmt = select(agency_reflection_notes).where(
            agency_reflection_notes.c.user_id == user_id
        ).order_by(agency_reflection_notes.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyReflectionNote(
                note_id=row.note_id,
                user_id=row.user_id,
                related_goal_id=row.related_goal_id,
                related_plan_id=row.related_plan_id,
                title=row.title,
                content=row.content,
                tags_json=row.tags_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
