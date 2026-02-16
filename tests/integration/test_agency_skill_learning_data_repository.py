"""Integration tests for AgencySkillLearningDataRepository."""

import pytest
import uuid
from aico.data.agency.skill_models import AgencySkillLearningData
from datetime import datetime, UTC

class TestAgencySkillLearningDataRepository:
    
    @pytest.mark.asyncio
    async def test_create_learning_data(self, uow, test_user):
        learning_data = AgencySkillLearningData(
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            dimension_vector="[0.1, 0.2, 0.3, 0.4, 0.5]",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_learning_data.create(learning_data)
        await uow.commit()
        
        assert created.skill_id == learning_data.skill_id
    
    @pytest.mark.asyncio
    async def test_get_learning_data_by_id(self, uow, test_user):
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        learning_data = AgencySkillLearningData(
            skill_id=skill_id,
            dimension_vector="[0.5, 0.6, 0.7, 0.8, 0.9]",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_learning_data.create(learning_data)
        await uow.commit()
        
        found = await uow.agency_skill_learning_data.get_by_id(skill_id)
        assert found is not None
        assert found.skill_id == skill_id
    
    @pytest.mark.asyncio
    async def test_update_learning_data(self, uow, test_user):
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        learning_data = AgencySkillLearningData(
            skill_id=skill_id,
            dimension_vector="[0.1, 0.1, 0.1]",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_learning_data.create(learning_data)
        await uow.commit()
        
        created.dimension_vector = "[0.9, 0.9, 0.9]"
        created.updated_at = datetime.now(UTC).isoformat()
        updated = await uow.agency_skill_learning_data.update(skill_id, created)
        await uow.commit()
        
        assert updated.dimension_vector == "[0.9, 0.9, 0.9]"
    
    @pytest.mark.asyncio
    async def test_delete_learning_data(self, uow, test_user):
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        learning_data = AgencySkillLearningData(
            skill_id=skill_id,
            dimension_vector="[0.0, 0.0, 0.0]",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_learning_data.create(learning_data)
        await uow.commit()
        
        deleted = await uow.agency_skill_learning_data.delete(skill_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_learning_data(self, uow, test_user):
        data_list = await uow.agency_skill_learning_data.list(limit=10)
        assert isinstance(data_list, list)
    
    @pytest.mark.asyncio
    async def test_count_learning_data(self, uow, test_user):
        count = await uow.agency_skill_learning_data.count()
        assert isinstance(count, int)
        assert count >= 0
