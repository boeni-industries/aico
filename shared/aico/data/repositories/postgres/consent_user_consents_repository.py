"""
ConsentUserConsentsRepository - PostgreSQL implementation

Handles CRUD operations for user consents.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.consent.models import ConsentUserConsent
from aico.data.tables import consent_user_consents
from aico.data.repositories.base import Repository


class PostgresConsentUserConsentsRepository(Repository[ConsentUserConsent]):
    """PostgreSQL implementation of consent user consents repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ConsentUserConsent) -> ConsentUserConsent:
        """Create a new consent."""
        stmt = consent_user_consents.insert().values(
            consent_id=entity.consent_id,
            user_id=entity.user_id,
            consent_type=entity.consent_type,
            scope=entity.scope,
            scope_identifier=entity.scope_identifier,
            granted=entity.granted,
            expires_at=entity.expires_at,
            inherited_from=entity.inherited_from,
            granted_at=entity.granted_at,
            revoked_at=entity.revoked_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ConsentUserConsent]:
        """Get consent by ID."""
        stmt = select(consent_user_consents).where(consent_user_consents.c.consent_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ConsentUserConsent(
            consent_id=row.consent_id,
            user_id=row.user_id,
            consent_type=row.consent_type,
            scope=row.scope,
            scope_identifier=row.scope_identifier,
            granted=row.granted,
            expires_at=row.expires_at,
            inherited_from=row.inherited_from,
            granted_at=row.granted_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: ConsentUserConsent) -> ConsentUserConsent:
        """Update an existing consent."""
        stmt = (
            update(consent_user_consents)
            .where(consent_user_consents.c.consent_id == entity.consent_id)
            .values(
                granted=entity.granted,
                revoked_at=entity.revoked_at,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a consent."""
        stmt = delete(consent_user_consents).where(consent_user_consents.c.consent_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ConsentUserConsent]:
        """List consents with optional filters."""
        stmt = select(consent_user_consents)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_user_consents.c.user_id == filters['user_id'])
            if 'consent_type' in filters:
                conditions.append(consent_user_consents.c.consent_type == filters['consent_type'])
            if 'granted' in filters:
                conditions.append(consent_user_consents.c.granted == filters['granted'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(consent_user_consents.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ConsentUserConsent(
                consent_id=row.consent_id,
                user_id=row.user_id,
                consent_type=row.consent_type,
                scope=row.scope,
                scope_identifier=row.scope_identifier,
                granted=row.granted,
                expires_at=row.expires_at,
                inherited_from=row.inherited_from,
                granted_at=row.granted_at,
                revoked_at=row.revoked_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count consents with optional filters."""
        stmt = select(func.count()).select_from(consent_user_consents)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(consent_user_consents.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_consents(self, user_id: str, consent_type: str) -> List[ConsentUserConsent]:
        """Get active consents for user and type."""
        stmt = select(consent_user_consents).where(
            and_(
                consent_user_consents.c.user_id == user_id,
                consent_user_consents.c.consent_type == consent_type,
                consent_user_consents.c.granted == 1,
                consent_user_consents.c.revoked_at.is_(None)
            )
        ).order_by(consent_user_consents.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ConsentUserConsent(
                consent_id=row.consent_id,
                user_id=row.user_id,
                consent_type=row.consent_type,
                scope=row.scope,
                scope_identifier=row.scope_identifier,
                granted=row.granted,
                expires_at=row.expires_at,
                inherited_from=row.inherited_from,
                granted_at=row.granted_at,
                revoked_at=row.revoked_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
