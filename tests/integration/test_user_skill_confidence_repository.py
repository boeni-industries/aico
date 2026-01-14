"""
Integration tests for UserSkillConfidenceRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.user.relationship_models import UserSkillConfidence
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
    user_id = "skill_confidence_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Skill Confidence Test User",
            nickname="skill_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestUserSkillConfidenceRepository:
    
    @pytest.mark.asyncio
    async def test_create_skill_confidence(self, uow, test_user):
        skill_conf = UserSkillConfidence(
            user_id=test_user.uuid,
            skill_id=f"test_skill_1_{uuid.uuid4().hex[:8]}",
            confidence_level=0.8,
            usage_count=5,
            last_used=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.user_skill_confidence.create(skill_conf)
        await uow.commit()
        
        assert created.user_id == test_user.uuid
        assert created.confidence_level == 0.8
    
    @pytest.mark.asyncio
    async def test_get_skill_confidence_by_id(self, uow, test_user):
        skill_conf = UserSkillConfidence(
            user_id=test_user.uuid,
            skill_id=f"test_skill_2_{uuid.uuid4().hex[:8]}",
            confidence_level=0.9,
            usage_count=10,
            last_used=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.user_skill_confidence.create(skill_conf)
        await uow.commit()
        
        found = await uow.user_skill_confidence.get_by_id(f"{test_user.uuid}:{created.skill_id}")
        assert found is not None
        assert found.confidence_level == 0.9
    
    @pytest.mark.asyncio
    async def test_update_skill_confidence(self, uow, test_user):
        skill_conf = UserSkillConfidence(
            user_id=test_user.uuid,
            skill_id=f"test_skill_3_{uuid.uuid4().hex[:8]}",
            confidence_level=0.5,
            usage_count=1,
            last_used=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.user_skill_confidence.create(skill_conf)
        await uow.commit()
        
        created.confidence_level = 0.7
        created.usage_count = 3
        updated = await uow.user_skill_confidence.update(created)
        await uow.commit()
        
        assert updated.confidence_level == 0.7
        
        found = await uow.user_skill_confidence.get_by_id(f"{test_user.uuid}:{created.skill_id}")
        assert found.usage_count == 3
    
    @pytest.mark.asyncio
    async def test_delete_skill_confidence(self, uow, test_user):
        skill_conf = UserSkillConfidence(
            user_id=test_user.uuid,
            skill_id="test_skill_4",
            confidence_level=0.6,
            usage_count=2,
            last_used=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_skill_confidence.create(skill_conf)
        await uow.commit()
        
        success = await uow.user_skill_confidence.delete(f"{test_user.uuid}:test_skill_4")
        await uow.commit()
        
        assert success is True
        
        found = await uow.user_skill_confidence.get_by_id(f"{test_user.uuid}:test_skill_4")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_skill_confidence(self, uow, test_user):
        for i in range(3):
            skill_conf = UserSkillConfidence(
                user_id=test_user.uuid,
                skill_id=f"list_skill_{i}_{uuid.uuid4().hex[:8]}",
                confidence_level=0.5 + (i * 0.1),
                usage_count=i,
                last_used=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_skill_confidence.create(skill_conf)
        
        await uow.commit()
        
        all_skills = await uow.user_skill_confidence.list(filters={"user_id": test_user.uuid})
        assert len(all_skills) >= 3
    
    @pytest.mark.asyncio
    async def test_count_skill_confidence(self, uow, test_user):
        for i in range(3):
            skill_conf = UserSkillConfidence(
                user_id=test_user.uuid,
                skill_id=f"count_skill_{i}_{uuid.uuid4().hex[:8]}",
                confidence_level=0.5,
                usage_count=i,
                last_used=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_skill_confidence.create(skill_conf)
        
        await uow.commit()
        
        count = await uow.user_skill_confidence.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_skills(self, uow, test_user):
        for i in range(3):
            skill_conf = UserSkillConfidence(
                user_id=test_user.uuid,
                skill_id=f"user_skill_{i}_{uuid.uuid4().hex[:8]}",
                confidence_level=0.5 + (i * 0.1),
                usage_count=i,
                last_used=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_skill_confidence.create(skill_conf)
        
        await uow.commit()
        
        skills = await uow.user_skill_confidence.get_user_skills(test_user.uuid)
        assert len(skills) >= 3
        for skill in skills:
            assert skill.user_id == test_user.uuid
