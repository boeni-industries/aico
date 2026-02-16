"""Integration tests for AgencyGoalOutcomesRepository."""

import pytest
import uuid
from aico.data.agency.goal_models import AgencyGoalOutcome
from datetime import datetime, UTC


class TestAgencyGoalOutcomesRepository:
    
    @pytest.mark.asyncio
    async def test_create_outcome(self, uow, test_user, test_goal):
        outcome = AgencyGoalOutcome(
            outcome_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            outcome="completed",
            success=1,
            reward=0.95,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_goal_outcomes.create(outcome)
        await uow.commit()
        
        assert created.outcome_id == outcome.outcome_id
        assert created.outcome == "completed"
        assert created.success == 1
    
    @pytest.mark.asyncio
    async def test_get_outcome_by_id(self, uow, test_user, test_goal):
        outcome = AgencyGoalOutcome(
            outcome_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            outcome="failed",
            success=0,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_outcomes.create(outcome)
        await uow.commit()
        
        found = await uow.agency_goal_outcomes.get_by_id(outcome.outcome_id)
        assert found is not None
        assert found.outcome == "failed"
    
    @pytest.mark.asyncio
    async def test_update_outcome(self, uow, test_user, test_goal):
        outcome = AgencyGoalOutcome(
            outcome_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            outcome="completed",
            success=1,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_goal_outcomes.create(outcome)
        await uow.commit()
        
        created.user_satisfaction = 0.9
        updated = await uow.agency_goal_outcomes.update(created.outcome_id, created)
        await uow.commit()
        
        assert updated.user_satisfaction == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_outcome(self, uow, test_user, test_goal):
        outcome = AgencyGoalOutcome(
            outcome_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            outcome="abandoned",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_outcomes.create(outcome)
        await uow.commit()
        
        deleted = await uow.agency_goal_outcomes.delete(outcome.outcome_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_outcomes(self, uow, test_user):
        outcomes = await uow.agency_goal_outcomes.list(limit=10)
        assert isinstance(outcomes, list)
    
    @pytest.mark.asyncio
    async def test_count_outcomes(self, uow, test_user):
        count = await uow.agency_goal_outcomes.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_goal_outcomes(self, uow, test_user, test_goal):
        outcome1 = AgencyGoalOutcome(
            outcome_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            outcome="completed",
            success=1,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_outcomes.create(outcome1)
        await uow.commit()
        
        outcomes = await uow.agency_goal_outcomes.get_goal_outcomes(test_goal.goal_id)
        assert len(outcomes) >= 1
