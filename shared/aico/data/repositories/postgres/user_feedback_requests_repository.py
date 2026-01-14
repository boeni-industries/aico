"""
UserFeedbackRequestsRepository - PostgreSQL implementation

Handles CRUD operations for user feedback requests.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.user.feedback_models import UserFeedbackRequest
from aico.data.tables import user_feedback_requests
from aico.data.repositories.base import Repository


class PostgresUserFeedbackRequestsRepository(Repository[UserFeedbackRequest]):
    """PostgreSQL implementation of user feedback requests repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserFeedbackRequest) -> UserFeedbackRequest:
        """Create a new user feedback request."""
        stmt = user_feedback_requests.insert().values(
            request_id=entity.request_id,
            user_id=entity.user_id,
            goal_id=entity.goal_id,
            skill_id=entity.skill_id,
            execution_id=entity.execution_id,
            feedback_type=entity.feedback_type,
            question=entity.question,
            response=entity.response,
            rating=entity.rating,
            responded_at=entity.responded_at,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserFeedbackRequest]:
        """Get user feedback request by ID."""
        stmt = select(user_feedback_requests).where(user_feedback_requests.c.request_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserFeedbackRequest(
            request_id=row.request_id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            skill_id=row.skill_id,
            execution_id=row.execution_id,
            feedback_type=row.feedback_type,
            question=row.question,
            response=row.response,
            rating=row.rating,
            responded_at=row.responded_at,
            created_at=row.created_at,
        )
    
    async def update(self, entity: UserFeedbackRequest) -> UserFeedbackRequest:
        """Update an existing user feedback request."""
        stmt = (
            update(user_feedback_requests)
            .where(user_feedback_requests.c.request_id == entity.request_id)
            .values(
                response=entity.response,
                rating=entity.rating,
                responded_at=entity.responded_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user feedback request."""
        stmt = delete(user_feedback_requests).where(user_feedback_requests.c.request_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserFeedbackRequest]:
        """List user feedback requests with optional filters."""
        stmt = select(user_feedback_requests)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_feedback_requests.c.user_id == filters['user_id'])
            if 'goal_id' in filters:
                conditions.append(user_feedback_requests.c.goal_id == filters['goal_id'])
            if 'feedback_type' in filters:
                conditions.append(user_feedback_requests.c.feedback_type == filters['feedback_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(user_feedback_requests.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserFeedbackRequest(
                request_id=row.request_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                skill_id=row.skill_id,
                execution_id=row.execution_id,
                feedback_type=row.feedback_type,
                question=row.question,
                response=row.response,
                rating=row.rating,
                responded_at=row.responded_at,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user feedback requests with optional filters."""
        stmt = select(func.count()).select_from(user_feedback_requests)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_feedback_requests.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_pending_for_user(self, user_id: str, limit: int = 50) -> List[UserFeedbackRequest]:
        """Get all pending feedback requests for a user."""
        stmt = select(user_feedback_requests).where(
            and_(
                user_feedback_requests.c.user_id == user_id,
                user_feedback_requests.c.responded_at.is_(None)
            )
        ).order_by(user_feedback_requests.c.created_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            UserFeedbackRequest(
                request_id=row.request_id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                skill_id=row.skill_id,
                execution_id=row.execution_id,
                feedback_type=row.feedback_type,
                question=row.question,
                response=row.response,
                rating=row.rating,
                responded_at=row.responded_at,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_responded(self, request_id: str, response: str, rating: Optional[float] = None) -> bool:
        """Mark a feedback request as responded."""
        stmt = (
            update(user_feedback_requests)
            .where(user_feedback_requests.c.request_id == request_id)
            .values(
                response=response,
                rating=rating,
                responded_at=datetime.now(UTC).isoformat(),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
