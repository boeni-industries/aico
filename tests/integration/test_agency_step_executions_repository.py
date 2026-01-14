"""Integration tests for AgencyStepExecutionsRepository."""

import pytest
import uuid
from aico.data.agency.execution_models import AgencyStepExecution
from datetime import datetime, UTC

class TestAgencyStepExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_step_execution(self, uow, test_user, test_plan_execution):
        step_execution = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_001",
            step_order=1,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_step_executions.create(step_execution)
        await uow.commit()
        
        assert created.step_execution_id == step_execution.step_execution_id
        assert created.step_order == 1
    
    @pytest.mark.asyncio
    async def test_get_step_execution_by_id(self, uow, test_user, test_plan_execution):
        step_execution = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_002",
            step_order=2,
            status="running",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_step_executions.create(step_execution)
        await uow.commit()
        
        found = await uow.agency_step_executions.get_by_id(step_execution.step_execution_id)
        assert found is not None
        assert found.status == "running"
    
    @pytest.mark.asyncio
    async def test_update_step_execution(self, uow, test_user, test_plan_execution):
        step_execution = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_003",
            step_order=3,
            status="running",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_step_executions.create(step_execution)
        await uow.commit()
        
        created.status = "completed"
        created.duration_ms = 500
        updated = await uow.agency_step_executions.update(created.step_execution_id, created)
        await uow.commit()
        
        assert updated.status == "completed"
        assert updated.duration_ms == 500
    
    @pytest.mark.asyncio
    async def test_delete_step_execution(self, uow, test_user, test_plan_execution):
        step_execution = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_004",
            step_order=4,
            status="failed",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_step_executions.create(step_execution)
        await uow.commit()
        
        deleted = await uow.agency_step_executions.delete(step_execution.step_execution_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_step_executions(self, uow, test_user):
        step_executions = await uow.agency_step_executions.list(limit=10)
        assert isinstance(step_executions, list)
    
    @pytest.mark.asyncio
    async def test_count_step_executions(self, uow, test_user):
        count = await uow.agency_step_executions.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_execution_steps(self, uow, test_user, test_plan_execution):
        step1 = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_001",
            step_order=1,
            status="completed",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        step2 = AgencyStepExecution(
            step_execution_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            step_id="step_002",
            step_order=2,
            status="running",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_step_executions.create(step1)
        await uow.agency_step_executions.create(step2)
        await uow.commit()
        
        steps = await uow.agency_step_executions.get_execution_steps(test_plan_execution.execution_id)
        assert len(steps) >= 2
        assert steps[0].step_order == 1
