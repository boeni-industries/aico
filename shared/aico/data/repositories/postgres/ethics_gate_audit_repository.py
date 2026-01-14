"""
EthicsGateAuditRepository - PostgreSQL implementation

Handles CRUD operations for ethics gate audit.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ethics.audit_models import EthicsGateAudit
from aico.data.tables import ethics_gate_audit
from aico.data.repositories.base import Repository


class PostgresEthicsGateAuditRepository(Repository[EthicsGateAudit]):
    """PostgreSQL implementation of ethics gate audit repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EthicsGateAudit) -> EthicsGateAudit:
        """Create a new audit entry."""
        stmt = ethics_gate_audit.insert().values(
            audit_id=entity.audit_id,
            user_id=entity.user_id,
            target_type=entity.target_type,
            target_id=entity.target_id,
            decision=entity.decision,
            reasoning=entity.reasoning,
            policy_rules_applied=entity.policy_rules_applied,
            check_level=entity.check_level,
            cached=entity.cached,
            processing_time_ms=entity.processing_time_ms,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[EthicsGateAudit]:
        """Get audit entry by ID."""
        stmt = select(ethics_gate_audit).where(ethics_gate_audit.c.audit_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsGateAudit(
            audit_id=row.audit_id,
            user_id=row.user_id,
            target_type=row.target_type,
            target_id=row.target_id,
            decision=row.decision,
            reasoning=row.reasoning,
            policy_rules_applied=row.policy_rules_applied,
            check_level=row.check_level,
            cached=row.cached,
            processing_time_ms=row.processing_time_ms,
            created_at=row.created_at,
        )
    
    async def update(self, entity: EthicsGateAudit) -> EthicsGateAudit:
        """Update an existing audit entry."""
        stmt = (
            update(ethics_gate_audit)
            .where(ethics_gate_audit.c.audit_id == entity.audit_id)
            .values(
                reasoning=entity.reasoning,
                processing_time_ms=entity.processing_time_ms,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an audit entry."""
        stmt = delete(ethics_gate_audit).where(ethics_gate_audit.c.audit_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EthicsGateAudit]:
        """List audit entries with optional filters."""
        stmt = select(ethics_gate_audit)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_gate_audit.c.user_id == filters['user_id'])
            if 'target_type' in filters:
                conditions.append(ethics_gate_audit.c.target_type == filters['target_type'])
            if 'decision' in filters:
                conditions.append(ethics_gate_audit.c.decision == filters['decision'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ethics_gate_audit.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EthicsGateAudit(
                audit_id=row.audit_id,
                user_id=row.user_id,
                target_type=row.target_type,
                target_id=row.target_id,
                decision=row.decision,
                reasoning=row.reasoning,
                policy_rules_applied=row.policy_rules_applied,
                check_level=row.check_level,
                cached=row.cached,
                processing_time_ms=row.processing_time_ms,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count audit entries with optional filters."""
        stmt = select(func.count()).select_from(ethics_gate_audit)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_gate_audit.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_audit_trail(self, user_id: str, limit: int = 100) -> List[EthicsGateAudit]:
        """Get audit trail for a specific user."""
        stmt = select(ethics_gate_audit).where(
            ethics_gate_audit.c.user_id == user_id
        ).order_by(ethics_gate_audit.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            EthicsGateAudit(
                audit_id=row.audit_id,
                user_id=row.user_id,
                target_type=row.target_type,
                target_id=row.target_id,
                decision=row.decision,
                reasoning=row.reasoning,
                policy_rules_applied=row.policy_rules_applied,
                check_level=row.check_level,
                cached=row.cached,
                processing_time_ms=row.processing_time_ms,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
