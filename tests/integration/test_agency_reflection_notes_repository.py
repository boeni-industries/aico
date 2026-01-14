"""
Integration tests for AgencyReflectionNotesRepository.

Tests AgencyReflectionNotesRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.models import AgencyReflectionNote, Goal
from aico.data.user.models import UserProfile
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


@pytest.fixture
async def test_user(uow):
    """Create a test user for reflection note tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Reflection Note Test User",
        nickname="reflection_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


@pytest.fixture
async def test_goal(uow, test_user):
    """Create a test goal for reflection note tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user",
        title="Test Goal for Reflections",
        status="active",
        priority="high",
        goal_type="learning",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestAgencyReflectionNotesRepository:
    """Test AgencyReflectionNotesRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_note(self, uow, test_user, test_goal):
        """Test creating a new reflection note."""
        note = AgencyReflectionNote(
            note_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            related_goal_id=test_goal.goal_id,
            title="My First Reflection",
            content="Today I learned something important about my goal.",
            tags_json={"tags": ["learning", "progress"]},
        )
        
        created = await uow.agency_reflection_notes.create(note)
        await uow.commit()
        
        assert created.note_id == note.note_id
        assert created.title == "My First Reflection"
        assert created.related_goal_id == test_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_note_by_id(self, uow, test_user):
        """Test retrieving note by ID."""
        note = AgencyReflectionNote(
            note_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Test Note",
            content="This is a test reflection note.",
        )
        
        await uow.agency_reflection_notes.create(note)
        await uow.commit()
        
        found = await uow.agency_reflection_notes.get_by_id(note.note_id)
        assert found is not None
        assert found.note_id == note.note_id
        assert found.title == "Test Note"
    
    @pytest.mark.asyncio
    async def test_update_note(self, uow, test_user):
        """Test updating a reflection note."""
        note = AgencyReflectionNote(
            note_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Original Title",
            content="Original content",
            tags_json={"tags": ["draft"]},
        )
        
        await uow.agency_reflection_notes.create(note)
        await uow.commit()
        
        # Update the note
        note.title = "Updated Title"
        note.content = "Updated content with more details"
        note.tags_json = {"tags": ["final", "reviewed"]}
        updated = await uow.agency_reflection_notes.update(note)
        await uow.commit()
        
        assert updated.title == "Updated Title"
        
        # Verify update persisted
        found = await uow.agency_reflection_notes.get_by_id(note.note_id)
        assert found.content == "Updated content with more details"
        assert found.tags_json["tags"] == ["final", "reviewed"]
    
    @pytest.mark.asyncio
    async def test_delete_note(self, uow, test_user):
        """Test deleting a reflection note."""
        note = AgencyReflectionNote(
            note_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Delete Me",
            content="This note will be deleted",
        )
        
        await uow.agency_reflection_notes.create(note)
        await uow.commit()
        
        # Delete the note
        success = await uow.agency_reflection_notes.delete(note.note_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.agency_reflection_notes.get_by_id(note.note_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_notes(self, uow, test_user, test_goal):
        """Test listing notes with filters."""
        for i in range(3):
            note = AgencyReflectionNote(
                note_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                related_goal_id=test_goal.goal_id if i < 2 else None,
                title=f"Note {i}",
                content=f"Content {i}",
            )
            await uow.agency_reflection_notes.create(note)
        
        await uow.commit()
        
        # List all notes for user
        all_notes = await uow.agency_reflection_notes.list(filters={"user_id": test_user.uuid})
        assert len(all_notes) >= 3
        
        # List by goal
        goal_notes = await uow.agency_reflection_notes.list(filters={"related_goal_id": test_goal.goal_id})
        assert len(goal_notes) >= 2
    
    @pytest.mark.asyncio
    async def test_count_notes(self, uow, test_user):
        """Test counting notes."""
        for i in range(3):
            note = AgencyReflectionNote(
                note_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                title=f"Count Note {i}",
                content=f"Count content {i}",
            )
            await uow.agency_reflection_notes.create(note)
        
        await uow.commit()
        
        count = await uow.agency_reflection_notes.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_notes_for_goal(self, uow, test_user, test_goal):
        """Test getting notes for a specific goal."""
        for i in range(3):
            note = AgencyReflectionNote(
                note_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                related_goal_id=test_goal.goal_id,
                title=f"Goal Note {i}",
                content=f"Reflection on goal progress {i}",
            )
            await uow.agency_reflection_notes.create(note)
        
        await uow.commit()
        
        goal_notes = await uow.agency_reflection_notes.get_notes_for_goal(test_goal.goal_id)
        assert len(goal_notes) >= 3
        for note in goal_notes:
            assert note.related_goal_id == test_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_recent_notes_for_user(self, uow, test_user):
        """Test getting recent notes for a user."""
        for i in range(3):
            note = AgencyReflectionNote(
                note_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                title=f"Recent Note {i}",
                content=f"Recent reflection {i}",
            )
            await uow.agency_reflection_notes.create(note)
        
        await uow.commit()
        
        recent_notes = await uow.agency_reflection_notes.get_recent_notes_for_user(test_user.uuid)
        assert len(recent_notes) >= 3
        for note in recent_notes:
            assert note.user_id == test_user.uuid
