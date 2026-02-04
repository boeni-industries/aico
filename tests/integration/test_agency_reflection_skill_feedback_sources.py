import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork
from aico.data.agency.skill_models import AgencySkillExecution

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_skill_tuning_uses_ams_behavioral_feedback(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_feedback_source"
    now = datetime.now(UTC)

    # Insert into agency_skill_executions only (should NOT be used for skill tuning anymore)
    async with UnitOfWork(session_factory) as local_uow:
        exec_row = AgencySkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_id=skill_id,
            user_id=test_user.uuid,
            message_id=None,
            goal_id=None,
            execution_time_ms=123,
            outcome="failure",
            error_message="test",
            context_json=None,
            created_at=now.isoformat(),
        )
        await local_uow.agency_skill_executions.create(exec_row)
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    # No AMS behavioral feedback rows => no skill tuning lessons should be generated for this skill
    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    assert not any(l.lesson_type == "skill_tuning" and l.target_id == skill_id for l in lessons)


@pytest.mark.asyncio
async def test_reflection_user_feedback_uses_reward_reason_patterns(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)
    skill_id = "test_skill_feedback_reason"

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
                "reason": "wrong_tone",
                "timestamp": now,
                "processed": 1,
                "outcome": "failure",
                "execution_time_ms": 100,
                "context_json": None,
                "user_satisfaction": None,
                "free_text": None,
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    persona = [l for l in lessons if l.lesson_type == "persona_style"]
    assert persona
    assert any((l.proposed_change or {}).get("notes", {}).get("reasons") for l in persona)
