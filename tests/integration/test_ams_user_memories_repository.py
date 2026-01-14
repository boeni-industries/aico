"""
Integration tests for AMSUserMemoriesRepository.

Tests AMSUserMemoriesRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.models import AMSUserMemory
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
    """Create a test user for memory tests."""
    # Create users if they don't exist
    for user_id in ["test_user", "count_user", "favorite_user", "category_user"]:
        existing = await uow.users.get_by_id(user_id)
        if not existing:
            user = UserProfile(
                uuid=user_id,
                full_name=f"{user_id.replace('_', ' ').title()}",
                nickname=user_id,
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
    
    await uow.commit()
    
    # Return the main test user
    return await uow.users.get_by_id("test_user")


class TestAMSUserMemoriesRepository:
    """Test AMSUserMemoriesRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_user_memory(self, uow, test_user):
        """Test creating a new user memory."""
        memory = AMSUserMemory(
            fact_id=str(uuid.uuid4()),
            user_id="test_user",
            fact_type="preference",
            category="personal_info",
            confidence=0.9,
            is_immutable=False,
            valid_from=datetime.now(UTC),
            content="User prefers morning conversations",
            extraction_method="automatic",
            source_conversation_id=str(uuid.uuid4()),
        )
        
        created = await uow.ams_user_memories.create(memory)
        await uow.commit()
        
        assert created.fact_id == memory.fact_id
        assert created.content == "User prefers morning conversations"
        assert created.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_get_user_memory_by_id(self, uow, test_user):
        """Test retrieving user memory by ID."""
        memory = AMSUserMemory(
            fact_id=str(uuid.uuid4()),
            user_id="test_user",
            fact_type="identity",
            category="personal_info",
            confidence=0.95,
            is_immutable=True,
            valid_from=datetime.now(UTC),
            content="User's name is Alice",
            extraction_method="user_provided",
            source_conversation_id=str(uuid.uuid4()),
        )
        
        await uow.ams_user_memories.create(memory)
        await uow.commit()
        
        found = await uow.ams_user_memories.get_by_id(memory.fact_id)
        assert found is not None
        assert found.fact_id == memory.fact_id
        assert found.content == "User's name is Alice"
    
    @pytest.mark.asyncio
    async def test_update_user_memory(self, uow, test_user):
        """Test updating a user memory."""
        memory = AMSUserMemory(
            fact_id=str(uuid.uuid4()),
            user_id="test_user",
            fact_type="preference",
            category="preferences",
            confidence=0.7,
            is_immutable=False,
            valid_from=datetime.now(UTC),
            content="User likes coffee",
            extraction_method="automatic",
            source_conversation_id=str(uuid.uuid4()),
        )
        
        await uow.ams_user_memories.create(memory)
        await uow.commit()
        
        # Update the memory
        memory.confidence = 0.95
        memory.user_note = "Confirmed by user"
        memory.is_favorite = True
        updated = await uow.ams_user_memories.update(memory)
        await uow.commit()
        
        assert updated.confidence == 0.95
        
        # Verify update persisted
        found = await uow.ams_user_memories.get_by_id(memory.fact_id)
        assert found.user_note == "Confirmed by user"
        assert found.is_favorite is True
    
    @pytest.mark.asyncio
    async def test_delete_user_memory(self, uow, test_user):
        """Test deleting a user memory."""
        memory = AMSUserMemory(
            fact_id=str(uuid.uuid4()),
            user_id="test_user",
            fact_type="temporal",
            category="relationships",
            confidence=0.8,
            is_immutable=False,
            valid_from=datetime.now(UTC),
            content="User met friend yesterday",
            extraction_method="automatic",
            source_conversation_id=str(uuid.uuid4()),
        )
        
        await uow.ams_user_memories.create(memory)
        await uow.commit()
        
        # Delete the memory
        success = await uow.ams_user_memories.delete(memory.fact_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.ams_user_memories.get_by_id(memory.fact_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_user_memories(self, uow, test_user):
        """Test listing user memories with filters."""
        for i in range(3):
            memory = AMSUserMemory(
                fact_id=str(uuid.uuid4()),
                user_id="test_user",
                fact_type="preference",
                category="personal_info" if i < 2 else "preferences",
                confidence=0.8 + i * 0.05,
                is_immutable=False,
                valid_from=datetime.now(UTC),
                content=f"Memory {i}",
                extraction_method="automatic",
                source_conversation_id=str(uuid.uuid4()),
            )
            await uow.ams_user_memories.create(memory)
        
        await uow.commit()
        
        # List all memories for user
        all_memories = await uow.ams_user_memories.list(filters={"user_id": "test_user"})
        assert len(all_memories) >= 3
        
        # List by category
        personal_memories = await uow.ams_user_memories.list(filters={"category": "personal_info"})
        assert len(personal_memories) >= 2
    
    @pytest.mark.asyncio
    async def test_count_user_memories(self, uow, test_user):
        """Test counting user memories."""
        for i in range(3):
            memory = AMSUserMemory(
                fact_id=str(uuid.uuid4()),
                user_id="count_user",
                fact_type="preference",
                category="preferences",
                confidence=0.8,
                is_immutable=False,
                valid_from=datetime.now(UTC),
                content=f"Count memory {i}",
                extraction_method="automatic",
                source_conversation_id=str(uuid.uuid4()),
            )
            await uow.ams_user_memories.create(memory)
        
        await uow.commit()
        
        count = await uow.ams_user_memories.count(filters={"user_id": "count_user"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_favorites_for_user(self, uow, test_user):
        """Test getting favorite memories for user."""
        for i in range(3):
            memory = AMSUserMemory(
                fact_id=str(uuid.uuid4()),
                user_id="favorite_user",
                fact_type="preference",
                category="personal_info",
                confidence=0.9,
                is_immutable=False,
                valid_from=datetime.now(UTC),
                content=f"Favorite memory {i}",
                extraction_method="automatic",
                source_conversation_id=str(uuid.uuid4()),
                is_favorite=i < 2,
            )
            await uow.ams_user_memories.create(memory)
        
        await uow.commit()
        
        favorites = await uow.ams_user_memories.get_favorites_for_user("favorite_user")
        assert len(favorites) >= 2
        for memory in favorites:
            assert memory.is_favorite is True
    
    @pytest.mark.asyncio
    async def test_get_by_category(self, uow, test_user):
        """Test getting memories by category for user."""
        for i in range(3):
            memory = AMSUserMemory(
                fact_id=str(uuid.uuid4()),
                user_id="category_user",
                fact_type="preference",
                category="preferences" if i < 2 else "relationships",
                confidence=0.9 - i * 0.1,
                is_immutable=False,
                valid_from=datetime.now(UTC),
                content=f"Category memory {i}",
                extraction_method="automatic",
                source_conversation_id=str(uuid.uuid4()),
            )
            await uow.ams_user_memories.create(memory)
        
        await uow.commit()
        
        preferences = await uow.ams_user_memories.get_by_category("category_user", "preferences")
        assert len(preferences) >= 2
        for memory in preferences:
            assert memory.category == "preferences"
