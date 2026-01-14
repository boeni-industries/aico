"""
ArbiterABTestsRepository - PostgreSQL implementation

Handles CRUD operations for arbiter A/B tests.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.arbiter.models import ArbiterABTest
from aico.data.tables import arbiter_ab_tests
from aico.data.repositories.base import Repository


class PostgresArbiterABTestsRepository(Repository[ArbiterABTest]):
    """PostgreSQL implementation of arbiter A/B tests repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ArbiterABTest) -> ArbiterABTest:
        """Create a new A/B test."""
        stmt = arbiter_ab_tests.insert().values(
            test_id=entity.test_id,
            test_name=entity.test_name,
            arm_a_id=entity.arm_a_id,
            arm_b_id=entity.arm_b_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            status=entity.status,
            winner_arm_id=entity.winner_arm_id,
            confidence_score=entity.confidence_score,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ArbiterABTest]:
        """Get A/B test by ID."""
        stmt = select(arbiter_ab_tests).where(arbiter_ab_tests.c.test_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ArbiterABTest(
            test_id=row.test_id,
            test_name=row.test_name,
            arm_a_id=row.arm_a_id,
            arm_b_id=row.arm_b_id,
            start_date=row.start_date,
            end_date=row.end_date,
            status=row.status,
            winner_arm_id=row.winner_arm_id,
            confidence_score=row.confidence_score,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: ArbiterABTest) -> ArbiterABTest:
        """Update an existing A/B test."""
        stmt = (
            update(arbiter_ab_tests)
            .where(arbiter_ab_tests.c.test_id == entity.test_id)
            .values(
                status=entity.status,
                winner_arm_id=entity.winner_arm_id,
                confidence_score=entity.confidence_score,
                notes=entity.notes,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an A/B test."""
        stmt = delete(arbiter_ab_tests).where(arbiter_ab_tests.c.test_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ArbiterABTest]:
        """List A/B tests with optional filters."""
        stmt = select(arbiter_ab_tests)
        
        if filters:
            conditions = []
            if 'status' in filters:
                conditions.append(arbiter_ab_tests.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(arbiter_ab_tests.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ArbiterABTest(
                test_id=row.test_id,
                test_name=row.test_name,
                arm_a_id=row.arm_a_id,
                arm_b_id=row.arm_b_id,
                start_date=row.start_date,
                end_date=row.end_date,
                status=row.status,
                winner_arm_id=row.winner_arm_id,
                confidence_score=row.confidence_score,
                notes=row.notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count A/B tests with optional filters."""
        stmt = select(func.count()).select_from(arbiter_ab_tests)
        
        if filters:
            conditions = []
            if 'status' in filters:
                conditions.append(arbiter_ab_tests.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_tests(self) -> List[ArbiterABTest]:
        """Get all active A/B tests."""
        stmt = select(arbiter_ab_tests).where(
            arbiter_ab_tests.c.status == 'active'
        ).order_by(arbiter_ab_tests.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ArbiterABTest(
                test_id=row.test_id,
                test_name=row.test_name,
                arm_a_id=row.arm_a_id,
                arm_b_id=row.arm_b_id,
                start_date=row.start_date,
                end_date=row.end_date,
                status=row.status,
                winner_arm_id=row.winner_arm_id,
                confidence_score=row.confidence_score,
                notes=row.notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
