import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine

from backend.api.agency.router import get_reflection_summary


@pytest.mark.asyncio
async def test_reflection_summary_endpoint_returns_aggregates(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_summary"
    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as local_uow:
        await local_uow._session.execute(
            text(
                """
                INSERT INTO ams_behavioral_feedback
                  (feedback_id, user_id, message_id, skill_id, reward, reason, timestamp, processed, outcome,
                   execution_time_ms, context_json, user_satisfaction, free_text)
                VALUES
                  (:feedback_id, :user_id, :message_id, :skill_id, :reward, :reason, :timestamp, :processed, :outcome,
                   :execution_time_ms, :context_json, :user_satisfaction, :free_text)
                """
            ),
            {
                "feedback_id": str(uuid.uuid4()),
                "user_id": test_user.uuid,
                "message_id": None,
                "skill_id": skill_id,
                "reward": -1,
                "reason": "test",
                "timestamp": now,
                "processed": 1,
                "outcome": "failure",
                "execution_time_ms": 123,
                "context_json": None,
                "user_satisfaction": None,
                "free_text": None,
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    run = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)
    assert run.run_id

    user_ctx = {"user_uuid": test_user.uuid, "is_technical": False}

    summary = await get_reflection_summary(user=user_ctx, uow=uow, days=7, recent_lessons_limit=10)
    assert summary.user_id == test_user.uuid
    assert summary.reflections >= 1
    assert summary.lessons_total >= 1
    assert summary.avg_confidence is None or isinstance(summary.avg_confidence, float)
    assert isinstance(summary.recent_lessons, list)
    assert len(summary.recent_lessons) >= 1
