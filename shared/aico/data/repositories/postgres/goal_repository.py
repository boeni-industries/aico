"""
GoalRepository - PostgreSQL implementation

Handles CRUD operations for agency goals.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, GoalStatus
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
            origin=entity.origin.value if isinstance(entity.origin, GoalOrigin) else entity.origin,
            goal_type=entity.goal_type,
            title=entity.title,
            description=entity.description,
            status=entity.status.value if isinstance(entity.status, GoalStatus) else entity.status,
            priority=entity.priority.value if isinstance(entity.priority, GoalPriority) else entity.priority,
            metadata_json=entity.metadata if entity.metadata else None,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        stmt = select(agency_goals).where(agency_goals.c.goal_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Parse metadata_json if it's a string, otherwise use as-is
        metadata = row.metadata_json if row.metadata_json else {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        return Goal(
            goal_id=row.goal_id,
            user_id=row.user_id,
            origin=GoalOrigin(row.origin),
            goal_type=row.goal_type,
            title=row.title,
            description=row.description,
            status=GoalStatus(row.status),
            priority=GoalPriority(row.priority),
            metadata=metadata,
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
                status=entity.status.value if isinstance(entity.status, GoalStatus) else entity.status,
                priority=entity.priority.value if isinstance(entity.priority, GoalPriority) else entity.priority,
                metadata_json=entity.metadata if entity.metadata else None,
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
        
        goals = []
        for row in rows:
            # Parse metadata_json if it's a string, otherwise use as-is
            metadata = row.metadata_json if row.metadata_json else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            goals.append(Goal(
                goal_id=row.goal_id,
                user_id=row.user_id,
                origin=GoalOrigin(row.origin),
                goal_type=row.goal_type,
                title=row.title,
                description=row.description,
                status=GoalStatus(row.status),
                priority=GoalPriority(row.priority),
                metadata=metadata,
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))
        
        return goals
    
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

    async def find_by_curiosity_signal_id(self, signal_id: str) -> Optional[Goal]:
        """Find a goal created from a specific curiosity signal, if any.

        Uses metadata_json->>'curiosity_signal_id' for lookup.
        """
        stmt = (
            select(agency_goals)
            .where(agency_goals.c.metadata_json["curiosity_signal_id"].astext == signal_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if not row:
            return None

        # Parse metadata_json if it's a string, otherwise use as-is
        metadata = row.metadata_json if row.metadata_json else {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Goal(
            goal_id=row.goal_id,
            user_id=row.user_id,
            origin=GoalOrigin(row.origin),
            goal_type=row.goal_type,
            title=row.title,
            description=row.description,
            status=GoalStatus(row.status),
            priority=GoalPriority(row.priority),
            metadata=metadata,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def find_open_goal_by_title(self, user_id: str, origin: str, title: str) -> Optional[Goal]:
        """Find an open goal for a user by origin and title.

        Open means status in (pending, active, in_progress).
        """
        stmt = (
            select(agency_goals)
            .where(
                and_(
                    agency_goals.c.user_id == user_id,
                    agency_goals.c.origin == origin,
                    agency_goals.c.title == title,
                    agency_goals.c.status.in_(["pending", "active", "in_progress"]),
                )
            )
            .order_by(agency_goals.c.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if not row:
            return None

        # Parse metadata_json if it's a string, otherwise use as-is
        metadata = row.metadata_json if row.metadata_json else {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Goal(
            goal_id=row.goal_id,
            user_id=row.user_id,
            origin=GoalOrigin(row.origin),
            goal_type=row.goal_type,
            title=row.title,
            description=row.description,
            status=GoalStatus(row.status),
            priority=GoalPriority(row.priority),
            metadata=metadata,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def get_active_goals_for_user(self, user_id: str) -> List[Goal]:
        """Get all active goals for a user."""
        stmt = select(agency_goals).where(
            and_(
                agency_goals.c.user_id == user_id,
                agency_goals.c.status.in_(['active', 'in_progress'])
            )
        ).order_by(agency_goals.c.priority.desc(), agency_goals.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        goals = []
        for row in result.fetchall():
            # Parse metadata_json if it's a string, otherwise use as-is
            metadata = row.metadata_json if row.metadata_json else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            goals.append(Goal(
                goal_id=row.goal_id,
                user_id=row.user_id,
                origin=GoalOrigin(row.origin),
                goal_type=row.goal_type,
                title=row.title,
                description=row.description,
                status=GoalStatus(row.status),
                priority=GoalPriority(row.priority),
                metadata=metadata,
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))
        
        return goals
    
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
