"""
PlanRepository - PostgreSQL implementation

Handles CRUD operations for agency plans.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.models import Plan
from aico.data.tables import agency_plans
from aico.data.repositories.base import Repository

import json

class PostgresPlanRepository(Repository[Plan]):
    """PostgreSQL implementation of plan repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Plan) -> Plan:
        """Create a new plan."""
        stmt = agency_plans.insert().values(
            plan_id=entity.plan_id,
            goal_id=entity.goal_id,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            steps_json=json.dumps(entity.steps_json) if entity.steps_json else None,
            metadata_json=json.dumps(entity.metadata) if entity.metadata else None,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Plan]:
        """Get plan by ID."""
        stmt = select(agency_plans).where(agency_plans.c.plan_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Plan(
            plan_id=row.plan_id,
            goal_id=row.goal_id,
            title=row.title,
            description=row.description,
            status=row.status,
            steps_json=json.loads(row.steps_json) if row.steps_json else [],
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Plan) -> Plan:
        """Update an existing plan."""
        stmt = (
            update(agency_plans)
            .where(agency_plans.c.plan_id == entity.plan_id)
            .values(
                status=entity.status,
                steps_json=json.dumps(entity.steps_json) if entity.steps_json else None,
                metadata_json=json.dumps(entity.metadata) if entity.metadata else None,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a plan."""
        stmt = delete(agency_plans).where(agency_plans.c.plan_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Plan]:
        """List plans with optional filters."""
        stmt = select(agency_plans)
        
        if filters:
            conditions = []
            if 'goal_id' in filters:
                conditions.append(agency_plans.c.goal_id == filters['goal_id'])
            if 'status' in filters:
                conditions.append(agency_plans.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_plans.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Plan(
                plan_id=row.plan_id,
                goal_id=row.goal_id,
                status=row.status,
                steps_json=row.steps_json,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count plans with optional filters."""
        stmt = select(func.count()).select_from(agency_plans)
        
        if filters:
            conditions = []
            if 'goal_id' in filters:
                conditions.append(agency_plans.c.goal_id == filters['goal_id'])
            if 'status' in filters:
                conditions.append(agency_plans.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_plans_for_goal(self, goal_id: str) -> List[Plan]:
        """Get all plans for a specific goal."""
        stmt = select(agency_plans).where(
            agency_plans.c.goal_id == goal_id
        ).order_by(agency_plans.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Plan(
                plan_id=row.plan_id,
                goal_id=row.goal_id,
                status=row.status,
                steps_json=row.steps_json,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_active_plan_for_goal(self, goal_id: str) -> Optional[Plan]:
        """Get the active plan for a goal."""
        stmt = select(agency_plans).where(
            and_(
                agency_plans.c.goal_id == goal_id,
                agency_plans.c.status == 'active'
            )
        ).order_by(agency_plans.c.created_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Plan(
            plan_id=row.plan_id,
            goal_id=row.goal_id,
            status=row.status,
            steps_json=row.steps_json,
            metadata_json=row.metadata_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update_status(self, plan_id: str, new_status: str) -> bool:
        """Update plan status."""
        stmt = (
            update(agency_plans)
            .where(agency_plans.c.plan_id == plan_id)
            .values(
                status=new_status,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
