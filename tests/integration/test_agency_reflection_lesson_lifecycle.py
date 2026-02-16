import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_supersedes_prior_active_lesson_on_same_target(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_lifecycle"

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)

    # Run 1: seed feedback and generate a lesson
    now1 = datetime.now(UTC)
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
                "timestamp": now1,
                "processed": 1,
                "outcome": "failure",
                "execution_time_ms": 123,
                "context_json": None,
                "user_satisfaction": None,
                "free_text": None,
            },
        )
        await local_uow.commit()

    r1 = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)
    assert r1.lessons_generated >= 1

    lessons1 = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    skill_lessons_1 = [l for l in lessons1 if l.lesson_type == "skill_tuning" and l.target_id == skill_id]
    assert skill_lessons_1
    first = skill_lessons_1[0]
    assert first.status == "active"
    assert first.superseded_by is None

    # Run 2: seed another feedback row so we generate another lesson for same target
    now2 = datetime.now(UTC)
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
                "timestamp": now2,
                "processed": 1,
                "outcome": "failure",
                "execution_time_ms": 150,
                "context_json": None,
                "user_satisfaction": None,
                "free_text": None,
            },
        )
        await local_uow.commit()

    r2 = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)
    assert r2.lessons_generated >= 1

    lessons2 = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    skill_lessons_2 = [l for l in lessons2 if l.lesson_type == "skill_tuning" and l.target_id == skill_id]
    assert len(skill_lessons_2) >= 2

    # Find newest active and confirm the old one is superseded
    active = [l for l in skill_lessons_2 if l.status == "active" and l.superseded_by is None]
    superseded = [l for l in skill_lessons_2 if l.status == "superseded" and l.superseded_by is not None]

    assert active
    assert superseded

    # The first lesson should point to the new active lesson
    new_lesson_id = active[0].lesson_id
    assert any(l.lesson_id == first.lesson_id and l.superseded_by == new_lesson_id for l in superseded)
