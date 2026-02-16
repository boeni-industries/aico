"""
Integration tests for EmotionHistoryRepository.

Tests EmotionHistoryRepository with real PostgreSQL database.
"""

import pytest
from datetime import datetime, UTC

from aico.data.emotion.models import EmotionHistory
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


class TestEmotionHistoryRepository:
    """Test EmotionHistoryRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_emotion_history(self, uow):
        """Test creating a new emotion history entry."""
        history = EmotionHistory(
            id=0,
            user_id="test_user",
            timestamp=datetime.now(UTC).isoformat(),
            feeling="happy",
            valence=0.8,
            arousal=0.6,
            intensity=0.7,
        )
        
        created = await uow.emotion_history.create(history)
        await uow.commit()
        
        assert created.id > 0
        assert created.feeling == "happy"
        assert created.valence == 0.8
    
    @pytest.mark.asyncio
    async def test_get_emotion_history_by_id(self, uow):
        """Test retrieving emotion history by ID."""
        history = EmotionHistory(
            id=0,
            user_id="test_user",
            timestamp=datetime.now(UTC).isoformat(),
            feeling="sad",
            valence=0.3,
            arousal=0.4,
            intensity=0.6,
        )
        
        await uow.emotion_history.create(history)
        await uow.commit()
        
        found = await uow.emotion_history.get_by_id(history.id)
        assert found is not None
        assert found.id == history.id
        assert found.feeling == "sad"
    
    @pytest.mark.asyncio
    async def test_update_emotion_history(self, uow):
        """Test updating an emotion history entry."""
        history = EmotionHistory(
            id=0,
            user_id="test_user",
            timestamp=datetime.now(UTC).isoformat(),
            feeling="neutral",
            valence=0.5,
            arousal=0.5,
            intensity=0.5,
        )
        
        await uow.emotion_history.create(history)
        await uow.commit()
        
        # Update the history
        history.feeling = "excited"
        history.valence = 0.9
        history.arousal = 0.8
        updated = await uow.emotion_history.update(history)
        await uow.commit()
        
        assert updated.feeling == "excited"
        
        # Verify update persisted
        found = await uow.emotion_history.get_by_id(history.id)
        assert found.valence == 0.9
        assert found.arousal == 0.8
    
    @pytest.mark.asyncio
    async def test_delete_emotion_history(self, uow):
        """Test deleting an emotion history entry."""
        history = EmotionHistory(
            id=0,
            user_id="test_user",
            timestamp=datetime.now(UTC).isoformat(),
            feeling="angry",
            valence=0.2,
            arousal=0.8,
            intensity=0.7,
        )
        
        await uow.emotion_history.create(history)
        await uow.commit()
        
        # Delete the history
        success = await uow.emotion_history.delete(history.id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.emotion_history.get_by_id(history.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_emotion_history(self, uow):
        """Test listing emotion history with filters."""
        for i in range(3):
            history = EmotionHistory(
                id=0,
                user_id="test_user",
                timestamp=datetime.now(UTC).isoformat(),
                feeling="happy" if i < 2 else "sad",
                valence=0.7 + i * 0.1,
                arousal=0.5 + i * 0.1,
                intensity=0.6 + i * 0.1,
            )
            await uow.emotion_history.create(history)
        
        await uow.commit()
        
        # List all history for user
        all_history = await uow.emotion_history.list(filters={"user_id": "test_user"})
        assert len(all_history) >= 3
        
        # List by feeling
        happy_history = await uow.emotion_history.list(filters={"feeling": "happy"})
        assert len(happy_history) >= 2
    
    @pytest.mark.asyncio
    async def test_count_emotion_history(self, uow):
        """Test counting emotion history entries."""
        for i in range(3):
            history = EmotionHistory(
                id=0,
                user_id="count_user",
                timestamp=datetime.now(UTC).isoformat(),
                feeling="content",
                valence=0.6,
                arousal=0.4,
                intensity=0.5,
            )
            await uow.emotion_history.create(history)
        
        await uow.commit()
        
        count = await uow.emotion_history.count(filters={"user_id": "count_user"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_recent_for_user(self, uow):
        """Test getting recent emotion history for a user."""
        for i in range(3):
            history = EmotionHistory(
                id=0,
                user_id="recent_user",
                timestamp=datetime.now(UTC).isoformat(),
                feeling=f"feeling_{i}",
                valence=0.5 + i * 0.1,
                arousal=0.5,
                intensity=0.5,
            )
            await uow.emotion_history.create(history)
        
        await uow.commit()
        
        recent = await uow.emotion_history.get_recent_for_user("recent_user")
        assert len(recent) >= 3
        for entry in recent:
            assert entry.user_id == "recent_user"
    
    @pytest.mark.asyncio
    async def test_get_by_feeling(self, uow):
        """Test getting emotion history by feeling type."""
        for i in range(3):
            history = EmotionHistory(
                id=0,
                user_id="feeling_user",
                timestamp=datetime.now(UTC).isoformat(),
                feeling="joyful" if i < 2 else "calm",
                valence=0.8,
                arousal=0.6,
                intensity=0.7,
            )
            await uow.emotion_history.create(history)
        
        await uow.commit()
        
        joyful_entries = await uow.emotion_history.get_by_feeling("feeling_user", "joyful")
        assert len(joyful_entries) >= 2
        for entry in joyful_entries:
            assert entry.feeling == "joyful"
