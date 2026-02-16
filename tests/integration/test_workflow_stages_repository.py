"""
Integration tests for WorkflowStagesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.workflow.models import WorkflowStage, WorkflowExecution
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
    user_id = "workflow_stage_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Workflow Stage Test User",
            nickname="stage_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


@pytest.fixture
async def test_execution(uow, test_user):
    execution_id = str(uuid.uuid4())
    execution = WorkflowExecution(
        execution_id=execution_id,
        workflow_type="test_workflow",
        user_id=test_user.uuid,
        status="running",
        started_at=datetime.now(UTC).isoformat(),
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
    await uow.workflow_executions.create(execution)
    await uow.commit()
    return execution


class TestWorkflowStagesRepository:
    
    @pytest.mark.asyncio
    async def test_create_stage(self, uow, test_execution):
        stage = WorkflowStage(
            stage_id=str(uuid.uuid4()),
            execution_id=test_execution.execution_id,
            stage_name="Stage 1",
            stage_order=1,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.workflow_stages.create(stage)
        await uow.commit()
        
        assert created.stage_id == stage.stage_id
        assert created.stage_name == "Stage 1"
    
    @pytest.mark.asyncio
    async def test_get_stage_by_id(self, uow, test_execution):
        stage = WorkflowStage(
            stage_id=str(uuid.uuid4()),
            execution_id=test_execution.execution_id,
            stage_name="Stage 2",
            stage_order=2,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_stages.create(stage)
        await uow.commit()
        
        found = await uow.workflow_stages.get_by_id(stage.stage_id)
        assert found is not None
        assert found.stage_name == "Stage 2"
    
    @pytest.mark.asyncio
    async def test_update_stage(self, uow, test_execution):
        stage = WorkflowStage(
            stage_id=str(uuid.uuid4()),
            execution_id=test_execution.execution_id,
            stage_name="Stage 3",
            stage_order=3,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_stages.create(stage)
        await uow.commit()
        
        stage.status = "completed"
        stage.completed_at = datetime.now(UTC).isoformat()
        updated = await uow.workflow_stages.update(stage)
        await uow.commit()
        
        assert updated.status == "completed"
        
        found = await uow.workflow_stages.get_by_id(stage.stage_id)
        assert found.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_stage(self, uow, test_execution):
        stage = WorkflowStage(
            stage_id=str(uuid.uuid4()),
            execution_id=test_execution.execution_id,
            stage_name="Stage 4",
            stage_order=4,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_stages.create(stage)
        await uow.commit()
        
        success = await uow.workflow_stages.delete(stage.stage_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.workflow_stages.get_by_id(stage.stage_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_stages(self, uow, test_execution):
        for i in range(3):
            stage = WorkflowStage(
                stage_id=str(uuid.uuid4()),
                execution_id=test_execution.execution_id,
                stage_name=f"Stage {i}",
                stage_order=i,
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_stages.create(stage)
        
        await uow.commit()
        
        all_stages = await uow.workflow_stages.list(filters={"execution_id": test_execution.execution_id})
        assert len(all_stages) >= 3
    
    @pytest.mark.asyncio
    async def test_count_stages(self, uow, test_execution):
        for i in range(3):
            stage = WorkflowStage(
                stage_id=str(uuid.uuid4()),
                execution_id=test_execution.execution_id,
                stage_name=f"Count Stage {i}",
                stage_order=i,
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_stages.create(stage)
        
        await uow.commit()
        
        count = await uow.workflow_stages.count(filters={"execution_id": test_execution.execution_id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_execution_stages(self, uow, test_execution):
        for i in range(3):
            stage = WorkflowStage(
                stage_id=str(uuid.uuid4()),
                execution_id=test_execution.execution_id,
                stage_name=f"Exec Stage {i}",
                stage_order=i,
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_stages.create(stage)
        
        await uow.commit()
        
        stages = await uow.workflow_stages.get_execution_stages(test_execution.execution_id)
        assert len(stages) >= 3
        assert stages[0].stage_order < stages[1].stage_order
