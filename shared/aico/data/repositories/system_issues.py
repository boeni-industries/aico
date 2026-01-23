"""Repository for system_issues table."""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_health import SystemIssue


class SystemIssueRepository:
    """Repository for managing system issues."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, issue: SystemIssue) -> SystemIssue:
        """Create a new issue."""
        self._session.add(issue)
        await self._session.flush()
        await self._session.refresh(issue)
        return issue

    async def get_by_id(self, issue_id: UUID) -> Optional[SystemIssue]:
        """Get issue by ID."""
        result = await self._session.execute(
            select(SystemIssue).where(SystemIssue.id == issue_id)
        )
        return result.scalar_one_or_none()

    async def get_by_issue_id(self, issue_id: str) -> Optional[SystemIssue]:
        """Get issue by issue_id string."""
        result = await self._session.execute(
            select(SystemIssue).where(SystemIssue.issue_id == issue_id)
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, service: Optional[str] = None, severity: Optional[str] = None
    ) -> List[SystemIssue]:
        """List active issues, optionally filtered by service and severity."""
        query = select(SystemIssue).where(SystemIssue.status == "active")
        
        if service:
            query = query.where(SystemIssue.service == service)
        
        if severity:
            query = query.where(SystemIssue.severity == severity)
        
        query = query.order_by(
            SystemIssue.severity.desc(),
            SystemIssue.detected_at.desc()
        )
        
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_all(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[SystemIssue]:
        """List all issues, optionally filtered by status."""
        query = select(SystemIssue)
        
        if status:
            query = query.where(SystemIssue.status == status)
        
        query = query.order_by(SystemIssue.detected_at.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, issue: SystemIssue) -> SystemIssue:
        """Update an existing issue."""
        issue.updated_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(issue)
        return issue

    async def resolve(self, issue_id: str) -> Optional[SystemIssue]:
        """Mark an issue as resolved."""
        issue = await self.get_by_issue_id(issue_id)
        if issue:
            issue.status = "resolved"
            issue.resolved_at = datetime.utcnow()
            issue.updated_at = datetime.utcnow()
            await self._session.flush()
            await self._session.refresh(issue)
        return issue

    async def count_active_by_severity(self, severity: str) -> int:
        """Count active issues by severity."""
        from sqlalchemy import func
        
        result = await self._session.execute(
            select(func.count(SystemIssue.id)).where(
                and_(
                    SystemIssue.status == "active",
                    SystemIssue.severity == severity
                )
            )
        )
        return result.scalar() or 0
