"""
TrajectoryRepository - PostgreSQL implementation

Handles CRUD operations for AMS trajectories.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.models import Trajectory
from aico.data.tables import ams_trajectories
from aico.data.repositories.base import Repository


class PostgresTrajectoryRepository(Repository[Trajectory]):
    """PostgreSQL implementation of trajectory repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Trajectory) -> Trajectory:
        """Create a new trajectory."""
        stmt = ams_trajectories.insert().values(
            trajectory_id=entity.trajectory_id,
            user_id=entity.user_id,
            goal_id=entity.goal_id,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status,
            outcome=entity.outcome,
            metadata_json=entity.metadata_json,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Trajectory]:
        """Get trajectory by ID."""
        stmt = select(ams_trajectories).where(ams_trajectories.c.trajectory_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Trajectory(
            trajectory_id=row.trajectory_id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            start_time=row.start_time,
            end_time=row.end_time,
            status=row.status,
            outcome=row.outcome,
            metadata_json=row.metadata_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Trajectory) -> Trajectory:
        """Update an existing trajectory."""
        stmt = (
            update(ams_trajectories)
            .where(ams_trajectories.c.trajectory_id == entity.trajectory_id)
            .values(
                end_time=entity.end_time,
                status=entity.status,
                outcome=entity.outcome,
                metadata_json=entity.metadata_json,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a trajectory."""
        stmt = delete(ams_trajectories).where(ams_trajectories.c.trajectory_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Trajectory]:
        """List trajectories with optional filters."""
        stmt = select(ams_trajectories)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_trajectories.c.user_id == filters['user_id'])
            if 'goal_id' in filters:
                conditions.append(ams_trajectories.c.goal_id == filters['goal_id'])
            if 'status' in filters:
                conditions.append(ams_trajectories.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_trajectories.c.start_time.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Trajectory(
                trajectory_id=row.trajectory_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                start_time=row.start_time,
                end_time=row.end_time,
                status=row.status,
                outcome=row.outcome,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count trajectories with optional filters."""
        stmt = select(func.count()).select_from(ams_trajectories)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_trajectories.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(ams_trajectories.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_trajectories_for_user(self, user_id: str) -> List[Trajectory]:
        """Get all active trajectories for a user."""
        stmt = select(ams_trajectories).where(
            and_(
                ams_trajectories.c.user_id == user_id,
                ams_trajectories.c.status == 'active'
            )
        ).order_by(ams_trajectories.c.start_time.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Trajectory(
                trajectory_id=row.trajectory_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                start_time=row.start_time,
                end_time=row.end_time,
                status=row.status,
                outcome=row.outcome,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def complete_trajectory(self, trajectory_id: str, outcome: str) -> bool:
        """Mark a trajectory as completed with an outcome."""
        stmt = (
            update(ams_trajectories)
            .where(ams_trajectories.c.trajectory_id == trajectory_id)
            .values(
                status='completed',
                outcome=outcome,
                end_time=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
