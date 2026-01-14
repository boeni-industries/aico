"""
UserProactivePreferencesRepository - PostgreSQL implementation

Handles CRUD operations for user proactive preferences.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.user.models import UserProactivePreferences
from aico.data.tables import user_proactive_preferences
from aico.data.repositories.base import Repository


class PostgresUserProactivePreferencesRepository(Repository[UserProactivePreferences]):
    """PostgreSQL implementation of user proactive preferences repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserProactivePreferences) -> UserProactivePreferences:
        """Create new user proactive preferences."""
        stmt = user_proactive_preferences.insert().values(
            user_id=entity.user_id,
            followup_enabled=entity.followup_enabled,
            reminder_enabled=entity.reminder_enabled,
            preferred_followup_times=entity.preferred_followup_times,
            preferred_reminder_times=entity.preferred_reminder_times,
            max_followups_per_day=entity.max_followups_per_day,
            max_reminders_per_day=entity.max_reminders_per_day,
            min_hours_between_followups=entity.min_hours_between_followups,
            min_hours_between_reminders=entity.min_hours_between_reminders,
            cluster_reminders=entity.cluster_reminders,
            auto_snooze_duration_minutes=entity.auto_snooze_duration_minutes,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserProactivePreferences]:
        """Get user proactive preferences by user ID."""
        stmt = select(user_proactive_preferences).where(
            user_proactive_preferences.c.user_id == entity_id
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserProactivePreferences(
            user_id=row.user_id,
            followup_enabled=row.followup_enabled,
            reminder_enabled=row.reminder_enabled,
            preferred_followup_times=row.preferred_followup_times,
            preferred_reminder_times=row.preferred_reminder_times,
            max_followups_per_day=row.max_followups_per_day,
            max_reminders_per_day=row.max_reminders_per_day,
            min_hours_between_followups=row.min_hours_between_followups,
            min_hours_between_reminders=row.min_hours_between_reminders,
            cluster_reminders=row.cluster_reminders,
            auto_snooze_duration_minutes=row.auto_snooze_duration_minutes,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: UserProactivePreferences) -> UserProactivePreferences:
        """Update existing user proactive preferences."""
        stmt = (
            update(user_proactive_preferences)
            .where(user_proactive_preferences.c.user_id == entity.user_id)
            .values(
                followup_enabled=entity.followup_enabled,
                reminder_enabled=entity.reminder_enabled,
                preferred_followup_times=entity.preferred_followup_times,
                preferred_reminder_times=entity.preferred_reminder_times,
                max_followups_per_day=entity.max_followups_per_day,
                max_reminders_per_day=entity.max_reminders_per_day,
                min_hours_between_followups=entity.min_hours_between_followups,
                min_hours_between_reminders=entity.min_hours_between_reminders,
                cluster_reminders=entity.cluster_reminders,
                auto_snooze_duration_minutes=entity.auto_snooze_duration_minutes,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete user proactive preferences."""
        stmt = delete(user_proactive_preferences).where(
            user_proactive_preferences.c.user_id == entity_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserProactivePreferences]:
        """List user proactive preferences with optional filters."""
        stmt = select(user_proactive_preferences)
        
        if filters:
            conditions = []
            if 'followup_enabled' in filters:
                conditions.append(user_proactive_preferences.c.followup_enabled == filters['followup_enabled'])
            if 'reminder_enabled' in filters:
                conditions.append(user_proactive_preferences.c.reminder_enabled == filters['reminder_enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserProactivePreferences(
                user_id=row.user_id,
                followup_enabled=row.followup_enabled,
                reminder_enabled=row.reminder_enabled,
                preferred_followup_times=row.preferred_followup_times,
                preferred_reminder_times=row.preferred_reminder_times,
                max_followups_per_day=row.max_followups_per_day,
                max_reminders_per_day=row.max_reminders_per_day,
                min_hours_between_followups=row.min_hours_between_followups,
                min_hours_between_reminders=row.min_hours_between_reminders,
                cluster_reminders=row.cluster_reminders,
                auto_snooze_duration_minutes=row.auto_snooze_duration_minutes,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user proactive preferences with optional filters."""
        stmt = select(func.count()).select_from(user_proactive_preferences)
        
        if filters:
            conditions = []
            if 'followup_enabled' in filters:
                conditions.append(user_proactive_preferences.c.followup_enabled == filters['followup_enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_users_with_followups_enabled(self) -> List[UserProactivePreferences]:
        """Get all users with followups enabled."""
        stmt = select(user_proactive_preferences).where(
            user_proactive_preferences.c.followup_enabled == True
        )
        
        result = await self.session.execute(stmt)
        
        return [
            UserProactivePreferences(
                user_id=row.user_id,
                followup_enabled=row.followup_enabled,
                reminder_enabled=row.reminder_enabled,
                preferred_followup_times=row.preferred_followup_times,
                preferred_reminder_times=row.preferred_reminder_times,
                max_followups_per_day=row.max_followups_per_day,
                max_reminders_per_day=row.max_reminders_per_day,
                min_hours_between_followups=row.min_hours_between_followups,
                min_hours_between_reminders=row.min_hours_between_reminders,
                cluster_reminders=row.cluster_reminders,
                auto_snooze_duration_minutes=row.auto_snooze_duration_minutes,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_users_with_reminders_enabled(self) -> List[UserProactivePreferences]:
        """Get all users with reminders enabled."""
        stmt = select(user_proactive_preferences).where(
            user_proactive_preferences.c.reminder_enabled == True
        )
        
        result = await self.session.execute(stmt)
        
        return [
            UserProactivePreferences(
                user_id=row.user_id,
                followup_enabled=row.followup_enabled,
                reminder_enabled=row.reminder_enabled,
                preferred_followup_times=row.preferred_followup_times,
                preferred_reminder_times=row.preferred_reminder_times,
                max_followups_per_day=row.max_followups_per_day,
                max_reminders_per_day=row.max_reminders_per_day,
                min_hours_between_followups=row.min_hours_between_followups,
                min_hours_between_reminders=row.min_hours_between_reminders,
                cluster_reminders=row.cluster_reminders,
                auto_snooze_duration_minutes=row.auto_snooze_duration_minutes,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
