"""
AMSTrajectoriesRepository - PostgreSQL implementation

Handles CRUD operations for AMS trajectories.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.models import Trajectory
from aico.data.tables import ams_trajectories
from aico.data.repositories.base import Repository


class PostgresAMSTrajectoriesRepository(Repository[Trajectory]):
    """PostgreSQL implementation of AMS trajectories repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Trajectory) -> Trajectory:
        """Create a new trajectory."""
        stmt = ams_trajectories.insert().values(
            trajectory_id=entity.trajectory_id,
            user_id=entity.user_id,
            conversation_id=entity.conversation_id,
            selected_skill_id=entity.selected_skill_id,
            context_bucket=entity.context_bucket,
            feedback_reward=entity.feedback_reward,
            timestamp=entity.timestamp,
            archived=entity.archived,
            agency_context=entity.agency_context,
            message_id=entity.message_id,
            turn_number=entity.turn_number,
            user_input=entity.user_input,
            ai_response=entity.ai_response,
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
            conversation_id=row.conversation_id,
            selected_skill_id=row.selected_skill_id,
            context_bucket=row.context_bucket,
            feedback_reward=row.feedback_reward,
            timestamp=row.timestamp,
            archived=row.archived,
            agency_context=row.agency_context,
            message_id=row.message_id,
            turn_number=row.turn_number,
            user_input=row.user_input,
            ai_response=row.ai_response,
        )
    
    async def update(self, entity: Trajectory) -> Trajectory:
        """Update an existing trajectory."""
        stmt = (
            update(ams_trajectories)
            .where(ams_trajectories.c.trajectory_id == entity.trajectory_id)
            .values(
                feedback_reward=entity.feedback_reward,
                archived=entity.archived,
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
            if 'conversation_id' in filters:
                conditions.append(ams_trajectories.c.conversation_id == filters['conversation_id'])
            if 'archived' in filters:
                conditions.append(ams_trajectories.c.archived == filters['archived'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_trajectories.c.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Trajectory(
                trajectory_id=row.trajectory_id,
                user_id=row.user_id,
                conversation_id=row.conversation_id,
                selected_skill_id=row.selected_skill_id,
                context_bucket=row.context_bucket,
                feedback_reward=row.feedback_reward,
                timestamp=row.timestamp,
                archived=row.archived,
                agency_context=row.agency_context,
                message_id=row.message_id,
                turn_number=row.turn_number,
                user_input=row.user_input,
                ai_response=row.ai_response,
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
            if 'archived' in filters:
                conditions.append(ams_trajectories.c.archived == filters['archived'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_conversation_trajectories(self, conversation_id: str) -> List[Trajectory]:
        """Get all trajectories for a conversation."""
        stmt = select(ams_trajectories).where(
            ams_trajectories.c.conversation_id == conversation_id
        ).order_by(ams_trajectories.c.timestamp.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            Trajectory(
                trajectory_id=row.trajectory_id,
                user_id=row.user_id,
                conversation_id=row.conversation_id,
                selected_skill_id=row.selected_skill_id,
                context_bucket=row.context_bucket,
                feedback_reward=row.feedback_reward,
                timestamp=row.timestamp,
                archived=row.archived,
                agency_context=row.agency_context,
                message_id=row.message_id,
                turn_number=row.turn_number,
                user_input=row.user_input,
                ai_response=row.ai_response,
            )
            for row in result.fetchall()
        ]
