"""
AMSBehavioralFeedbackRepository - PostgreSQL implementation

Handles CRUD operations for AMS behavioral feedback.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.models import BehavioralFeedback
from aico.data.tables import ams_behavioral_feedback
from aico.data.repositories.base import Repository

import json

class PostgresAMSBehavioralFeedbackRepository(Repository[BehavioralFeedback]):
    """PostgreSQL implementation of AMS behavioral feedback repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: BehavioralFeedback) -> BehavioralFeedback:
        """Create a new behavioral feedback."""
        stmt = ams_behavioral_feedback.insert().values(
            feedback_id=entity.feedback_id,
            user_id=entity.user_id,
            message_id=entity.message_id,
            skill_id=entity.skill_id,
            reward=entity.reward,
            reason=entity.reason,
            timestamp=entity.timestamp,
            processed=entity.processed,
            outcome=entity.outcome,
            execution_time_ms=entity.execution_time_ms,
            context_json=entity.context_json,
            user_satisfaction=entity.user_satisfaction,
            free_text=entity.free_text,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[BehavioralFeedback]:
        """Get behavioral feedback by ID."""
        stmt = select(ams_behavioral_feedback).where(ams_behavioral_feedback.c.feedback_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return BehavioralFeedback(
            feedback_id=row.feedback_id,
            user_id=row.user_id,
            message_id=row.message_id,
            skill_id=row.skill_id,
            reward=row.reward,
            reason=row.reason,
            timestamp=row.timestamp,
            processed=row.processed,
            outcome=row.outcome,
            execution_time_ms=row.execution_time_ms,
            context_json=row.context_json,
            user_satisfaction=row.user_satisfaction,
            free_text=row.free_text,
        )
    
    async def update(self, entity: BehavioralFeedback) -> BehavioralFeedback:
        """Update an existing behavioral feedback."""
        stmt = (
            update(ams_behavioral_feedback)
            .where(ams_behavioral_feedback.c.feedback_id == entity.feedback_id)
            .values(
                processed=entity.processed,
                outcome=entity.outcome,
                execution_time_ms=entity.execution_time_ms,
                user_satisfaction=entity.user_satisfaction,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a behavioral feedback."""
        stmt = delete(ams_behavioral_feedback).where(ams_behavioral_feedback.c.feedback_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[BehavioralFeedback]:
        """List behavioral feedback with optional filters."""
        stmt = select(ams_behavioral_feedback)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_behavioral_feedback.c.user_id == filters['user_id'])
            if 'skill_id' in filters:
                conditions.append(ams_behavioral_feedback.c.skill_id == filters['skill_id'])
            if 'processed' in filters:
                conditions.append(ams_behavioral_feedback.c.processed == filters['processed'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_behavioral_feedback.c.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            BehavioralFeedback(
                feedback_id=row.feedback_id,
                user_id=row.user_id,
                message_id=row.message_id,
                skill_id=row.skill_id,
                reward=row.reward,
                reason=row.reason,
                timestamp=row.timestamp,
                processed=row.processed,
                outcome=row.outcome,
                execution_time_ms=row.execution_time_ms,
                context_json=row.context_json,
                user_satisfaction=row.user_satisfaction,
                free_text=row.free_text,
            )
            for row in result.fetchall()
        ]

    async def get_skill_stats(
        self,
        skill_id: str,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
    ) -> dict:
        """Get aggregate performance stats for a skill."""
        conditions = [ams_behavioral_feedback.c.skill_id == skill_id]
        if user_id:
            conditions.append(ams_behavioral_feedback.c.user_id == user_id)
        if from_date:
            conditions.append(ams_behavioral_feedback.c.timestamp >= from_date)

        stmt = (
            select(
                func.count().label("total"),
                func.coalesce(
                    func.sum(case((ams_behavioral_feedback.c.outcome == "success", 1), else_=0)),
                    0,
                ).label("successes"),
                func.coalesce(
                    func.sum(case((ams_behavioral_feedback.c.outcome == "failure", 1), else_=0)),
                    0,
                ).label("failures"),
            )
            .where(and_(*conditions))
        )

        result = await self.session.execute(stmt)
        row = result.fetchone()
        if not row:
            return {"total": 0, "successes": 0, "failures": 0}

        mapping = row._mapping
        return {
            "total": int(mapping["total"] or 0),
            "successes": int(mapping["successes"] or 0),
            "failures": int(mapping["failures"] or 0),
        }
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count behavioral feedback with optional filters."""
        stmt = select(func.count()).select_from(ams_behavioral_feedback)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_behavioral_feedback.c.user_id == filters['user_id'])
            if 'processed' in filters:
                conditions.append(ams_behavioral_feedback.c.processed == filters['processed'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_unprocessed(self, limit: int = 100) -> List[BehavioralFeedback]:
        """Get unprocessed behavioral feedback."""
        stmt = select(ams_behavioral_feedback).where(
            ams_behavioral_feedback.c.processed == 0
        ).order_by(ams_behavioral_feedback.c.timestamp.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            BehavioralFeedback(
                feedback_id=row.feedback_id,
                user_id=row.user_id,
                message_id=row.message_id,
                skill_id=row.skill_id,
                reward=row.reward,
                reason=row.reason,
                timestamp=row.timestamp,
                processed=row.processed,
                outcome=row.outcome,
                execution_time_ms=row.execution_time_ms,
                context_json=row.context_json,
                user_satisfaction=row.user_satisfaction,
                free_text=row.free_text,
            )
            for row in result.fetchall()
        ]
