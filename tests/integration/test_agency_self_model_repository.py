"""Integration tests for AgencySelfModelRepository."""

import pytest
import uuid
from aico.data.agency.reflection_models import AgencySelfModel
from datetime import datetime, UTC

class TestAgencySelfModelRepository:
    
    @pytest.mark.asyncio
    async def test_create_model(self, uow, test_user):
        model = AgencySelfModel(
            model_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            entity_type="skill",
            entity_id="planning_skill_001",
            performance_summary='{"success_rate": 0.85, "avg_duration": 120}',
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=50,
            confidence=0.9,
            created_at=datetime.now(UTC),
        )
        
        created = await uow.agency_self_model.create(model)
        await uow.commit()
        
        assert created.model_id == model.model_id
        assert created.entity_type == "skill"
    
    @pytest.mark.asyncio
    async def test_get_model_by_id(self, uow, test_user):
        model = AgencySelfModel(
            model_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            entity_type="goal_type",
            entity_id="project",
            performance_summary='{"completion_rate": 0.75}',
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=20,
            confidence=0.8,
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_self_model.create(model)
        await uow.commit()
        
        found = await uow.agency_self_model.get_by_id(model.model_id)
        assert found is not None
        assert found.entity_type == "goal_type"
    
    @pytest.mark.asyncio
    async def test_update_model(self, uow, test_user):
        model = AgencySelfModel(
            model_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            entity_type="skill",
            entity_id="analysis_skill_002",
            performance_summary='{"success_rate": 0.70}',
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=30,
            confidence=0.75,
            created_at=datetime.now(UTC),
        )
        
        created = await uow.agency_self_model.create(model)
        await uow.commit()
        
        created.performance_summary = '{"success_rate": 0.80}'
        created.confidence = 0.85
        updated = await uow.agency_self_model.update(created.model_id, created)
        await uow.commit()
        
        assert updated.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_delete_model(self, uow, test_user):
        model = AgencySelfModel(
            model_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            entity_type="interaction_pattern",
            entity_id="morning_routine",
            performance_summary='{"consistency": 0.9}',
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=100,
            confidence=0.95,
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_self_model.create(model)
        await uow.commit()
        
        deleted = await uow.agency_self_model.delete(model.model_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_models(self, uow, test_user):
        models = await uow.agency_self_model.list(limit=10)
        assert isinstance(models, list)
    
    @pytest.mark.asyncio
    async def test_count_models(self, uow, test_user):
        count = await uow.agency_self_model.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_user_models(self, uow, test_user):
        model = AgencySelfModel(
            model_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            entity_type="skill",
            entity_id="communication_skill",
            performance_summary='{"effectiveness": 0.88}',
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=40,
            confidence=0.85,
            created_at=datetime.now(UTC),
        )
        
        await uow.agency_self_model.create(model)
        await uow.commit()
        
        models = await uow.agency_self_model.get_user_models(test_user.uuid, entity_type="skill")
        assert len(models) >= 1
