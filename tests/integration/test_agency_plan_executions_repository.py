"""Integration tests for AgencyPlanExecutionsRepository."""

import pytest
import uuid
from aico.data.agency.execution_models import AgencyPlanExecution
from datetime import datetime, UTC


class TestAgencyPlanExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_execution(self, uow, test_user, test_goal, test_plan):
        execution = AgencyPlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=test_plan.plan_id,
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="pending",
            steps_total=5,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_plan_executions.create(execution)
        await uow.commit()
        
        assert created.execution_id == execution.execution_id
        assert created.steps_total == 5
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id(self, uow, test_user, test_goal, test_plan):
        execution = AgencyPlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=test_plan.plan_id,
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="running",
            steps_total=3,
            steps_completed=1,
            progress_percentage=33.3,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_plan_executions.create(execution)
        await uow.commit()
        
        found = await uow.agency_plan_executions.get_by_id(execution.execution_id)
        assert found is not None
        assert found.status == "running"
    
    @pytest.mark.asyncio
    async def test_update_execution(self, uow, test_user, test_goal, test_plan):
        execution = AgencyPlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=test_plan.plan_id,
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="running",
            steps_total=5,
            steps_completed=2,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_plan_executions.create(execution)
        await uow.commit()
        
        created.steps_completed = 3
        created.progress_percentage = 60.0
        updated = await uow.agency_plan_executions.update(created.execution_id, created)
        await uow.commit()
        
        assert updated.steps_completed == 3
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, uow, test_user, test_goal, test_plan):
        execution = AgencyPlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=test_plan.plan_id,
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="cancelled",
            steps_total=5,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_plan_executions.create(execution)
        await uow.commit()
        
        deleted = await uow.agency_plan_executions.delete(execution.execution_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_executions(self, uow, test_user):
        executions = await uow.agency_plan_executions.list(limit=10)
        assert isinstance(executions, list)
    
    @pytest.mark.asyncio
    async def test_count_executions(self, uow, test_user):
        count = await uow.agency_plan_executions.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_user_executions(self, uow, test_user, test_goal, test_plan):
        execution = AgencyPlanExecution(
            execution_id=str(uuid.uuid4()),
            plan_id=test_plan.plan_id,
            goal_id=test_goal.goal_id,
            user_id=test_user.uuid,
            status="completed",
            steps_total=5,
            steps_completed=5,
            progress_percentage=100.0,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_plan_executions.create(execution)
        await uow.commit()
        
        executions = await uow.agency_plan_executions.get_user_executions(test_user.uuid)
        assert len(executions) >= 1
