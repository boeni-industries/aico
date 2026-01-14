"""
AMSBehavioralSkillsRepository - PostgreSQL implementation

Handles CRUD operations for AMS behavioral skills.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.ams.models import BehavioralSkill
from aico.data.tables import ams_behavioral_skills
from aico.data.repositories.base import Repository


class PostgresAMSBehavioralSkillsRepository(Repository[BehavioralSkill]):
    """PostgreSQL implementation of AMS behavioral skills repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: BehavioralSkill) -> BehavioralSkill:
        """Create a new behavioral skill."""
        stmt = ams_behavioral_skills.insert().values(
            skill_id=entity.skill_id,
            skill_name=entity.skill_name,
            skill_type=entity.skill_type,
            trigger_context=entity.trigger_context,
            procedure_template=entity.procedure_template,
            dimension_vector=entity.dimension_vector,
            supported_languages=entity.supported_languages,
            status=entity.status,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[BehavioralSkill]:
        """Get behavioral skill by ID."""
        stmt = select(ams_behavioral_skills).where(ams_behavioral_skills.c.skill_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return BehavioralSkill(
            skill_id=row.skill_id,
            skill_name=row.skill_name,
            skill_type=row.skill_type,
            trigger_context=row.trigger_context,
            procedure_template=row.procedure_template,
            dimension_vector=row.dimension_vector,
            supported_languages=row.supported_languages,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: BehavioralSkill) -> BehavioralSkill:
        """Update an existing behavioral skill."""
        stmt = (
            update(ams_behavioral_skills)
            .where(ams_behavioral_skills.c.skill_id == entity.skill_id)
            .values(
                skill_name=entity.skill_name,
                trigger_context=entity.trigger_context,
                procedure_template=entity.procedure_template,
                dimension_vector=entity.dimension_vector,
                supported_languages=entity.supported_languages,
                status=entity.status,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a behavioral skill."""
        stmt = delete(ams_behavioral_skills).where(ams_behavioral_skills.c.skill_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[BehavioralSkill]:
        """List behavioral skills with optional filters."""
        stmt = select(ams_behavioral_skills)
        
        if filters:
            conditions = []
            if 'skill_type' in filters:
                conditions.append(ams_behavioral_skills.c.skill_type == filters['skill_type'])
            if 'status' in filters:
                conditions.append(ams_behavioral_skills.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_behavioral_skills.c.skill_name.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            BehavioralSkill(
                skill_id=row.skill_id,
                skill_name=row.skill_name,
                skill_type=row.skill_type,
                trigger_context=row.trigger_context,
                procedure_template=row.procedure_template,
                dimension_vector=row.dimension_vector,
                supported_languages=row.supported_languages,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count behavioral skills with optional filters."""
        stmt = select(func.count()).select_from(ams_behavioral_skills)
        
        if filters:
            conditions = []
            if 'status' in filters:
                conditions.append(ams_behavioral_skills.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_skills(self) -> List[BehavioralSkill]:
        """Get all active behavioral skills."""
        stmt = select(ams_behavioral_skills).where(
            ams_behavioral_skills.c.status == 'active'
        ).order_by(ams_behavioral_skills.c.skill_name.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            BehavioralSkill(
                skill_id=row.skill_id,
                skill_name=row.skill_name,
                skill_type=row.skill_type,
                trigger_context=row.trigger_context,
                procedure_template=row.procedure_template,
                dimension_vector=row.dimension_vector,
                supported_languages=row.supported_languages,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_skills_by_type(self, skill_type: str) -> List[BehavioralSkill]:
        """Get all skills of a specific type."""
        stmt = select(ams_behavioral_skills).where(
            ams_behavioral_skills.c.skill_type == skill_type
        ).order_by(ams_behavioral_skills.c.skill_name.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            BehavioralSkill(
                skill_id=row.skill_id,
                skill_name=row.skill_name,
                skill_type=row.skill_type,
                trigger_context=row.trigger_context,
                procedure_template=row.procedure_template,
                dimension_vector=row.dimension_vector,
                supported_languages=row.supported_languages,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
