"""
Integration tests for AMSConsolidationStateRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.consolidation_models import AMSConsolidationState
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


class TestAMSConsolidationStateRepository:
    
    @pytest.mark.asyncio
    async def test_create_state(self, uow):
        state = AMSConsolidationState(
            id=str(uuid.uuid4()),
            state_json={"key": "value", "count": 42},
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.ams_consolidation_state.create(state)
        await uow.commit()
        
        assert created.id == state.id
        assert created.state_json["count"] == 42
    
    @pytest.mark.asyncio
    async def test_get_state_by_id(self, uow):
        state = AMSConsolidationState(
            id=str(uuid.uuid4()),
            state_json={"test": "data"},
            updated_at=datetime.now(UTC),
        )
        
        await uow.ams_consolidation_state.create(state)
        await uow.commit()
        
        found = await uow.ams_consolidation_state.get_by_id(state.id)
        assert found is not None
        assert found.state_json["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_update_state(self, uow):
        state = AMSConsolidationState(
            id=str(uuid.uuid4()),
            state_json={"version": 1},
            updated_at=datetime.now(UTC),
        )
        
        await uow.ams_consolidation_state.create(state)
        await uow.commit()
        
        state.state_json = {"version": 2, "updated": True}
        updated = await uow.ams_consolidation_state.update(state)
        await uow.commit()
        
        assert updated.state_json["version"] == 2
        
        found = await uow.ams_consolidation_state.get_by_id(state.id)
        assert found.state_json["updated"] is True
    
    @pytest.mark.asyncio
    async def test_delete_state(self, uow):
        state = AMSConsolidationState(
            id=str(uuid.uuid4()),
            state_json={"temp": "data"},
            updated_at=datetime.now(UTC),
        )
        
        await uow.ams_consolidation_state.create(state)
        await uow.commit()
        
        success = await uow.ams_consolidation_state.delete(state.id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_consolidation_state.get_by_id(state.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_states(self, uow):
        for i in range(3):
            state = AMSConsolidationState(
                id=str(uuid.uuid4()),
                state_json={"index": i},
                updated_at=datetime.now(UTC),
            )
            await uow.ams_consolidation_state.create(state)
        
        await uow.commit()
        
        all_states = await uow.ams_consolidation_state.list()
        assert len(all_states) >= 3
    
    @pytest.mark.asyncio
    async def test_count_states(self, uow):
        for i in range(3):
            state = AMSConsolidationState(
                id=str(uuid.uuid4()),
                state_json={"count_test": i},
                updated_at=datetime.now(UTC),
            )
            await uow.ams_consolidation_state.create(state)
        
        await uow.commit()
        
        count = await uow.ams_consolidation_state.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_latest(self, uow):
        for i in range(3):
            state = AMSConsolidationState(
                id=str(uuid.uuid4()),
                state_json={"sequence": i},
                updated_at=datetime.now(UTC),
            )
            await uow.ams_consolidation_state.create(state)
            await uow.commit()
        
        latest = await uow.ams_consolidation_state.get_latest()
        assert latest is not None
        assert latest.state_json["sequence"] == 2
