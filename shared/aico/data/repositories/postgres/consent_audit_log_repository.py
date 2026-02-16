"""
ConsentAuditLogRepository - PostgreSQL implementation

Handles CRUD operations for consent audit log.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.consent.models import ConsentAuditLog
from aico.data.tables import consent_audit_log
from aico.data.repositories.base import Repository


class PostgresConsentAuditLogRepository(Repository[ConsentAuditLog]):
    """PostgreSQL implementation of consent audit log repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ConsentAuditLog) -> ConsentAuditLog:
        """Create a new audit log entry."""
        stmt = consent_audit_log.insert().values(
            audit_id=entity.audit_id,
            consent_id=entity.consent_id,
            user_id=entity.user_id,
            action=entity.action,
            reason=entity.reason,
            metadata=entity.metadata,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ConsentAuditLog]:
        """Get audit log entry by ID."""
        stmt = select(consent_audit_log).where(consent_audit_log.c.audit_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ConsentAuditLog(
            audit_id=row.audit_id,
            consent_id=row.consent_id,
            user_id=row.user_id,
            action=row.action,
            reason=row.reason,
            metadata=row.metadata,
            created_at=row.created_at,
        )
    
    async def update(self, entity: ConsentAuditLog) -> ConsentAuditLog:
        """Update an existing audit log entry."""
        stmt = (
            update(consent_audit_log)
            .where(consent_audit_log.c.audit_id == entity.audit_id)
            .values(
                reason=entity.reason,
                metadata=entity.metadata,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an audit log entry."""
        stmt = delete(consent_audit_log).where(consent_audit_log.c.audit_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ConsentAuditLog]:
        """List audit log entries with optional filters."""
        stmt = select(consent_audit_log)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_audit_log.c.user_id == filters['user_id'])
            if 'consent_id' in filters:
                conditions.append(consent_audit_log.c.consent_id == filters['consent_id'])
            if 'action' in filters:
                conditions.append(consent_audit_log.c.action == filters['action'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(consent_audit_log.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ConsentAuditLog(
                audit_id=row.audit_id,
                consent_id=row.consent_id,
                user_id=row.user_id,
                action=row.action,
                reason=row.reason,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count audit log entries with optional filters."""
        stmt = select(func.count()).select_from(consent_audit_log)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_audit_log.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_consent_history(self, consent_id: str) -> List[ConsentAuditLog]:
        """Get audit history for a specific consent."""
        stmt = select(consent_audit_log).where(
            consent_audit_log.c.consent_id == consent_id
        ).order_by(consent_audit_log.c.created_at.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            ConsentAuditLog(
                audit_id=row.audit_id,
                consent_id=row.consent_id,
                user_id=row.user_id,
                action=row.action,
                reason=row.reason,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
