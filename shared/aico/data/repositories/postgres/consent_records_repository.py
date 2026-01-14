"""
ConsentRecordsRepository - PostgreSQL implementation

Handles CRUD operations for consent records.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.consent.models import ConsentRecord
from aico.data.tables import consent_records
from aico.data.repositories.base import Repository

import json

class PostgresConsentRecordsRepository(Repository[ConsentRecord]):
    """PostgreSQL implementation of consent records repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ConsentRecord) -> ConsentRecord:
        """Create a new consent record."""
        stmt = consent_records.insert().values(
            consent_id=entity.consent_id,
            user_id=entity.user_id,
            consent_scope=entity.consent_scope,
            decision=entity.decision,
            context_json=json.dumps(entity.context_json) if entity.context_json else None,
            granted_at=entity.granted_at,
            expires_at=entity.expires_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ConsentRecord]:
        """Get consent record by ID."""
        stmt = select(consent_records).where(consent_records.c.consent_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ConsentRecord(
            consent_id=row.consent_id,
            user_id=row.user_id,
            consent_scope=row.consent_scope,
            decision=row.decision,
            context_json=row.context_json,
            granted_at=row.granted_at,
            expires_at=row.expires_at,
        )
    
    async def update(self, entity: ConsentRecord) -> ConsentRecord:
        """Update an existing consent record."""
        stmt = (
            update(consent_records)
            .where(consent_records.c.consent_id == entity.consent_id)
            .values(
                decision=entity.decision,
                context_json=json.dumps(entity.context_json) if entity.context_json else None,
                expires_at=entity.expires_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a consent record."""
        stmt = delete(consent_records).where(consent_records.c.consent_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ConsentRecord]:
        """List consent records with optional filters."""
        stmt = select(consent_records)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_records.c.user_id == filters['user_id'])
            if 'decision' in filters:
                conditions.append(consent_records.c.decision == filters['decision'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(consent_records.c.granted_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ConsentRecord(
                consent_id=row.consent_id,
                user_id=row.user_id,
                consent_scope=row.consent_scope,
                decision=row.decision,
                context_json=row.context_json,
                granted_at=row.granted_at,
                expires_at=row.expires_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count consent records with optional filters."""
        stmt = select(func.count()).select_from(consent_records)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_records.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        stmt = select(consent_records).where(
            consent_records.c.user_id == user_id
        ).order_by(consent_records.c.granted_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ConsentRecord(
                consent_id=row.consent_id,
                user_id=row.user_id,
                consent_scope=row.consent_scope,
                decision=row.decision,
                context_json=row.context_json,
                granted_at=row.granted_at,
                expires_at=row.expires_at,
            )
            for row in result.fetchall()
        ]
