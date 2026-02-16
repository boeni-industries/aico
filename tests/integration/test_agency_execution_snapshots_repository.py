"""Integration tests for AgencyExecutionSnapshotsRepository."""

import pytest
import uuid
from aico.data.agency.execution_models import AgencyExecutionSnapshot
from datetime import datetime, UTC


class TestAgencyExecutionSnapshotsRepository:
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, uow, test_user, test_plan_execution):
        snapshot = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="checkpoint",
            state_data='{"step": 3, "status": "running"}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_execution_snapshots.create(snapshot)
        await uow.commit()
        
        assert created.snapshot_id == snapshot.snapshot_id
        assert created.snapshot_type == "checkpoint"
    
    @pytest.mark.asyncio
    async def test_get_snapshot_by_id(self, uow, test_user, test_plan_execution):
        snapshot = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="pause",
            state_data='{"paused_at": "step_5"}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_execution_snapshots.create(snapshot)
        await uow.commit()
        
        found = await uow.agency_execution_snapshots.get_by_id(snapshot.snapshot_id)
        assert found is not None
        assert found.snapshot_type == "pause"
    
    @pytest.mark.asyncio
    async def test_update_snapshot(self, uow, test_user, test_plan_execution):
        snapshot = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="checkpoint",
            state_data='{"step": 1}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_execution_snapshots.create(snapshot)
        await uow.commit()
        
        created.state_data = '{"step": 2}'
        updated = await uow.agency_execution_snapshots.update(created.snapshot_id, created)
        await uow.commit()
        
        assert updated.state_data == '{"step": 2}'
    
    @pytest.mark.asyncio
    async def test_delete_snapshot(self, uow, test_user, test_plan_execution):
        snapshot = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="error",
            state_data='{"error": "timeout"}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_execution_snapshots.create(snapshot)
        await uow.commit()
        
        deleted = await uow.agency_execution_snapshots.delete(snapshot.snapshot_id)
        await uow.commit()
        
        assert deleted is True
        found = await uow.agency_execution_snapshots.get_by_id(snapshot.snapshot_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_snapshots(self, uow, test_user):
        snapshots = await uow.agency_execution_snapshots.list(limit=10)
        assert isinstance(snapshots, list)
    
    @pytest.mark.asyncio
    async def test_count_snapshots(self, uow, test_user):
        count = await uow.agency_execution_snapshots.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_by_execution(self, uow, test_user, test_plan_execution):
        snapshot1 = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="checkpoint",
            state_data='{"step": 1}',
            created_at=datetime.now(UTC).isoformat(),
        )
        snapshot2 = AgencyExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=test_plan_execution.execution_id,
            snapshot_type="checkpoint",
            state_data='{"step": 2}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_execution_snapshots.create(snapshot1)
        await uow.agency_execution_snapshots.create(snapshot2)
        await uow.commit()
        
        snapshots = await uow.agency_execution_snapshots.get_by_execution(test_plan_execution.execution_id)
        assert len(snapshots) >= 2
