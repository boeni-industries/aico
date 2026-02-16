import pytest
from datetime import datetime, UTC

from aico.data.emotion.models import EmotionHistory
from backend.api.emotion.router import get_emotion_history


@pytest.mark.asyncio
async def test_emotion_history_endpoint_returns_spec_ranges(uow):
    history = EmotionHistory(
        id=0,
        user_id="test_user_ranges",
        timestamp=datetime.now(UTC).isoformat(),
        feeling="warm_concern",
        valence=-0.6,
        arousal=0.7,
        intensity=0.8,
    )

    await uow.emotion_history.create(history)
    await uow.commit()

    response = await get_emotion_history(
        user={"uuid": "test_user_ranges"},
        emotion_engine=object(),
        uow=uow,
        limit=10,
        hours=None,
        days=None,
        since=None,
        feeling=None,
    )

    assert response.count >= 1
    assert len(response.history) >= 1

    for item in response.history:
        assert -1.0 <= item.valence <= 1.0
        assert 0.0 <= item.arousal <= 1.0
        assert 0.0 <= item.intensity <= 1.0
