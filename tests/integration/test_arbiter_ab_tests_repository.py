"""
Integration tests for ArbiterABTestsRepository.

Tests ArbiterABTestsRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.arbiter.models import ArbiterABTest
from aico.data.arbiter.bandit_models import ArbiterBanditArm
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_arms(uow):
    """Create test bandit arms for FK constraints."""
    arms = []
    for i in range(10):
        arm = ArbiterBanditArm(
            arm_id=f"arm_{chr(97+i)}_{i}",
            weights_json={"weight": 1.0},
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        existing = await uow.arbiter_bandit_arms.get_by_id(arm.arm_id)
        if not existing:
            await uow.arbiter_bandit_arms.create(arm)
        arms.append(arm)
    await uow.commit()
    return arms


class TestArbiterABTestsRepository:
    """Test ArbiterABTestsRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_ab_test(self, uow, test_arms):
        """Test creating a new A/B test."""
        test = ArbiterABTest(
            test_id=str(uuid.uuid4()),
            test_name="Test A vs B",
            arm_a_id=test_arms[0].arm_id,
            arm_b_id=test_arms[1].arm_id,
            start_date=datetime.now(UTC).isoformat(),
            end_date=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.arbiter_ab_tests.create(test)
        await uow.commit()
        
        assert created.test_id == test.test_id
        assert created.test_name == "Test A vs B"
        assert created.status == 'active'
    
    @pytest.mark.asyncio
    async def test_get_ab_test_by_id(self, uow, test_arms):
        """Test retrieving A/B test by ID."""
        test = ArbiterABTest(
            test_id=str(uuid.uuid4()),
            test_name="Get Test",
            arm_a_id=test_arms[2].arm_id,
            arm_b_id=test_arms[3].arm_id,
            start_date=datetime.now(UTC).isoformat(),
            end_date=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.arbiter_ab_tests.create(test)
        await uow.commit()
        
        found = await uow.arbiter_ab_tests.get_by_id(test.test_id)
        assert found is not None
        assert found.test_id == test.test_id
        assert found.test_name == "Get Test"
    
    @pytest.mark.asyncio
    async def test_update_ab_test(self, uow, test_arms):
        """Test updating an A/B test."""
        test = ArbiterABTest(
            test_id=str(uuid.uuid4()),
            test_name="Update Test",
            arm_a_id=test_arms[4].arm_id,
            arm_b_id=test_arms[5].arm_id,
            start_date=datetime.now(UTC).isoformat(),
            end_date=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.arbiter_ab_tests.create(test)
        await uow.commit()
        
        test.status = 'completed'
        test.winner_arm_id = test_arms[4].arm_id
        test.confidence_score = 0.95
        updated = await uow.arbiter_ab_tests.update(test)
        await uow.commit()
        
        assert updated.status == 'completed'
        
        found = await uow.arbiter_ab_tests.get_by_id(test.test_id)
        assert found.winner_arm_id == test_arms[4].arm_id
        assert found.confidence_score == 0.95
    
    @pytest.mark.asyncio
    async def test_delete_ab_test(self, uow, test_arms):
        """Test deleting an A/B test."""
        test = ArbiterABTest(
            test_id=str(uuid.uuid4()),
            test_name="Delete Test",
            arm_a_id=test_arms[6].arm_id,
            arm_b_id=test_arms[7].arm_id,
            start_date=datetime.now(UTC).isoformat(),
            end_date=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.arbiter_ab_tests.create(test)
        await uow.commit()
        
        success = await uow.arbiter_ab_tests.delete(test.test_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.arbiter_ab_tests.get_by_id(test.test_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_ab_tests(self, uow, test_arms):
        """Test listing A/B tests with filters."""
        for i in range(3):
            test = ArbiterABTest(
                test_id=str(uuid.uuid4()),
                test_name=f"List Test {i}",
                arm_a_id=test_arms[0].arm_id,
                arm_b_id=test_arms[1].arm_id,
                start_date=datetime.now(UTC).isoformat(),
                end_date=datetime.now(UTC).isoformat(),
                status='active' if i < 2 else 'completed',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.arbiter_ab_tests.create(test)
        
        await uow.commit()
        
        all_tests = await uow.arbiter_ab_tests.list()
        assert len(all_tests) >= 3
        
        active_tests = await uow.arbiter_ab_tests.list(filters={"status": "active"})
        assert len(active_tests) >= 2
    
    @pytest.mark.asyncio
    async def test_count_ab_tests(self, uow, test_arms):
        """Test counting A/B tests."""
        for i in range(3):
            test = ArbiterABTest(
                test_id=str(uuid.uuid4()),
                test_name=f"Count Test {i}",
                arm_a_id=test_arms[0].arm_id,
                arm_b_id=test_arms[1].arm_id,
                start_date=datetime.now(UTC).isoformat(),
                end_date=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.arbiter_ab_tests.create(test)
        
        await uow.commit()
        
        count = await uow.arbiter_ab_tests.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_tests(self, uow, test_arms):
        """Test getting active A/B tests."""
        for i in range(3):
            test = ArbiterABTest(
                test_id=str(uuid.uuid4()),
                test_name=f"Active Test {i}",
                arm_a_id=test_arms[0].arm_id,
                arm_b_id=test_arms[1].arm_id,
                start_date=datetime.now(UTC).isoformat(),
                end_date=datetime.now(UTC).isoformat(),
                status='active' if i < 2 else 'cancelled',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.arbiter_ab_tests.create(test)
        
        await uow.commit()
        
        active = await uow.arbiter_ab_tests.get_active_tests()
        assert len(active) >= 2
        for test in active:
            assert test.status == 'active'
