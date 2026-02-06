import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_observe_only_creates_lessons_but_does_not_apply(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_observe"
    now = datetime.now(UTC)

    # Insert behavioral feedback so a lesson is generated
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
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied == 0

    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    assert any(l.target_id == skill_id for l in lessons)

    # No application should have occurred
    skill_learning = await uow.agency_skill_learning_data.get_by_id(skill_id)
    assert skill_learning is None


@pytest.mark.asyncio
async def test_reflection_allow_amend_applies_skill_tuning_and_marks_applied(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "allow_amend", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_enforce"
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
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied >= 1

    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    relevant = [l for l in lessons if l.target_id == skill_id]
    assert relevant
    assert any(l.applied_at is not None and l.applied_by for l in relevant)

    skill_learning = await uow.agency_skill_learning_data.get_by_id(skill_id)
    assert skill_learning is not None
