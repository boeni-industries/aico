"""Integration tests for AgencySkillGapsRepository."""

import pytest
import uuid
from aico.data.agency.skill_models import AgencySkillGap
from datetime import datetime, UTC

class TestAgencySkillGapsRepository:
    
    @pytest.mark.asyncio
    async def test_create_gap(self, uow, test_user):
        gap = AgencySkillGap(
            gap_id=str(uuid.uuid4()),
            step_description="Analyze user sentiment from conversation",
            first_seen_at=datetime.now(UTC).isoformat(),
            last_seen_at=datetime.now(UTC).isoformat(),
            frequency_count=1,
            priority_score=0.75,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_gaps.create(gap)
        await uow.commit()
        
        assert created.gap_id == gap.gap_id
        assert created.frequency_count == 1
    
    @pytest.mark.asyncio
    async def test_get_gap_by_id(self, uow, test_user):
        gap = AgencySkillGap(
            gap_id=str(uuid.uuid4()),
            step_description="Generate creative content suggestions",
            llm_suggested_skills='["content_generation", "creativity"]',
            first_seen_at=datetime.now(UTC).isoformat(),
            last_seen_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_gaps.create(gap)
        await uow.commit()
        
        found = await uow.agency_skill_gaps.get_by_id(gap.gap_id)
        assert found is not None
    
    @pytest.mark.asyncio
    async def test_update_gap(self, uow, test_user):
        gap = AgencySkillGap(
            gap_id=str(uuid.uuid4()),
            step_description="Parse complex user queries",
            first_seen_at=datetime.now(UTC).isoformat(),
            last_seen_at=datetime.now(UTC).isoformat(),
            frequency_count=1,
            priority_score=0.5,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_skill_gaps.create(gap)
        await uow.commit()
        
        created.frequency_count = 5
        created.priority_score = 0.9
        updated = await uow.agency_skill_gaps.update(created.gap_id, created)
        await uow.commit()
        
        assert updated.frequency_count == 5
        assert updated.priority_score == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_gap(self, uow, test_user):
        gap = AgencySkillGap(
            gap_id=str(uuid.uuid4()),
            step_description="Obsolete skill requirement",
            first_seen_at=datetime.now(UTC).isoformat(),
            last_seen_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_gaps.create(gap)
        await uow.commit()
        
        deleted = await uow.agency_skill_gaps.delete(gap.gap_id)
        await uow.commit()
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_gaps(self, uow, test_user):
        gaps = await uow.agency_skill_gaps.list(limit=10)
        assert isinstance(gaps, list)
    
    @pytest.mark.asyncio
    async def test_count_gaps(self, uow, test_user):
        count = await uow.agency_skill_gaps.count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_get_top_gaps(self, uow, test_user):
        gap1 = AgencySkillGap(
            gap_id=str(uuid.uuid4()),
            step_description="High priority gap",
            first_seen_at=datetime.now(UTC).isoformat(),
            last_seen_at=datetime.now(UTC).isoformat(),
            priority_score=0.95,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_skill_gaps.create(gap1)
        await uow.commit()
        
        top_gaps = await uow.agency_skill_gaps.get_top_gaps(limit=5)
        assert isinstance(top_gaps, list)
