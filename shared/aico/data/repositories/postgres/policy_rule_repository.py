"""
PostgreSQL repository for agency policy rules.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.tables import agency_policy_rules
from aico.ai.agency.policy_manager import PolicyRule


class PostgresPolicyRuleRepository:
    """Repository for agency policy rules."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_active_policies(
        self,
        user_id: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> List[PolicyRule]:
        """
        Get active policy rules.
        
        Args:
            user_id: Optional user ID for user-specific policies (includes global)
            target_type: Optional filter by target type
            
        Returns:
            List of active policy rules ordered by priority DESC, created_at ASC
        """
        stmt = select(agency_policy_rules).where(
            agency_policy_rules.c.active == True
        )
        
        # Add user filter (include global + user-specific)
        if user_id:
            stmt = stmt.where(
                or_(
                    agency_policy_rules.c.user_id.is_(None),
                    agency_policy_rules.c.user_id == user_id
                )
            )
        else:
            stmt = stmt.where(agency_policy_rules.c.user_id.is_(None))
        
        # Add target type filter
        if target_type:
            stmt = stmt.where(agency_policy_rules.c.target_type == target_type)
        
        # Order by priority DESC, created_at ASC
        stmt = stmt.order_by(
            agency_policy_rules.c.priority.desc(),
            agency_policy_rules.c.created_at.asc()
        )
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        policies = []
        for row in rows:
            row_dict = dict(row._mapping)
            # Deserialize JSON conditions
            if isinstance(row_dict['conditions'], str):
                row_dict['conditions'] = json.loads(row_dict['conditions'])
            # Parse datetime strings
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = datetime.fromisoformat(row_dict['created_at']).replace(tzinfo=UTC)
            if isinstance(row_dict['updated_at'], str):
                row_dict['updated_at'] = datetime.fromisoformat(row_dict['updated_at']).replace(tzinfo=UTC)
            policies.append(PolicyRule(**row_dict))
        
        return policies
    
    async def create_policy(
        self,
        rule_id: str,
        rule_name: str,
        target_type: str,
        conditions: Dict[str, Any],
        effect: str,
        user_id: Optional[str] = None,
        user_message_template: Optional[str] = None,
        priority: int = 50,
        scope: str = "global"
    ) -> PolicyRule:
        """
        Create a new policy rule.
        
        Args:
            rule_id: Unique rule identifier
            rule_name: Human-readable name
            target_type: Type of target (goal, curiosity_signal, etc.)
            conditions: Conditions to match (dict)
            effect: Policy effect (allow, block, needs_consent, etc.)
            user_id: Optional user ID for user-specific policy
            user_message_template: Optional message template
            priority: Priority (higher = evaluated first)
            scope: Policy scope (global, user, deployment)
            
        Returns:
            Created PolicyRule
        """
        now = datetime.now(UTC)
        
        stmt = agency_policy_rules.insert().values(
            rule_id=rule_id,
            rule_name=rule_name,
            user_id=user_id,
            target_type=target_type,
            conditions=json.dumps(conditions),
            effect=effect,
            user_message_template=user_message_template,
            priority=priority,
            scope=scope,
            version=1,
            active=True,
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        )
        
        await self.session.execute(stmt)
        await self.session.flush()
        
        # Return the created policy
        result = await self.session.execute(
            select(agency_policy_rules).where(
                agency_policy_rules.c.rule_id == rule_id
            )
        )
        row = result.fetchone()
        row_dict = dict(row._mapping)
        # Deserialize JSON conditions
        if isinstance(row_dict['conditions'], str):
            row_dict['conditions'] = json.loads(row_dict['conditions'])
        # Parse datetime strings
        if isinstance(row_dict['created_at'], str):
            row_dict['created_at'] = datetime.fromisoformat(row_dict['created_at']).replace(tzinfo=UTC)
        if isinstance(row_dict['updated_at'], str):
            row_dict['updated_at'] = datetime.fromisoformat(row_dict['updated_at']).replace(tzinfo=UTC)
        return PolicyRule(**row_dict)
    
    async def update_policy(
        self,
        rule_id: str,
        conditions: Optional[Dict[str, Any]] = None,
        effect: Optional[str] = None,
        priority: Optional[int] = None,
        active: Optional[bool] = None
    ) -> bool:
        """
        Update an existing policy rule.
        
        Args:
            rule_id: Rule ID to update
            conditions: Optional new conditions
            effect: Optional new effect
            priority: Optional new priority
            active: Optional new active status
            
        Returns:
            True if updated, False if not found
        """
        values = {"updated_at": datetime.now(UTC).isoformat()}
        
        if conditions is not None:
            values["conditions"] = json.dumps(conditions)
        if effect is not None:
            values["effect"] = effect
        if priority is not None:
            values["priority"] = priority
        if active is not None:
            values["active"] = active
        
        if len(values) == 1:  # Only updated_at
            return False
        
        stmt = (
            update(agency_policy_rules)
            .where(agency_policy_rules.c.rule_id == rule_id)
            .values(**values)
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def delete_policy(self, rule_id: str) -> bool:
        """
        Delete a policy rule.
        
        Args:
            rule_id: Rule ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(agency_policy_rules).where(
            agency_policy_rules.c.rule_id == rule_id
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_by_rule_id(self, rule_id: str) -> Optional[PolicyRule]:
        """
        Get a policy rule by ID.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            PolicyRule if found, None otherwise
        """
        stmt = select(agency_policy_rules).where(
            agency_policy_rules.c.rule_id == rule_id
        )
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row:
            row_dict = dict(row._mapping)
            # Deserialize JSON conditions
            if isinstance(row_dict['conditions'], str):
                row_dict['conditions'] = json.loads(row_dict['conditions'])
            # Parse datetime strings
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = datetime.fromisoformat(row_dict['created_at']).replace(tzinfo=UTC)
            if isinstance(row_dict['updated_at'], str):
                row_dict['updated_at'] = datetime.fromisoformat(row_dict['updated_at']).replace(tzinfo=UTC)
            return PolicyRule(**row_dict)
        return None
