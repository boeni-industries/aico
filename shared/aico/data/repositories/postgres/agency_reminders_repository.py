"""
AgencyRemindersRepository - PostgreSQL implementation

Handles CRUD operations for agency reminders.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import AgencyReminder
from aico.data.tables import agency_reminders
from aico.data.repositories.base import Repository


class PostgresAgencyRemindersRepository(Repository[AgencyReminder]):
    """PostgreSQL implementation of agency reminders repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyReminder) -> AgencyReminder:
        """Create a new agency reminder."""
        stmt = agency_reminders.insert().values(
            reminder_id=entity.reminder_id,
            user_id=entity.user_id,
            goal_id=entity.goal_id,
            title=entity.title,
            description=entity.description,
            scheduled_at=entity.scheduled_at,
            delivered_at=entity.delivered_at,
            snoozed_until=entity.snoozed_until,
            snooze_count=entity.snooze_count,
            status=entity.status,
            priority=entity.priority,
            urgency_score=entity.urgency_score,
            recurrence_rule=entity.recurrence_rule,
            cluster_id=entity.cluster_id,
            adaptation_data=entity.adaptation_data,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AgencyReminder]:
        """Get agency reminder by ID."""
        stmt = select(agency_reminders).where(agency_reminders.c.reminder_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyReminder(
            reminder_id=row.reminder_id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            title=row.title,
            description=row.description,
            scheduled_at=row.scheduled_at,
            delivered_at=row.delivered_at,
            snoozed_until=row.snoozed_until,
            snooze_count=row.snooze_count,
            status=row.status,
            priority=row.priority,
            urgency_score=row.urgency_score,
            recurrence_rule=row.recurrence_rule,
            cluster_id=row.cluster_id,
            adaptation_data=row.adaptation_data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AgencyReminder) -> AgencyReminder:
        """Update an existing agency reminder."""
        stmt = (
            update(agency_reminders)
            .where(agency_reminders.c.reminder_id == entity.reminder_id)
            .values(
                status=entity.status,
                delivered_at=entity.delivered_at,
                snoozed_until=entity.snoozed_until,
                snooze_count=entity.snooze_count,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an agency reminder."""
        stmt = delete(agency_reminders).where(agency_reminders.c.reminder_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyReminder]:
        """List agency reminders with optional filters."""
        stmt = select(agency_reminders)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_reminders.c.user_id == filters['user_id'])
            if 'goal_id' in filters:
                conditions.append(agency_reminders.c.goal_id == filters['goal_id'])
            if 'status' in filters:
                conditions.append(agency_reminders.c.status == filters['status'])
            if 'priority' in filters:
                conditions.append(agency_reminders.c.priority == filters['priority'])
            if 'cluster_id' in filters:
                conditions.append(agency_reminders.c.cluster_id == filters['cluster_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_reminders.c.scheduled_at.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyReminder(
                reminder_id=row.reminder_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                title=row.title,
                description=row.description,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                snoozed_until=row.snoozed_until,
                snooze_count=row.snooze_count,
                status=row.status,
                priority=row.priority,
                urgency_score=row.urgency_score,
                recurrence_rule=row.recurrence_rule,
                cluster_id=row.cluster_id,
                adaptation_data=row.adaptation_data,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count agency reminders with optional filters."""
        stmt = select(func.count()).select_from(agency_reminders)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_reminders.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_reminders.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_pending_for_user(self, user_id: str, limit: int = 50) -> List[AgencyReminder]:
        """Get all pending reminders for a user."""
        stmt = select(agency_reminders).where(
            and_(
                agency_reminders.c.user_id == user_id,
                agency_reminders.c.status == 'pending'
            )
        ).order_by(agency_reminders.c.scheduled_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyReminder(
                reminder_id=row.reminder_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                title=row.title,
                description=row.description,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                snoozed_until=row.snoozed_until,
                snooze_count=row.snooze_count,
                status=row.status,
                priority=row.priority,
                urgency_score=row.urgency_score,
                recurrence_rule=row.recurrence_rule,
                cluster_id=row.cluster_id,
                adaptation_data=row.adaptation_data,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def snooze_reminder(self, reminder_id: str, snoozed_until: str) -> bool:
        """Snooze a reminder until a specific time."""
        stmt = (
            update(agency_reminders)
            .where(agency_reminders.c.reminder_id == reminder_id)
            .values(
                status='snoozed',
                snoozed_until=snoozed_until,
                snooze_count=agency_reminders.c.snooze_count + 1,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def mark_as_delivered(self, reminder_id: str) -> bool:
        """Mark a reminder as delivered."""
        stmt = (
            update(agency_reminders)
            .where(agency_reminders.c.reminder_id == reminder_id)
            .values(
                status='delivered',
                delivered_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_reminders_by_cluster(self, cluster_id: str, limit: int = 50) -> List[AgencyReminder]:
        """Get all reminders in a cluster."""
        stmt = select(agency_reminders).where(
            agency_reminders.c.cluster_id == cluster_id
        ).order_by(agency_reminders.c.scheduled_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyReminder(
                reminder_id=row.reminder_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                title=row.title,
                description=row.description,
                scheduled_at=row.scheduled_at,
                delivered_at=row.delivered_at,
                snoozed_until=row.snoozed_until,
                snooze_count=row.snooze_count,
                status=row.status,
                priority=row.priority,
                urgency_score=row.urgency_score,
                recurrence_rule=row.recurrence_rule,
                cluster_id=row.cluster_id,
                adaptation_data=row.adaptation_data,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
