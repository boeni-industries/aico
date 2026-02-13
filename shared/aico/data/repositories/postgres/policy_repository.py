"""
PolicyRepository - PostgreSQL implementation

Handles CRUD operations for agency policy rules.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.models import Policy
from aico.data.tables import agency_policy_rules
from aico.data.repositories.base import Repository


class PostgresPolicyRepository(Repository[Policy]):
    """PostgreSQL implementation of policy repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Policy) -> Policy:
        """Create a new policy rule."""
        from datetime import datetime, UTC
        now = datetime.now(UTC)
        
        stmt = agency_policy_rules.insert().values(
            rule_id=entity.rule_id,
            rule_name=entity.rule_name,
            user_id=entity.user_id,
            target_type=entity.target_type,
            conditions=entity.conditions,
            effect=entity.effect,
            user_message_template=entity.user_message_template,
            priority=entity.priority,
            scope=entity.scope,
            version=entity.version,
            active=entity.active,
            created_at=getattr(entity, 'created_at', None) or now,
            updated_at=getattr(entity, 'updated_at', None) or now,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        stmt = select(agency_policy_rules).where(agency_policy_rules.c.rule_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        
        
        return Policy(
            rule_id=row.rule_id,
            rule_name=row.rule_name,
            user_id=row.user_id,
            target_type=row.target_type,
            conditions=row.conditions,
            effect=row.effect,
            user_message_template=row.user_message_template,
            priority=row.priority,
            scope=row.scope,
            version=row.version,
            active=row.active,
            created_at=row.created_at if hasattr(row, 'created_at') else None,
            updated_at=row.updated_at if hasattr(row, 'updated_at') else None,
        )
    
    async def update(self, entity: Policy) -> Policy:
        """Update an existing policy."""
        stmt = (
            update(agency_policy_rules)
            .where(agency_policy_rules.c.rule_id == entity.rule_id)
            .values(
                rule_name=entity.rule_name,
                conditions=entity.conditions,
                effect=entity.effect,
                user_message_template=entity.user_message_template,
                priority=entity.priority,
                active=entity.active,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a policy."""
        stmt = delete(agency_policy_rules).where(agency_policy_rules.c.rule_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Policy]:
        """List policies with optional filters."""
        stmt = select(agency_policy_rules)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_policy_rules.c.user_id == filters['user_id'])
            if 'target_type' in filters:
                conditions.append(agency_policy_rules.c.target_type == filters['target_type'])
            if 'scope' in filters:
                conditions.append(agency_policy_rules.c.scope == filters['scope'])
            if 'active' in filters:
                conditions.append(agency_policy_rules.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_policy_rules.c.priority.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Policy(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                user_id=row.user_id,
                target_type=row.target_type,
                conditions=row.conditions,
                effect=row.effect,
                user_message_template=row.user_message_template,
                priority=row.priority,
                scope=row.scope,
                version=row.version,
                active=row.active,
                created_at=row.created_at if isinstance(row.created_at, str) else row.created_at,
                updated_at=row.updated_at if isinstance(row.updated_at, str) else row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count policies with optional filters."""
        stmt = select(func.count()).select_from(agency_policy_rules)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_policy_rules.c.user_id == filters['user_id'])
            if 'active' in filters:
                conditions.append(agency_policy_rules.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_policies_for_user(self, user_id: Optional[str], target_type: str) -> List[Policy]:
        """Get active policies for a user and target type, including global policies."""
        conditions = [
            agency_policy_rules.c.active == True,
            agency_policy_rules.c.target_type == target_type,
        ]
        
        # Include user-specific and global policies
        if user_id:
            from sqlalchemy import or_
            conditions.append(
                or_(
                    agency_policy_rules.c.user_id == user_id,
                    agency_policy_rules.c.user_id.is_(None)
                )
            )
        else:
            conditions.append(agency_policy_rules.c.user_id.is_(None))
        
        stmt = select(agency_policy_rules).where(
            and_(*conditions)
        ).order_by(agency_policy_rules.c.priority.desc())
        
        result = await self.session.execute(stmt)
        
        
        
        return [
            Policy(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                user_id=row.user_id,
                target_type=row.target_type,
                conditions=row.conditions,
                effect=row.effect,
                user_message_template=row.user_message_template,
                priority=row.priority,
                scope=row.scope,
                version=row.version,
                active=row.active,
                created_at=row.created_at if hasattr(row, 'created_at') else None,
                updated_at=row.updated_at if hasattr(row, 'updated_at') else None,
            )
            for row in result.fetchall()
        ]
