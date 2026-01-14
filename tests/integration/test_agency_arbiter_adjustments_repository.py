"""
Integration tests for AgencyArbiterAdjustmentsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.arbiter_models import AgencyArbiterAdjustment
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    user_id = "arbiter_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Arbiter Test User",
            nickname="arbiter_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAgencyArbiterAdjustmentsRepository:
    
    @pytest.mark.asyncio
    async def test_create_adjustment(self, uow, test_user):
        adjustment = AgencyArbiterAdjustment(
            adjustment_key=f"test_key_{uuid.uuid4()}",
            adjustment_value=1.5,
            lesson_id="test_lesson_id",
            user_id=test_user.uuid,
            applied_at=datetime.now(UTC),
            confidence=0.85,
            active=True,
        )
        
        created = await uow.agency_arbiter_adjustments.create(adjustment)
        await uow.commit()
        
        assert created.adjustment_key == adjustment.adjustment_key
        assert created.adjustment_value == 1.5
    
    @pytest.mark.asyncio
    async def test_get_adjustment_by_id(self, uow, test_user):
        adjustment = AgencyArbiterAdjustment(
            adjustment_key=f"test_key_{uuid.uuid4()}",
            adjustment_value=2.0,
            lesson_id="test_lesson_id",
            user_id=test_user.uuid,
            applied_at=datetime.now(UTC),
            confidence=0.9,
        )
        
        await uow.agency_arbiter_adjustments.create(adjustment)
        await uow.commit()
        
        found = await uow.agency_arbiter_adjustments.get_by_id(adjustment.adjustment_key)
        assert found is not None
        assert found.adjustment_value == 2.0
    
    @pytest.mark.asyncio
    async def test_update_adjustment(self, uow, test_user):
        adjustment = AgencyArbiterAdjustment(
            adjustment_key=f"test_key_{uuid.uuid4()}",
            adjustment_value=1.0,
            lesson_id="test_lesson_id",
            user_id=test_user.uuid,
            applied_at=datetime.now(UTC),
            confidence=0.7,
            active=True,
        )
        
        await uow.agency_arbiter_adjustments.create(adjustment)
        await uow.commit()
        
        adjustment.adjustment_value = 2.5
        adjustment.confidence = 0.95
        updated = await uow.agency_arbiter_adjustments.update(adjustment)
        await uow.commit()
        
        assert updated.adjustment_value == 2.5
        
        found = await uow.agency_arbiter_adjustments.get_by_id(adjustment.adjustment_key)
        assert found.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_delete_adjustment(self, uow, test_user):
        adjustment = AgencyArbiterAdjustment(
            adjustment_key=f"test_key_{uuid.uuid4()}",
            adjustment_value=1.0,
            lesson_id="test_lesson_id",
            user_id=test_user.uuid,
            applied_at=datetime.now(UTC),
            confidence=0.8,
        )
        
        await uow.agency_arbiter_adjustments.create(adjustment)
        await uow.commit()
        
        success = await uow.agency_arbiter_adjustments.delete(adjustment.adjustment_key)
        await uow.commit()
        
        assert success is True
        
        found = await uow.agency_arbiter_adjustments.get_by_id(adjustment.adjustment_key)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_adjustments(self, uow, test_user):
        for i in range(3):
            adjustment = AgencyArbiterAdjustment(
                adjustment_key=f"test_key_{uuid.uuid4()}",
                adjustment_value=float(i),
                lesson_id="test_lesson_id",
                user_id=test_user.uuid,
                applied_at=datetime.now(UTC),
                confidence=0.8,
                active=True if i < 2 else False,
            )
            await uow.agency_arbiter_adjustments.create(adjustment)
        
        await uow.commit()
        
        all_adjustments = await uow.agency_arbiter_adjustments.list(filters={"user_id": test_user.uuid})
        assert len(all_adjustments) >= 3
        
        active = await uow.agency_arbiter_adjustments.list(filters={"active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_adjustments(self, uow, test_user):
        for i in range(3):
            adjustment = AgencyArbiterAdjustment(
                adjustment_key=f"count_key_{uuid.uuid4()}",
                adjustment_value=float(i),
                lesson_id="test_lesson_id",
                user_id=test_user.uuid,
                applied_at=datetime.now(UTC),
                confidence=0.8,
            )
            await uow.agency_arbiter_adjustments.create(adjustment)
        
        await uow.commit()
        
        count = await uow.agency_arbiter_adjustments.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_adjustments(self, uow, test_user):
        for i in range(3):
            adjustment = AgencyArbiterAdjustment(
                adjustment_key=f"active_key_{uuid.uuid4()}",
                adjustment_value=float(i),
                lesson_id="test_lesson_id",
                user_id=test_user.uuid,
                applied_at=datetime.now(UTC),
                confidence=0.8,
                active=True if i < 2 else False,
            )
            await uow.agency_arbiter_adjustments.create(adjustment)
        
        await uow.commit()
        
        active = await uow.agency_arbiter_adjustments.get_active_adjustments(test_user.uuid)
        assert len(active) >= 2
        for adj in active:
            assert adj.active is True
