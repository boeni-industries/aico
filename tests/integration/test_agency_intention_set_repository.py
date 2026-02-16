"""Integration tests for AgencyIntentionSetRepository."""

import pytest
import uuid
from aico.data.agency.goal_models import AgencyIntentionSet
from datetime import datetime, UTC


class TestAgencyIntentionSetRepository:
    
    @pytest.mark.asyncio
    async def test_create_intention(self, uow, test_user, test_goal):
        intention = AgencyIntentionSet(
            intention_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="proposed",
            arbiter_score=0.85,
            priority_band="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.agency_intention_set.create(intention)
        await uow.commit()
        
        assert created.intention_id == intention.intention_id
        assert created.arbiter_score == 0.85
    
    @pytest.mark.asyncio
    async def test_get_intention_by_id(self, uow, test_user, test_goal):
        intention = AgencyIntentionSet(
            intention_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="active",
            arbiter_score=0.92,
            priority_band="urgent",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.agency_intention_set.create(intention)
        await uow.commit()
        
        found = await uow.agency_intention_set.get_by_id(intention.intention_id)
        assert found is not None
        assert found.status == "active"
    
    @pytest.mark.asyncio
    async def test_update_intention(self, uow, test_user, test_goal):
        intention = AgencyIntentionSet(
            intention_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="proposed",
            arbiter_score=0.75,
            priority_band="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.agency_intention_set.create(intention)
        await uow.commit()
        
        created.status = "active"
        created.updated_at = datetime.now(UTC)
        updated = await uow.agency_intention_set.update(created.intention_id, created)
        await uow.commit()
        
        assert updated.status == "active"
    
    @pytest.mark.asyncio
    async def test_delete_intention(self, uow, test_user, test_goal):
        intention = AgencyIntentionSet(
            intention_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="dropped",
            arbiter_score=0.3,
            priority_band="background",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.agency_intention_set.create(intention)
        await uow.commit()
        
        deleted = await uow.agency_intention_set.delete(intention.intention_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_intentions(self, uow, test_user):
        intentions = await uow.agency_intention_set.list(limit=10)
        assert isinstance(intentions, list)
    
    @pytest.mark.asyncio
    async def test_count_intentions(self, uow, test_user):
        count = await uow.agency_intention_set.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_user_intentions(self, uow, test_user, test_goal):
        intention = AgencyIntentionSet(
            intention_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="active",
            arbiter_score=0.88,
            priority_band="normal",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.agency_intention_set.create(intention)
        await uow.commit()
        
        intentions = await uow.agency_intention_set.get_user_intentions(test_user.uuid, status="active")
        assert len(intentions) >= 1
