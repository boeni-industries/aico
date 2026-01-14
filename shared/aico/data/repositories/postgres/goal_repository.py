"""
GoalRepository - PostgreSQL implementation

Handles CRUD operations for agency goals.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import Goal
from aico.data.tables import agency_goals
from aico.data.repositories.base import Repository
import json


class PostgresGoalRepository(Repository[Goal]):
    """PostgreSQL implementation of goal repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Goal) -> Goal:
        """Create a new goal."""
        stmt = agency_goals.insert().values(
            goal_id=entity.goal_id,
            user_id=entity.user_id,
            origin=entity.origin.value if hasattr(entity.origin, 'value') else entity.origin,
            goal_type=entity.goal_type,
            title=entity.title,
            description=entity.description,
            status=entity.status.value if hasattr(entity.status, 'value') else entity.status,
            priority=entity.priority.value if hasattr(entity.priority, 'value') else entity.priority,
            metadata_json=json.dumps(entity.metadata) if entity.metadata else None,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        from aico.ai.agency.models import GoalOrigin, GoalStatus, GoalPriority
        
        stmt = select(agency_goals).where(agency_goals.c.goal_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Goal(
            goal_id=row.goal_id,
            user_id=row.user_id,
            origin=GoalOrigin(row.origin),
            goal_type=row.goal_type,
            title=row.title,
            description=row.description,
            status=GoalStatus(row.status),
            priority=GoalPriority(row.priority),
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Goal) -> Goal:
        """Update an existing goal."""
        stmt = (
            update(agency_goals)
            .where(agency_goals.c.goal_id == entity.goal_id)
            .values(
                title=entity.title,
                description=entity.description,
                status=entity.status.value if hasattr(entity.status, 'value') else entity.status,
                priority=entity.priority.value if hasattr(entity.priority, 'value') else entity.priority,
                metadata_json=json.dumps(entity.metadata) if entity.metadata else None,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a goal."""
        stmt = delete(agency_goals).where(agency_goals.c.goal_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Goal]:
        """List goals with optional filters."""
        stmt = select(agency_goals)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_goals.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_goals.c.status == filters['status'])
            if 'priority' in filters:
                conditions.append(agency_goals.c.priority == filters['priority'])
            if 'origin' in filters:
                conditions.append(agency_goals.c.origin == filters['origin'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        from aico.ai.agency.models import GoalOrigin, GoalStatus, GoalPriority
        
        return [
            Goal(
                goal_id=row.goal_id,
                user_id=row.user_id,
                origin=GoalOrigin(row.origin),
                goal_type=row.goal_type,
                title=row.title,
                description=row.description,
                status=GoalStatus(row.status),
                priority=GoalPriority(row.priority),
                metadata=json.loads(row.metadata_json) if row.metadata_json else {},
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count goals with optional filters."""
        stmt = select(func.count()).select_from(agency_goals)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_goals.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_goals.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_goals_for_user(self, user_id: str) -> List[Goal]:
        """Get all active goals for a user."""
        stmt = select(agency_goals).where(
            and_(
                agency_goals.c.user_id == user_id,
                agency_goals.c.status.in_(['active', 'in_progress'])
            )
        ).order_by(agency_goals.c.priority.desc(), agency_goals.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Goal(
                goal_id=row.goal_id,
                user_id=row.user_id,
                origin=row.origin,
                goal_type=row.goal_type,
                title=row.title,
                description=row.description,
                status=row.status,
                priority=row.priority,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def update_status(self, goal_id: str, new_status: str) -> bool:
        """Update goal status."""
        stmt = (
            update(agency_goals)
            .where(agency_goals.c.goal_id == goal_id)
            .values(
                status=new_status,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
