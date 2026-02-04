import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_generates_persona_style_lesson_from_emotion_history(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as local_uow:
        await local_uow._session.execute(
            text(
                """
                INSERT INTO emotion_history
                  (user_id, timestamp, feeling, valence, arousal, intensity, created_at)
                VALUES
                  (:user_id, :timestamp, :feeling, :valence, :arousal, :intensity, :created_at)
                """
            ),
            {
                "user_id": test_user.uuid,
                "timestamp": now.isoformat(),
                "feeling": "test",
                "valence": -0.9,
                "arousal": 0.8,
                "intensity": 0.9,
                "created_at": now.isoformat(),
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1

    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    persona_lessons = [l for l in lessons if l.lesson_type == "persona_style"]
    assert persona_lessons
    assert any(l.proposed_change and l.proposed_change.get("change_type") == "template_update" for l in persona_lessons)
