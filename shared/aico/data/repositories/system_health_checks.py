"""Repository for system_health_checks table."""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_health import SystemHealthCheck


class SystemHealthCheckRepository:
    """Repository for managing system health check records."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, health_check: SystemHealthCheck) -> SystemHealthCheck:
        """Create a new health check record."""
        self._session.add(health_check)
        await self._session.flush()
        await self._session.refresh(health_check)
        return health_check

    async def get_by_id(self, check_id: UUID) -> Optional[SystemHealthCheck]:
        """Get health check by ID."""
        result = await self._session.execute(
            select(SystemHealthCheck).where(SystemHealthCheck.id == check_id)
        )
        return result.scalar_one_or_none()

    async def list_by_check_id(
        self, check_id: str, limit: int = 10
    ) -> List[SystemHealthCheck]:
        """List recent health checks by check_id."""
        result = await self._session.execute(
            select(SystemHealthCheck)
            .where(SystemHealthCheck.check_id == check_id)
            .order_by(SystemHealthCheck.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(
        self, limit: int = 50, status: Optional[str] = None
    ) -> List[SystemHealthCheck]:
        """List recent health checks, optionally filtered by status."""
        query = select(SystemHealthCheck).order_by(
            SystemHealthCheck.started_at.desc()
        )
        
        if status:
            query = query.where(SystemHealthCheck.status == status)
        
        query = query.limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Delete health checks older than cutoff date."""
        from sqlalchemy import delete
        
        result = await self._session.execute(
            delete(SystemHealthCheck).where(
                SystemHealthCheck.created_at < cutoff
            )
        )
        return result.rowcount
