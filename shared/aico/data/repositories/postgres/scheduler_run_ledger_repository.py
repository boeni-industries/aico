"""
SchedulerRunLedgerRepository - PostgreSQL implementation

Handles CRUD operations for scheduler run ledger (planned run accounting).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List, Dict, Literal

from sqlalchemy import select, update, delete, and_, desc, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.scheduler.models import SchedulerTaskRun
from aico.data.tables import scheduler_run_ledger
from aico.data.repositories.base import Repository


class PostgresSchedulerRunLedgerRepository(Repository[SchedulerTaskRun]):
    """PostgreSQL implementation of scheduler run-ledger repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: SchedulerTaskRun) -> SchedulerTaskRun:
        """Create a new run ledger row."""
        stmt = scheduler_run_ledger.insert().values(
            task_id=entity.task_id,
            run_key=entity.run_key,
            tenant_id=entity.tenant_id,
            scheduled_for=entity.scheduled_for,
            planned_at=entity.planned_at,
            state=entity.state,
            enqueued_at=entity.enqueued_at,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            execution_id=entity.execution_id,
            reason_code=entity.reason_code,
            reason_detail=entity.reason_detail,
        )
        result = await self.session.execute(stmt)
        entity.id = result.inserted_primary_key[0]
        return entity

    async def create_if_absent(self, entity: SchedulerTaskRun) -> bool:
        """Idempotently create a run ledger row.

        Returns:
            True if inserted, False if it already existed.
        """

        stmt = (
            insert(scheduler_run_ledger)
            .values(
                task_id=entity.task_id,
                run_key=entity.run_key,
                tenant_id=entity.tenant_id,
                scheduled_for=entity.scheduled_for,
                planned_at=entity.planned_at,
                state=entity.state,
                enqueued_at=entity.enqueued_at,
                started_at=entity.started_at,
                completed_at=entity.completed_at,
                execution_id=entity.execution_id,
                reason_code=entity.reason_code,
                reason_detail=entity.reason_detail,
            )
            .on_conflict_do_nothing()
        )

        result = await self.session.execute(stmt)
        return bool(getattr(result, "rowcount", 0) or 0)

    async def get_by_id(self, id: str) -> Optional[SchedulerTaskRun]:
        stmt = select(scheduler_run_ledger).where(scheduler_run_ledger.c.id == int(id))
        result = await self.session.execute(stmt)
        row = result.fetchone()
        if not row:
            return None

        return SchedulerTaskRun(
            id=row.id,
            task_id=row.task_id,
            run_key=row.run_key,
            tenant_id=getattr(row, "tenant_id", None),
            scheduled_for=row.scheduled_for,
            planned_at=row.planned_at,
            state=row.state,
            enqueued_at=row.enqueued_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            execution_id=row.execution_id,
            reason_code=row.reason_code,
            reason_detail=row.reason_detail,
        )

    async def update(self, entity: SchedulerTaskRun) -> SchedulerTaskRun:
        if entity.id is None:
            raise ValueError("Cannot update SchedulerTaskRun without id")

        stmt = (
            update(scheduler_run_ledger)
            .where(scheduler_run_ledger.c.id == entity.id)
            .values(
                state=entity.state,
                enqueued_at=entity.enqueued_at,
                started_at=entity.started_at,
                completed_at=entity.completed_at,
                execution_id=entity.execution_id,
                reason_code=entity.reason_code,
                reason_detail=entity.reason_detail,
            )
        )
        await self.session.execute(stmt)
        return entity

    async def delete(self, id: str) -> bool:
        stmt = delete(scheduler_run_ledger).where(scheduler_run_ledger.c.id == int(id))
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SchedulerTaskRun]:
        stmt = select(scheduler_run_ledger)

        if filters:
            conditions: list[Any] = []
            if "task_id" in filters:
                conditions.append(scheduler_run_ledger.c.task_id == filters["task_id"])
            if "tenant_id" in filters:
                conditions.append(scheduler_run_ledger.c.tenant_id == filters["tenant_id"])
            if "state" in filters:
                conditions.append(scheduler_run_ledger.c.state == filters["state"])
            if "scheduled_for_from" in filters:
                conditions.append(scheduler_run_ledger.c.scheduled_for >= filters["scheduled_for_from"])
            if "scheduled_for_to" in filters:
                conditions.append(scheduler_run_ledger.c.scheduled_for <= filters["scheduled_for_to"])

            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(desc(scheduler_run_ledger.c.scheduled_for)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            SchedulerTaskRun(
                id=row.id,
                task_id=row.task_id,
                run_key=row.run_key,
                tenant_id=getattr(row, "tenant_id", None),
                scheduled_for=row.scheduled_for,
                planned_at=row.planned_at,
                state=row.state,
                enqueued_at=row.enqueued_at,
                started_at=row.started_at,
                completed_at=row.completed_at,
                execution_id=row.execution_id,
                reason_code=row.reason_code,
                reason_detail=row.reason_detail,
            )
            for row in rows
        ]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(scheduler_run_ledger)

        if filters:
            conditions: list[Any] = []
            if "task_id" in filters:
                conditions.append(scheduler_run_ledger.c.task_id == filters["task_id"])
            if "tenant_id" in filters:
                conditions.append(scheduler_run_ledger.c.tenant_id == filters["tenant_id"])
            if "state" in filters:
                conditions.append(scheduler_run_ledger.c.state == filters["state"])
            if "scheduled_for_from" in filters:
                conditions.append(scheduler_run_ledger.c.scheduled_for >= filters["scheduled_for_from"])
            if "scheduled_for_to" in filters:
                conditions.append(scheduler_run_ledger.c.scheduled_for <= filters["scheduled_for_to"])

            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def mark_missed_before(
        self,
        *,
        cutoff: datetime,
        states: tuple[str, ...] = ("planned", "enqueued"),
        reason_code: str = "MISSED",
        reason_detail: str = "Run did not start before grace period",
    ) -> int:
        """Mark overdue runs as missed.

        Only affects rows that have not started (started_at IS NULL).
        Returns the number of rows updated.
        """

        stmt = (
            update(scheduler_run_ledger)
            .where(
                and_(
                    scheduler_run_ledger.c.scheduled_for < cutoff,
                    scheduler_run_ledger.c.state.in_(states),
                    scheduler_run_ledger.c.started_at.is_(None),
                )
            )
            .values(
                state="missed",
                reason_code=reason_code,
                reason_detail=reason_detail,
            )
        )

        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def stats_in_range(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        bucket: Literal["hour", "day"] = "hour",
        task_id: str | None = None,
        tenant_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate run counts grouped into time buckets and state."""

        bucket_expr = func.date_trunc(bucket, scheduler_run_ledger.c.scheduled_for).label("bucket_start")
        stmt = select(
            bucket_expr,
            scheduler_run_ledger.c.state.label("state"),
            func.count().label("count"),
        ).where(
            and_(
                scheduler_run_ledger.c.scheduled_for >= start_dt,
                scheduler_run_ledger.c.scheduled_for <= end_dt,
            )
        )

        if task_id:
            stmt = stmt.where(scheduler_run_ledger.c.task_id == task_id)
        if tenant_id is not None:
            stmt = stmt.where(scheduler_run_ledger.c.tenant_id == tenant_id)

        stmt = stmt.group_by(bucket_expr, scheduler_run_ledger.c.state).order_by(bucket_expr.asc())

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "bucket_start": row.bucket_start,
                "state": row.state,
                "count": int(row.count or 0),
            }
            for row in rows
        ]

    async def mark_enqueued(
        self,
        *,
        task_id: str,
        scheduled_for: datetime,
        tenant_id: str | None,
        enqueued_at: datetime,
        execution_id: str | None = None,
    ) -> int:
        stmt = (
            update(scheduler_run_ledger)
            .where(
                and_(
                    scheduler_run_ledger.c.task_id == task_id,
                    scheduler_run_ledger.c.scheduled_for == scheduled_for,
                    scheduler_run_ledger.c.tenant_id.is_(None)
                    if tenant_id is None
                    else scheduler_run_ledger.c.tenant_id == tenant_id,
                )
            )
            .values(
                state="enqueued",
                enqueued_at=enqueued_at,
                execution_id=execution_id,
            )
        )

        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def mark_suppressed(
        self,
        *,
        task_id: str,
        scheduled_for: datetime,
        tenant_id: str | None,
        reason_code: str,
        reason_detail: str,
    ) -> int:
        stmt = (
            update(scheduler_run_ledger)
            .where(
                and_(
                    scheduler_run_ledger.c.task_id == task_id,
                    scheduler_run_ledger.c.scheduled_for == scheduled_for,
                    scheduler_run_ledger.c.tenant_id.is_(None)
                    if tenant_id is None
                    else scheduler_run_ledger.c.tenant_id == tenant_id,
                    scheduler_run_ledger.c.started_at.is_(None),
                )
            )
            .values(
                state="suppressed",
                reason_code=reason_code,
                reason_detail=reason_detail,
            )
        )

        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def delete_before(
        self,
        *,
        cutoff: datetime,
        states: List[str] | None = None,
    ) -> int:
        """Delete run ledger entries scheduled before cutoff date.
        
        Args:
            cutoff: Delete runs scheduled before this datetime
            states: Optional list of states to delete (e.g., ['completed', 'missed', 'suppressed'])
                   If None, deletes all states except 'planned' and 'enqueued'
        
        Returns:
            Number of rows deleted
        """
        stmt = delete(scheduler_run_ledger).where(
            scheduler_run_ledger.c.scheduled_for < cutoff
        )
        
        if states is not None:
            stmt = stmt.where(scheduler_run_ledger.c.state.in_(states))
        else:
            # Default: delete finalized states only, keep active runs
            stmt = stmt.where(
                scheduler_run_ledger.c.state.in_(['completed', 'missed', 'suppressed', 'started'])
            )
        
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
