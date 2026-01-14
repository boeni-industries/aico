"""
EthicsValueProfilesRepository - PostgreSQL implementation

Handles CRUD operations for ethics value profiles.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ethics.models import EthicsValueProfile
from aico.data.tables import ethics_value_profiles
from aico.data.repositories.base import Repository


class PostgresEthicsValueProfilesRepository(Repository[EthicsValueProfile]):
    """PostgreSQL implementation of ethics value profiles repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EthicsValueProfile) -> EthicsValueProfile:
        """Create a new value profile."""
        stmt = ethics_value_profiles.insert().values(
            profile_id=entity.profile_id,
            user_id=entity.user_id,
            sensitive_life_areas=entity.sensitive_life_areas,
            allowed_curiosity_domains=entity.allowed_curiosity_domains,
            curiosity_intensity=entity.curiosity_intensity,
            proactive_behavior_level=entity.proactive_behavior_level,
            storage_preferences=entity.storage_preferences,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[EthicsValueProfile]:
        """Get value profile by ID."""
        stmt = select(ethics_value_profiles).where(ethics_value_profiles.c.profile_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsValueProfile(
            profile_id=row.profile_id,
            user_id=row.user_id,
            sensitive_life_areas=row.sensitive_life_areas,
            allowed_curiosity_domains=row.allowed_curiosity_domains,
            curiosity_intensity=row.curiosity_intensity,
            proactive_behavior_level=row.proactive_behavior_level,
            storage_preferences=row.storage_preferences,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: EthicsValueProfile) -> EthicsValueProfile:
        """Update an existing value profile."""
        stmt = (
            update(ethics_value_profiles)
            .where(ethics_value_profiles.c.profile_id == entity.profile_id)
            .values(
                sensitive_life_areas=entity.sensitive_life_areas,
                allowed_curiosity_domains=entity.allowed_curiosity_domains,
                curiosity_intensity=entity.curiosity_intensity,
                proactive_behavior_level=entity.proactive_behavior_level,
                storage_preferences=entity.storage_preferences,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a value profile."""
        stmt = delete(ethics_value_profiles).where(ethics_value_profiles.c.profile_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EthicsValueProfile]:
        """List value profiles with optional filters."""
        stmt = select(ethics_value_profiles)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_value_profiles.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ethics_value_profiles.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EthicsValueProfile(
                profile_id=row.profile_id,
                user_id=row.user_id,
                sensitive_life_areas=row.sensitive_life_areas,
                allowed_curiosity_domains=row.allowed_curiosity_domains,
                curiosity_intensity=row.curiosity_intensity,
                proactive_behavior_level=row.proactive_behavior_level,
                storage_preferences=row.storage_preferences,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count value profiles with optional filters."""
        stmt = select(func.count()).select_from(ethics_value_profiles)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_value_profiles.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_user_id(self, user_id: str) -> Optional[EthicsValueProfile]:
        """Get value profile by user ID."""
        stmt = select(ethics_value_profiles).where(ethics_value_profiles.c.user_id == user_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsValueProfile(
            profile_id=row.profile_id,
            user_id=row.user_id,
            sensitive_life_areas=row.sensitive_life_areas,
            allowed_curiosity_domains=row.allowed_curiosity_domains,
            curiosity_intensity=row.curiosity_intensity,
            proactive_behavior_level=row.proactive_behavior_level,
            storage_preferences=row.storage_preferences,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
