"""
AgencyFollowupsRepository - PostgreSQL implementation

Handles CRUD operations for agency followups.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import AgencyFollowup
from aico.data.tables import agency_followups
from aico.data.repositories.base import Repository


class PostgresAgencyFollowupsRepository(Repository[AgencyFollowup]):
    """PostgreSQL implementation of agency followups repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyFollowup) -> AgencyFollowup:
        """Create a new agency followup."""
        stmt = agency_followups.insert().values(
            followup_id=entity.followup_id,
            user_id=entity.user_id,
            goal_id=entity.goal_id,
            related_message_id=entity.related_message_id,
            followup_type=entity.followup_type,
            content=entity.content,
            scheduled_at=entity.scheduled_at,
            delivered_at=entity.delivered_at,
            user_response=entity.user_response,
            response_sentiment=entity.response_sentiment,
            status=entity.status,
            priority=entity.priority,
            policy_approved=entity.policy_approved,
            relationship_context=entity.relationship_context,
            values_alignment=entity.values_alignment,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AgencyFollowup]:
        """Get agency followup by ID."""
        stmt = select(agency_followups).where(agency_followups.c.followup_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyFollowup(
            followup_id=row.followup_id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            related_message_id=row.related_message_id,
            followup_type=row.followup_type,
            content=row.content,
            scheduled_at=row.scheduled_at,
            delivered_at=row.delivered_at,
            user_response=row.user_response,
            response_sentiment=row.response_sentiment,
            status=row.status,
            priority=row.priority,
            policy_approved=row.policy_approved,
            relationship_context=row.relationship_context,
            values_alignment=row.values_alignment,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AgencyFollowup) -> AgencyFollowup:
        """Update an existing agency followup."""
        stmt = (
            update(agency_followups)
            .where(agency_followups.c.followup_id == entity.followup_id)
            .values(
                status=entity.status,
                delivered_at=entity.delivered_at,
                user_response=entity.user_response,
                response_sentiment=entity.response_sentiment,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an agency followup."""
        stmt = delete(agency_followups).where(agency_followups.c.followup_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyFollowup]:
        """List agency followups with optional filters."""
        stmt = select(agency_followups)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_followups.c.user_id == filters['user_id'])
            if 'goal_id' in filters:
                conditions.append(agency_followups.c.goal_id == filters['goal_id'])
            if 'status' in filters:
                conditions.append(agency_followups.c.status == filters['status'])
            if 'followup_type' in filters:
                conditions.append(agency_followups.c.followup_type == filters['followup_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_followups.c.scheduled_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyFollowup(
                followup_id=row.followup_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                related_message_id=row.related_message_id,
                followup_type=row.followup_type,
                content=row.content,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                user_response=row.user_response,
                response_sentiment=row.response_sentiment,
                status=row.status,
                priority=row.priority,
                policy_approved=row.policy_approved,
                relationship_context=row.relationship_context,
                values_alignment=row.values_alignment,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count agency followups with optional filters."""
        stmt = select(func.count()).select_from(agency_followups)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_followups.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_followups.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_pending_for_user(self, user_id: str, limit: int = 50) -> List[AgencyFollowup]:
        """Get all pending followups for a user."""
        stmt = select(agency_followups).where(
            and_(
                agency_followups.c.user_id == user_id,
                agency_followups.c.status == 'pending'
            )
        ).order_by(agency_followups.c.scheduled_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyFollowup(
                followup_id=row.followup_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                related_message_id=row.related_message_id,
                followup_type=row.followup_type,
                content=row.content,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                user_response=row.user_response,
                response_sentiment=row.response_sentiment,
                status=row.status,
                priority=row.priority,
                policy_approved=row.policy_approved,
                relationship_context=row.relationship_context,
                values_alignment=row.values_alignment,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_delivered(self, followup_id: str) -> bool:
        """Mark a followup as delivered."""
        stmt = (
            update(agency_followups)
            .where(agency_followups.c.followup_id == followup_id)
            .values(
                status='delivered',
                delivered_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_followups_for_goal(self, goal_id: str, limit: int = 50) -> List[AgencyFollowup]:
        """Get all followups for a specific goal."""
        stmt = select(agency_followups).where(
            agency_followups.c.goal_id == goal_id
        ).order_by(agency_followups.c.scheduled_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyFollowup(
                followup_id=row.followup_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                related_message_id=row.related_message_id,
                followup_type=row.followup_type,
                content=row.content,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                user_response=row.user_response,
                response_sentiment=row.response_sentiment,
                status=row.status,
                priority=row.priority,
                policy_approved=row.policy_approved,
                relationship_context=row.relationship_context,
                values_alignment=row.values_alignment,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
