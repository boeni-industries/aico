"""
EthicsPolicyRulesRepository - PostgreSQL implementation

Handles CRUD operations for ethics policy rules.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from aico.data.ethics.models import EthicsPolicyRule
from aico.data.tables import ethics_policy_rules
from aico.data.repositories.base import Repository


class PostgresEthicsPolicyRulesRepository(Repository[EthicsPolicyRule]):
    """PostgreSQL implementation of ethics policy rules repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EthicsPolicyRule) -> EthicsPolicyRule:
        """Create a new policy rule."""
        stmt = ethics_policy_rules.insert().values(
            rule_id=entity.rule_id,
            rule_name=entity.rule_name,
            target_type=entity.target_type,
            conditions_json=entity.conditions_json,
            effect=entity.effect,
            user_message_template=entity.user_message_template,
            priority=entity.priority,
            enabled=entity.enabled,
            scope=entity.scope,
            scope_id=entity.scope_id,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[EthicsPolicyRule]:
        """Get policy rule by ID."""
        stmt = select(ethics_policy_rules).where(ethics_policy_rules.c.rule_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsPolicyRule(
            rule_id=row.rule_id,
            rule_name=row.rule_name,
            target_type=row.target_type,
            conditions_json=json.loads(row.conditions_json) if isinstance(row.conditions_json, str) else row.conditions_json,
            effect=row.effect,
            user_message_template=row.user_message_template,
            priority=row.priority,
            enabled=row.enabled,
            scope=row.scope,
            scope_id=row.scope_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: EthicsPolicyRule) -> EthicsPolicyRule:
        """Update an existing policy rule."""
        stmt = (
            update(ethics_policy_rules)
            .where(ethics_policy_rules.c.rule_id == entity.rule_id)
            .values(
                rule_name=entity.rule_name,
                conditions_json=entity.conditions_json,
                effect=entity.effect,
                user_message_template=entity.user_message_template,
                priority=entity.priority,
                enabled=entity.enabled,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a policy rule."""
        stmt = delete(ethics_policy_rules).where(ethics_policy_rules.c.rule_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EthicsPolicyRule]:
        """List policy rules with optional filters."""
        stmt = select(ethics_policy_rules)
        
        if filters:
            conditions = []
            if 'target_type' in filters:
                conditions.append(ethics_policy_rules.c.target_type == filters['target_type'])
            if 'enabled' in filters:
                conditions.append(ethics_policy_rules.c.enabled == filters['enabled'])
            if 'scope' in filters:
                conditions.append(ethics_policy_rules.c.scope == filters['scope'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ethics_policy_rules.c.priority.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EthicsPolicyRule(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                target_type=row.target_type,
                conditions_json=json.loads(row.conditions_json) if isinstance(row.conditions_json, str) else row.conditions_json,
                effect=row.effect,
                user_message_template=row.user_message_template,
                priority=row.priority,
                enabled=row.enabled,
                scope=row.scope,
                scope_id=row.scope_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count policy rules with optional filters."""
        stmt = select(func.count()).select_from(ethics_policy_rules)
        
        if filters:
            conditions = []
            if 'enabled' in filters:
                conditions.append(ethics_policy_rules.c.enabled == filters['enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_rules(self, target_type: str) -> List[EthicsPolicyRule]:
        """Get active rules for a specific target type."""
        stmt = select(ethics_policy_rules).where(
            and_(
                ethics_policy_rules.c.target_type == target_type,
                ethics_policy_rules.c.enabled == True
            )
        ).order_by(ethics_policy_rules.c.priority.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            EthicsPolicyRule(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                target_type=row.target_type,
                conditions_json=json.loads(row.conditions_json) if isinstance(row.conditions_json, str) else row.conditions_json,
                effect=row.effect,
                user_message_template=row.user_message_template,
                priority=row.priority,
                enabled=row.enabled,
                scope=row.scope,
                scope_id=row.scope_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
