"""
Integration tests for MemoryService.

Tests memory service layer (episodic/semantic orchestration) using actual repositories.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.services.memory_service import MemoryService


@pytest.fixture
async def memory_service(uow):
    """Create MemoryService with UnitOfWork."""
    return MemoryService(uow)


class TestMemoryService:
    """Test suite for MemoryService."""

    @pytest.mark.asyncio
    async def test_create_memory_metadata(self, memory_service, test_user):
        """Test creating memory metadata."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "preference",
            "category": "preferences",
            "confidence": 0.8,
            "is_immutable": False,
            "valid_from": datetime.now(UTC),
            "valid_until": None,
            "content": "Test memory content",
            "entities_json": None,
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "source_message_id": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await memory_service.create_memory_metadata(memory_data)
        
        assert created.fact_id == memory_data["fact_id"]
        assert created.user_id == test_user.uuid

    @pytest.mark.asyncio
    async def test_get_memory_metadata(self, memory_service, test_user):
        """Test retrieving memory metadata."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "preference",
            "category": "preferences",
            "confidence": 0.8,
            "is_immutable": False,
            "valid_from": datetime.now(UTC),
            "valid_until": None,
            "content": "Test memory content",
            "entities_json": None,
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "source_message_id": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await memory_service.create_memory_metadata(memory_data)
        retrieved = await memory_service.get_memory_metadata(created.fact_id)
        
        assert retrieved is not None
        assert retrieved.fact_id == created.fact_id

    @pytest.mark.asyncio
    async def test_list_user_memories(self, memory_service, test_user):
        """Test listing memories for a user."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "preference",
            "category": "preferences",
            "confidence": 0.8,
            "is_immutable": False,
            "valid_from": datetime.now(UTC),
            "valid_until": None,
            "content": "Test memory content",
            "entities_json": None,
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "source_message_id": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await memory_service.create_memory_metadata(memory_data)
        memories = await memory_service.list_user_memories(test_user.uuid)
        
        assert len(memories) >= 1
        assert any(m.fact_id == created.fact_id for m in memories)

    @pytest.mark.asyncio
    async def test_get_episodic_memories(self, memory_service, test_user):
        """Test getting episodic memories."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "temporal",
            "category": "events",
            "confidence": 0.9,
            "is_immutable": False,
            "valid_from": datetime.now(UTC),
            "content": "Episodic memory",
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "memory_type": "episodic",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await memory_service.create_memory_metadata(memory_data)
        
        episodic = await memory_service.get_episodic_memories(test_user.uuid)
        assert len(episodic) >= 1

    @pytest.mark.asyncio
    async def test_get_semantic_memories(self, memory_service, test_user):
        """Test getting semantic memories."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "identity",
            "category": "personal_info",
            "confidence": 0.95,
            "is_immutable": True,
            "valid_from": datetime.now(UTC),
            "content": "Semantic memory",
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "memory_type": "semantic",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await memory_service.create_memory_metadata(memory_data)
        
        semantic = await memory_service.get_semantic_memories(test_user.uuid)
        assert len(semantic) >= 1

    @pytest.mark.asyncio
    async def test_get_memory_count(self, memory_service, test_user):
        """Test counting memories."""
        count = await memory_service.get_memory_count(test_user.uuid)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_get_episodic_memory_count(self, memory_service, test_user):
        """Test counting episodic memories."""
        from datetime import datetime, UTC
        
        memory_data = {
            "fact_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "fact_type": "temporal",
            "category": "events",
            "confidence": 0.9,
            "valid_from": datetime.now(UTC),
            "content": "Test episodic",
            "extraction_method": "manual",
            "source_conversation_id": str(uuid.uuid4()),
            "memory_type": "episodic",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await memory_service.create_memory_metadata(memory_data)
        
        count = await memory_service.get_episodic_memory_count(test_user.uuid)
        assert count >= 1
