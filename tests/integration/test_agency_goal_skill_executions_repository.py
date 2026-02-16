"""Integration tests for AgencyGoalSkillExecutionsRepository."""

import pytest
import uuid
from aico.data.agency.goal_models import AgencyGoalSkillExecution
from datetime import datetime, UTC


class TestAgencyGoalSkillExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_execution(self, uow, test_user, test_goal):
        execution = AgencyGoalSkillExecution(
            link_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            skill_id=str(uuid.uuid4()),
            execution_id=str(uuid.uuid4()),
            execution_order=1,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_goal_skill_executions.create(execution)
        await uow.commit()
        
        assert created.link_id == execution.link_id
        assert created.execution_order == 1
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id(self, uow, test_user, test_goal):
        execution = AgencyGoalSkillExecution(
            link_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            skill_id=str(uuid.uuid4()),
            execution_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_skill_executions.create(execution)
        await uow.commit()
        
        found = await uow.agency_goal_skill_executions.get_by_id(execution.link_id)
        assert found is not None
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, uow, test_user, test_goal):
        execution = AgencyGoalSkillExecution(
            link_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            skill_id=str(uuid.uuid4()),
            execution_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_goal_skill_executions.create(execution)
        await uow.commit()
        
        deleted = await uow.agency_goal_skill_executions.delete(execution.link_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_executions(self, uow, test_user):
        executions = await uow.agency_goal_skill_executions.list(limit=10)
        assert isinstance(executions, list)
    
    @pytest.mark.asyncio
    async def test_count_executions(self, uow, test_user):
        count = await uow.agency_goal_skill_executions.count()
        assert isinstance(count, int)
        assert count >= 0
