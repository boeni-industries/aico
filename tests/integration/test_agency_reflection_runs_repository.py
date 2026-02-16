"""Integration tests for AgencyReflectionRunsRepository."""

import pytest
import uuid
from aico.data.agency.reflection_models import AgencyReflectionRun
from datetime import datetime, UTC

class TestAgencyReflectionRunsRepository:
    
    @pytest.mark.asyncio
    async def test_create_run(self, uow, test_user):
        run = AgencyReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            run_type="scheduled",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            started_at=datetime.now(UTC),
            status="running",
            created_at=datetime.now(UTC),
        )
        
        created = await uow.agency_reflection_runs.create(run)
        await uow.commit()
        
        assert created.run_id == run.run_id
        assert created.status == "running"
    
    @pytest.mark.asyncio
    async def test_get_run_by_id(self, uow, test_user):
        run = AgencyReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            run_type="triggered",
            trigger_reason="goal_completion",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            started_at=datetime.now(UTC),
            status="completed",
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_reflection_runs.create(run)
        await uow.commit()
        
        found = await uow.agency_reflection_runs.get_by_id(run.run_id)
        assert found is not None
        assert found.trigger_reason == "goal_completion"
    
    @pytest.mark.asyncio
    async def test_update_run(self, uow, test_user):
        run = AgencyReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            run_type="manual",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            started_at=datetime.now(UTC),
            status="running",
            created_at=datetime.now(UTC),
        )
        
        created = await uow.agency_reflection_runs.create(run)
        await uow.commit()
        
        created.status = "completed"
        created.lessons_generated = 3
        created.completed_at = datetime.now(UTC)
        updated = await uow.agency_reflection_runs.update(created.run_id, created)
        await uow.commit()
        
        assert updated.status == "completed"
        assert updated.lessons_generated == 3
    
    @pytest.mark.asyncio
    async def test_delete_run(self, uow, test_user):
        run = AgencyReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            run_type="scheduled",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            started_at=datetime.now(UTC),
            status="failed",
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_reflection_runs.create(run)
        await uow.commit()
        
        deleted = await uow.agency_reflection_runs.delete(run.run_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_runs(self, uow, test_user):
        runs = await uow.agency_reflection_runs.list(limit=10)
        assert isinstance(runs, list)
    
    @pytest.mark.asyncio
    async def test_count_runs(self, uow, test_user):
        count = await uow.agency_reflection_runs.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_user_runs(self, uow, test_user):
        run = AgencyReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            run_type="scheduled",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            started_at=datetime.now(UTC),
            status="completed",
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_reflection_runs.create(run)
        await uow.commit()
        
        runs = await uow.agency_reflection_runs.get_user_runs(test_user.uuid)
        assert len(runs) >= 1
