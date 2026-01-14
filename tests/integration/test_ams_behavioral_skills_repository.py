"""
Integration tests for AMSBehavioralSkillsRepository.

Tests AMSBehavioralSkillsRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.models import BehavioralSkill
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


class TestAMSBehavioralSkillsRepository:
    """Test AMSBehavioralSkillsRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_skill(self, uow):
        """Test creating a new behavioral skill."""
        skill = BehavioralSkill(
            skill_id=str(uuid.uuid4()),
            skill_name="Test Skill",
            skill_type="conversation",
            trigger_context="greeting",
            procedure_template="Respond with friendly greeting",
            dimension_vector="[0.1, 0.2, 0.3]",
            supported_languages="en,de",
            status="active",
        )
        
        created = await uow.ams_behavioral_skills.create(skill)
        await uow.commit()
        
        assert created.skill_id == skill.skill_id
        assert created.skill_name == "Test Skill"
        assert created.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_skill_by_id(self, uow):
        """Test retrieving skill by ID."""
        skill = BehavioralSkill(
            skill_id=str(uuid.uuid4()),
            skill_name="Retrieve Test",
            skill_type="task",
            trigger_context="task_request",
            procedure_template="Execute task",
            dimension_vector="[0.5, 0.5, 0.5]",
        )
        
        await uow.ams_behavioral_skills.create(skill)
        await uow.commit()
        
        found = await uow.ams_behavioral_skills.get_by_id(skill.skill_id)
        assert found is not None
        assert found.skill_id == skill.skill_id
        assert found.skill_name == "Retrieve Test"
    
    @pytest.mark.asyncio
    async def test_update_skill(self, uow):
        """Test updating a behavioral skill."""
        skill = BehavioralSkill(
            skill_id=str(uuid.uuid4()),
            skill_name="Original Name",
            skill_type="conversation",
            trigger_context="original_context",
            procedure_template="Original template",
            dimension_vector="[0.1, 0.1, 0.1]",
            status="active",
        )
        
        await uow.ams_behavioral_skills.create(skill)
        await uow.commit()
        
        # Update the skill
        skill.skill_name = "Updated Name"
        skill.procedure_template = "Updated template"
        skill.status = "inactive"
        updated = await uow.ams_behavioral_skills.update(skill)
        await uow.commit()
        
        assert updated.skill_name == "Updated Name"
        
        # Verify update persisted
        found = await uow.ams_behavioral_skills.get_by_id(skill.skill_id)
        assert found.procedure_template == "Updated template"
        assert found.status == "inactive"
    
    @pytest.mark.asyncio
    async def test_delete_skill(self, uow):
        """Test deleting a behavioral skill."""
        skill = BehavioralSkill(
            skill_id=str(uuid.uuid4()),
            skill_name="Delete Me",
            skill_type="test",
            trigger_context="delete_test",
            procedure_template="Will be deleted",
            dimension_vector="[0.0, 0.0, 0.0]",
        )
        
        await uow.ams_behavioral_skills.create(skill)
        await uow.commit()
        
        # Delete the skill
        success = await uow.ams_behavioral_skills.delete(skill.skill_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.ams_behavioral_skills.get_by_id(skill.skill_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_skills(self, uow):
        """Test listing skills with filters."""
        for i in range(3):
            skill = BehavioralSkill(
                skill_id=str(uuid.uuid4()),
                skill_name=f"Skill {i}",
                skill_type="conversation" if i < 2 else "task",
                trigger_context=f"context_{i}",
                procedure_template=f"template_{i}",
                dimension_vector=f"[{i}, {i}, {i}]",
                status="active" if i < 2 else "inactive",
            )
            await uow.ams_behavioral_skills.create(skill)
        
        await uow.commit()
        
        # List all skills
        all_skills = await uow.ams_behavioral_skills.list()
        assert len(all_skills) >= 3
        
        # List by type
        conversation_skills = await uow.ams_behavioral_skills.list(filters={"skill_type": "conversation"})
        assert len(conversation_skills) >= 2
        
        # List by status
        active_skills = await uow.ams_behavioral_skills.list(filters={"status": "active"})
        assert len(active_skills) >= 2
    
    @pytest.mark.asyncio
    async def test_count_skills(self, uow):
        """Test counting skills."""
        for i in range(3):
            skill = BehavioralSkill(
                skill_id=str(uuid.uuid4()),
                skill_name=f"Count Skill {i}",
                skill_type="test",
                trigger_context=f"count_{i}",
                procedure_template=f"count_template_{i}",
                dimension_vector=f"[{i}, {i}, {i}]",
                status="active",
            )
            await uow.ams_behavioral_skills.create(skill)
        
        await uow.commit()
        
        count = await uow.ams_behavioral_skills.count(filters={"status": "active"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_skills(self, uow):
        """Test getting all active skills."""
        for i in range(3):
            skill = BehavioralSkill(
                skill_id=str(uuid.uuid4()),
                skill_name=f"Active Skill {i}",
                skill_type="test",
                trigger_context=f"active_{i}",
                procedure_template=f"active_template_{i}",
                dimension_vector=f"[{i}, {i}, {i}]",
                status="active" if i < 2 else "inactive",
            )
            await uow.ams_behavioral_skills.create(skill)
        
        await uow.commit()
        
        active_skills = await uow.ams_behavioral_skills.get_active_skills()
        assert len(active_skills) >= 2
        for skill in active_skills:
            assert skill.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_skills_by_type(self, uow):
        """Test getting skills by type."""
        for i in range(3):
            skill = BehavioralSkill(
                skill_id=str(uuid.uuid4()),
                skill_name=f"Type Skill {i}",
                skill_type="conversation" if i < 2 else "task",
                trigger_context=f"type_{i}",
                procedure_template=f"type_template_{i}",
                dimension_vector=f"[{i}, {i}, {i}]",
            )
            await uow.ams_behavioral_skills.create(skill)
        
        await uow.commit()
        
        conversation_skills = await uow.ams_behavioral_skills.get_skills_by_type("conversation")
        assert len(conversation_skills) >= 2
        for skill in conversation_skills:
            assert skill.skill_type == "conversation"
