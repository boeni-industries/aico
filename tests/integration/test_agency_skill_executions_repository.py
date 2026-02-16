"""Integration tests for AgencySkillExecutionsRepository."""

import pytest
import uuid
from aico.data.agency.skill_models import AgencySkillExecution
from datetime import datetime, UTC

class TestAgencySkillExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_execution(self, uow, test_user):
        execution = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id="planning_skill_001",
            user_id=test_user.uuid,
            outcome="success",
            execution_time_ms=250,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_executions.create(execution)
        await uow.commit()
        
        assert created.execution_id == execution.execution_id
        assert created.outcome == "success"
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id(self, uow, test_user):
        execution = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id="analysis_skill_002",
            user_id=test_user.uuid,
            outcome="failure",
            error_message="Timeout exceeded",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_executions.create(execution)
        await uow.commit()
        
        found = await uow.agency_skill_executions.get_by_id(execution.execution_id)
        assert found is not None
        assert found.outcome == "failure"
    
    @pytest.mark.asyncio
    async def test_update_execution(self, uow, test_user):
        execution = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id="communication_skill",
            user_id=test_user.uuid,
            outcome="success",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_executions.create(execution)
        await uow.commit()
        
        created.execution_time_ms = 180
        updated = await uow.agency_skill_executions.update(created.execution_id, created)
        await uow.commit()
        
        assert updated.execution_time_ms == 180
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, uow, test_user):
        execution = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id="test_skill",
            user_id=test_user.uuid,
            outcome="success",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_executions.create(execution)
        await uow.commit()
        
        deleted = await uow.agency_skill_executions.delete(execution.execution_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_executions(self, uow, test_user):
        executions = await uow.agency_skill_executions.list(limit=10)
        assert isinstance(executions, list)
    
    @pytest.mark.asyncio
    async def test_count_executions(self, uow, test_user):
        count = await uow.agency_skill_executions.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_skill_executions(self, uow, test_user):
        skill_id = "planning_skill_003"
        execution = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id=skill_id,
            user_id=test_user.uuid,
            outcome="success",
            execution_time_ms=200,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_executions.create(execution)
        await uow.commit()
        
        executions = await uow.agency_skill_executions.get_skill_executions(skill_id)
        assert len(executions) >= 1
