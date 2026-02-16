"""
ArbiterBanditArmsRepository - PostgreSQL implementation

Handles CRUD operations for arbiter bandit arms.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.arbiter.models import ArbiterBanditArm
from aico.data.tables import arbiter_bandit_arms
from aico.data.repositories.base import Repository


class PostgresArbiterBanditArmsRepository(Repository[ArbiterBanditArm]):
    """PostgreSQL implementation of arbiter bandit arms repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ArbiterBanditArm) -> ArbiterBanditArm:
        """Create a new bandit arm."""
        stmt = arbiter_bandit_arms.insert().values(
            arm_id=entity.arm_id,
            weights_json=entity.weights_json,
            pulls=entity.pulls,
            total_reward=entity.total_reward,
            success_count=entity.success_count,
            failure_count=entity.failure_count,
            last_pulled=entity.last_pulled,
            active=entity.active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ArbiterBanditArm]:
        """Get bandit arm by ID."""
        stmt = select(arbiter_bandit_arms).where(arbiter_bandit_arms.c.arm_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ArbiterBanditArm(
            arm_id=row.arm_id,
            weights_json=row.weights_json,
            pulls=row.pulls,
            total_reward=row.total_reward,
            success_count=row.success_count,
            failure_count=row.failure_count,
            last_pulled=row.last_pulled,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: ArbiterBanditArm) -> ArbiterBanditArm:
        """Update an existing bandit arm."""
        stmt = (
            update(arbiter_bandit_arms)
            .where(arbiter_bandit_arms.c.arm_id == entity.arm_id)
            .values(
                weights_json=entity.weights_json,
                pulls=entity.pulls,
                total_reward=entity.total_reward,
                success_count=entity.success_count,
                failure_count=entity.failure_count,
                last_pulled=entity.last_pulled,
                active=entity.active,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a bandit arm."""
        stmt = delete(arbiter_bandit_arms).where(arbiter_bandit_arms.c.arm_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ArbiterBanditArm]:
        """List bandit arms with optional filters."""
        stmt = select(arbiter_bandit_arms)
        
        if filters:
            conditions = []
            if 'active' in filters:
                conditions.append(arbiter_bandit_arms.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(arbiter_bandit_arms.c.pulls.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ArbiterBanditArm(
                arm_id=row.arm_id,
                weights_json=row.weights_json,
                pulls=row.pulls,
                total_reward=row.total_reward,
                success_count=row.success_count,
                failure_count=row.failure_count,
                last_pulled=row.last_pulled,
                active=row.active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count bandit arms with optional filters."""
        stmt = select(func.count()).select_from(arbiter_bandit_arms)
        
        if filters:
            conditions = []
            if 'active' in filters:
                conditions.append(arbiter_bandit_arms.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_arms(self) -> List[ArbiterBanditArm]:
        """Get all active bandit arms."""
        stmt = select(arbiter_bandit_arms).where(
            arbiter_bandit_arms.c.active == True
        ).order_by(arbiter_bandit_arms.c.pulls.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ArbiterBanditArm(
                arm_id=row.arm_id,
                weights_json=row.weights_json,
                pulls=row.pulls,
                total_reward=row.total_reward,
                success_count=row.success_count,
                failure_count=row.failure_count,
                last_pulled=row.last_pulled,
                active=row.active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
