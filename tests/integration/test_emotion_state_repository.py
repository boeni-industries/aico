"""
Integration tests for EmotionStateRepository.

Tests EmotionStateRepository with real PostgreSQL database.
"""

import pytest
from datetime import datetime, UTC

from aico.data.emotion.models import EmotionState
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
        # Clean up any existing emotion state before test
        try:
            await uow.emotion_state.delete(1)
            await uow.commit()
        except:
            pass
        yield uow
        # Clean up after test
        try:
            await uow.emotion_state.delete(1)
            await uow.commit()
        except:
            pass


class TestEmotionStateRepository:
    """Test EmotionStateRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_emotion_state(self, uow):
        """Test creating a new emotion state."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="content",
            mood_valence=0.7,
            mood_arousal=0.5,
            intensity=0.6,
            warmth=0.8,
            directness=0.5,
            formality=0.4,
            engagement=0.7,
            closeness=0.6,
            care_focus=0.8,
        )
        
        created = await uow.emotion_state.create(state)
        await uow.commit()
        
        assert created.id == 1
        assert created.subjective_feeling == "content"
        assert created.mood_valence == 0.7
    
    @pytest.mark.asyncio
    async def test_get_emotion_state_by_id(self, uow):
        """Test retrieving emotion state by ID."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="happy",
            mood_valence=0.8,
            mood_arousal=0.6,
            intensity=0.7,
            warmth=0.9,
            directness=0.6,
            formality=0.3,
            engagement=0.8,
            closeness=0.7,
            care_focus=0.9,
        )
        
        await uow.emotion_state.create(state)
        await uow.commit()
        
        found = await uow.emotion_state.get_by_id(1)
        assert found is not None
        assert found.id == 1
        assert found.subjective_feeling == "happy"
    
    @pytest.mark.asyncio
    async def test_update_emotion_state(self, uow):
        """Test updating an emotion state."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="neutral",
            mood_valence=0.5,
            mood_arousal=0.5,
            intensity=0.5,
            warmth=0.5,
            directness=0.5,
            formality=0.5,
            engagement=0.5,
            closeness=0.5,
            care_focus=0.5,
        )
        
        await uow.emotion_state.create(state)
        await uow.commit()
        
        # Update the state
        state.subjective_feeling = "excited"
        state.mood_valence = 0.9
        state.mood_arousal = 0.8
        updated = await uow.emotion_state.update(state)
        await uow.commit()
        
        assert updated.subjective_feeling == "excited"
        
        # Verify update persisted
        found = await uow.emotion_state.get_by_id(1)
        assert found.mood_valence == 0.9
        assert found.mood_arousal == 0.8
    
    @pytest.mark.asyncio
    async def test_delete_emotion_state(self, uow):
        """Test deleting an emotion state."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="sad",
            mood_valence=0.3,
            mood_arousal=0.4,
            intensity=0.6,
            warmth=0.4,
            directness=0.5,
            formality=0.5,
            engagement=0.4,
            closeness=0.5,
            care_focus=0.6,
        )
        
        await uow.emotion_state.create(state)
        await uow.commit()
        
        # Delete the state
        success = await uow.emotion_state.delete(1)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.emotion_state.get_by_id(1)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_emotion_states(self, uow):
        """Test listing emotion states."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="calm",
            mood_valence=0.6,
            mood_arousal=0.3,
            intensity=0.4,
            warmth=0.7,
            directness=0.5,
            formality=0.4,
            engagement=0.6,
            closeness=0.6,
            care_focus=0.7,
        )
        await uow.emotion_state.create(state)
        await uow.commit()
        
        # List all states
        all_states = await uow.emotion_state.list()
        assert len(all_states) >= 1
    
    @pytest.mark.asyncio
    async def test_count_emotion_states(self, uow):
        """Test counting emotion states."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="peaceful",
            mood_valence=0.7,
            mood_arousal=0.2,
            intensity=0.5,
            warmth=0.8,
            directness=0.4,
            formality=0.3,
            engagement=0.6,
            closeness=0.7,
            care_focus=0.8,
        )
        await uow.emotion_state.create(state)
        await uow.commit()
        
        count = await uow.emotion_state.count()
        assert count >= 1
    
    @pytest.mark.asyncio
    async def test_get_current_state(self, uow):
        """Test getting the current emotion state."""
        state = EmotionState(
            id=1,
            user_id="system",
            timestamp=datetime.now(UTC).isoformat(),
            subjective_feeling="focused",
            mood_valence=0.6,
            mood_arousal=0.6,
            intensity=0.7,
            warmth=0.6,
            directness=0.7,
            formality=0.5,
            engagement=0.8,
            closeness=0.6,
            care_focus=0.7,
        )
        await uow.emotion_state.create(state)
        await uow.commit()
        
        current = await uow.emotion_state.get_current_state()
        assert current is not None
        assert current.id == 1
        assert current.subjective_feeling == "focused"
