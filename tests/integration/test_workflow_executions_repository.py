"""
Integration tests for WorkflowExecutionsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.workflow.models import WorkflowExecution
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
    user_id = "workflow_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Workflow Test User",
            nickname="workflow_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestWorkflowExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_execution(self, uow, test_user):
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_type="goal_lifecycle",
            user_id=test_user.uuid,
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.workflow_executions.create(execution)
        await uow.commit()
        
        assert created.execution_id == execution.execution_id
        assert created.status == "running"
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id(self, uow, test_user):
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_type="reflection_cycle",
            user_id=test_user.uuid,
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_executions.create(execution)
        await uow.commit()
        
        found = await uow.workflow_executions.get_by_id(execution.execution_id)
        assert found is not None
        assert found.workflow_type == "reflection_cycle"
    
    @pytest.mark.asyncio
    async def test_update_execution(self, uow, test_user):
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_type="curiosity_to_goal",
            user_id=test_user.uuid,
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_executions.create(execution)
        await uow.commit()
        
        execution.status = "completed"
        execution.completed_at = datetime.now(UTC).isoformat()
        updated = await uow.workflow_executions.update(execution)
        await uow.commit()
        
        assert updated.status == "completed"
        
        found = await uow.workflow_executions.get_by_id(execution.execution_id)
        assert found.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, uow, test_user):
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_type="test",
            user_id=test_user.uuid,
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.workflow_executions.create(execution)
        await uow.commit()
        
        success = await uow.workflow_executions.delete(execution.execution_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.workflow_executions.get_by_id(execution.execution_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_executions(self, uow, test_user):
        for i in range(3):
            execution = WorkflowExecution(
                execution_id=str(uuid.uuid4()),
                workflow_type="goal_lifecycle",
                user_id=test_user.uuid,
                status="running" if i < 2 else "completed",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_executions.create(execution)
        
        await uow.commit()
        
        all_executions = await uow.workflow_executions.list(filters={"user_id": test_user.uuid})
        assert len(all_executions) >= 3
        
        running = await uow.workflow_executions.list(filters={"status": "running"})
        assert len(running) >= 2
    
    @pytest.mark.asyncio
    async def test_count_executions(self, uow, test_user):
        for i in range(3):
            execution = WorkflowExecution(
                execution_id=str(uuid.uuid4()),
                workflow_type="count_test",
                user_id=test_user.uuid,
                status="running",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_executions.create(execution)
        
        await uow.commit()
        
        count = await uow.workflow_executions.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_executions(self, uow, test_user):
        for i in range(3):
            execution = WorkflowExecution(
                execution_id=str(uuid.uuid4()),
                workflow_type="active_test",
                user_id=test_user.uuid,
                status="running" if i < 2 else "completed",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.workflow_executions.create(execution)
        
        await uow.commit()
        
        active = await uow.workflow_executions.get_active_executions(test_user.uuid)
        assert len(active) >= 2
        for exec in active:
            assert exec.status == "running"
