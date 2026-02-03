"""
LessonRepository - PostgreSQL implementation

Handles CRUD operations for agency lessons.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.lesson_models import Lesson
from aico.data.tables import agency_lessons
from aico.data.repositories.base import Repository


class PostgresLessonRepository(Repository[Lesson]):
    """PostgreSQL implementation of lesson repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    def _safe_json_dumps(self, value) -> Optional[str]:
        import json

        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value)
        except Exception:
            return None

    def _safe_json_loads(self, value) -> Optional[dict]:
        import json

        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

    def _safe_json_list_dumps(self, value) -> Optional[str]:
        import json

        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(list(value))
        except Exception:
            return None

    def _safe_json_list_loads(self, value) -> List[str]:
        import json

        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except Exception:
                # Backward-compatible: treat as comma-separated
                return [v for v in (s.strip() for s in value.split(",")) if v]
        return []
    
    async def create(self, entity: Lesson) -> Lesson:
        """Create a new lesson."""
        stmt = agency_lessons.insert().values(
            lesson_id=entity.lesson_id,
            user_id=entity.user_id,
            lesson_type=entity.lesson_type.value if hasattr(entity.lesson_type, 'value') else entity.lesson_type,
            target_kind=entity.target_kind.value if hasattr(entity.target_kind, 'value') else entity.target_kind,
            target_id=entity.target_id,
            summary_text=entity.summary_text,
            proposed_change=self._safe_json_dumps(entity.proposed_change) or "{}",
            confidence=entity.confidence,
            metrics_basis=self._safe_json_dumps(entity.metrics_basis),
            scope=entity.scope.value if hasattr(entity.scope, 'value') else entity.scope,
            status=entity.status.value if hasattr(entity.status, 'value') else entity.status,
            superseded_by=entity.superseded_by,
            applied_at=entity.applied_at,
            applied_by=entity.applied_by,
            source_reflection_run_id=entity.source_reflection_run_id,
            evidence_window_start=entity.evidence_window_start,
            evidence_window_end=entity.evidence_window_end,
            related_goal_ids=self._safe_json_list_dumps(entity.related_goal_ids),
            related_trajectory_ids=self._safe_json_list_dumps(entity.related_trajectory_ids),
            related_event_ids=self._safe_json_list_dumps(entity.related_event_ids),
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Lesson]:
        """Get lesson by ID."""
        stmt = select(agency_lessons).where(agency_lessons.c.lesson_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None

        return Lesson(
            lesson_id=row.lesson_id,
            user_id=row.user_id,
            lesson_type=row.lesson_type,
            target_kind=row.target_kind,
            target_id=row.target_id,
            summary_text=row.summary_text,
            proposed_change=self._safe_json_loads(row.proposed_change),
            confidence=row.confidence,
            metrics_basis=self._safe_json_loads(row.metrics_basis),
            scope=row.scope,
            status=row.status,
            superseded_by=row.superseded_by,
            applied_at=row.applied_at,
            applied_by=row.applied_by,
            source_reflection_run_id=row.source_reflection_run_id,
            evidence_window_start=row.evidence_window_start,
            evidence_window_end=row.evidence_window_end,
            related_goal_ids=self._safe_json_list_loads(row.related_goal_ids),
            related_trajectory_ids=self._safe_json_list_loads(row.related_trajectory_ids),
            related_event_ids=self._safe_json_list_loads(row.related_event_ids),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Lesson) -> Lesson:
        """Update an existing lesson."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == entity.lesson_id)
            .values(
                summary_text=entity.summary_text,
                proposed_change=self._safe_json_dumps(entity.proposed_change) or "{}",
                confidence=entity.confidence,
                metrics_basis=self._safe_json_dumps(entity.metrics_basis),
                status=entity.status.value if hasattr(entity.status, 'value') else entity.status,
                superseded_by=entity.superseded_by,
                applied_at=entity.applied_at,
                applied_by=entity.applied_by,
                scope=entity.scope.value if hasattr(entity.scope, 'value') else entity.scope,
                source_reflection_run_id=entity.source_reflection_run_id,
                evidence_window_start=entity.evidence_window_start,
                evidence_window_end=entity.evidence_window_end,
                related_goal_ids=self._safe_json_list_dumps(entity.related_goal_ids),
                related_trajectory_ids=self._safe_json_list_dumps(entity.related_trajectory_ids),
                related_event_ids=self._safe_json_list_dumps(entity.related_event_ids),
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a lesson."""
        stmt = delete(agency_lessons).where(agency_lessons.c.lesson_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Lesson]:
        """List lessons with optional filters."""
        stmt = select(agency_lessons)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_lessons.c.user_id == filters['user_id'])
            if 'lesson_type' in filters:
                conditions.append(agency_lessons.c.lesson_type == filters['lesson_type'])
            if 'status' in filters:
                conditions.append(agency_lessons.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_lessons.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)

        return [
            Lesson(
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                lesson_type=row.lesson_type,
                target_kind=row.target_kind,
                target_id=row.target_id,
                summary_text=row.summary_text,
                proposed_change=self._safe_json_loads(row.proposed_change),
                confidence=row.confidence,
                metrics_basis=self._safe_json_loads(row.metrics_basis),
                scope=row.scope,
                status=row.status,
                superseded_by=row.superseded_by,
                applied_at=row.applied_at,
                applied_by=row.applied_by,
                source_reflection_run_id=row.source_reflection_run_id,
                evidence_window_start=row.evidence_window_start,
                evidence_window_end=row.evidence_window_end,
                related_goal_ids=self._safe_json_list_loads(row.related_goal_ids),
                related_trajectory_ids=self._safe_json_list_loads(row.related_trajectory_ids),
                related_event_ids=self._safe_json_list_loads(row.related_event_ids),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count lessons with optional filters."""
        stmt = select(func.count()).select_from(agency_lessons)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_lessons.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(agency_lessons.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_lessons_for_user(self, user_id: str, lesson_type: Optional[str] = None) -> List[Lesson]:
        """Get active lessons for a user, optionally filtered by type."""
        conditions = [
            agency_lessons.c.user_id == user_id,
            agency_lessons.c.status == 'active',
            agency_lessons.c.superseded_by.is_(None)
        ]
        
        if lesson_type:
            conditions.append(agency_lessons.c.lesson_type == lesson_type)
        
        stmt = select(agency_lessons).where(
            and_(*conditions)
        ).order_by(agency_lessons.c.confidence.desc(), agency_lessons.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Lesson(
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                lesson_type=row.lesson_type,
                target_kind=row.target_kind,
                target_id=row.target_id,
                summary_text=row.summary_text,
                proposed_change=self._safe_json_loads(row.proposed_change),
                confidence=row.confidence,
                metrics_basis=self._safe_json_loads(row.metrics_basis),
                scope=row.scope,
                status=row.status,
                superseded_by=row.superseded_by,
                applied_at=row.applied_at,
                applied_by=row.applied_by,
                source_reflection_run_id=row.source_reflection_run_id,
                evidence_window_start=row.evidence_window_start,
                evidence_window_end=row.evidence_window_end,
                related_goal_ids=self._safe_json_list_loads(row.related_goal_ids),
                related_trajectory_ids=self._safe_json_list_loads(row.related_trajectory_ids),
                related_event_ids=self._safe_json_list_loads(row.related_event_ids),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def supersede_lesson(self, old_lesson_id: str, new_lesson_id: str) -> bool:
        """Mark a lesson as superseded by a newer lesson."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == old_lesson_id)
            .values(
                superseded_by=new_lesson_id,
                status='superseded',
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def update_confidence(self, lesson_id: str, new_confidence: float) -> bool:
        """Update lesson confidence score."""
        stmt = (
            update(agency_lessons)
            .where(agency_lessons.c.lesson_id == lesson_id)
            .values(
                confidence=new_confidence,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
