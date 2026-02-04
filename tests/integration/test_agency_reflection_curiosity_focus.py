import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_allow_amend_applies_curiosity_focus_updates_value_profile(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "allow_amend", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as local_uow:
        await local_uow._session.execute(
            text(
                """
                INSERT INTO agency_goals
                  (goal_id, user_id, origin, goal_type, title, description, status, priority, metadata_json, created_at, updated_at)
                VALUES
                  (:goal_id, :user_id, :origin, :goal_type, :title, :description, :status, :priority, :metadata_json, :created_at, :updated_at)
                """
            ),
            {
                "goal_id": str(uuid.uuid4()),
                "user_id": test_user.uuid,
                "origin": "curiosity",
                "goal_type": "exploration",
                "title": "Curiosity Goal",
                "description": "",
                "status": "retired",
                "priority": "normal",
                "metadata_json": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        await local_uow.commit()

    before = await uow.ethics_value_profiles.get_by_user_id(test_user.uuid)
    before_intensity = float(before.curiosity_intensity) if before else 0.5

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied >= 1

    after = await uow.ethics_value_profiles.get_by_user_id(test_user.uuid)
    assert after is not None
    assert float(after.curiosity_intensity) < before_intensity


@pytest.mark.asyncio
async def test_reflection_observe_only_does_not_apply_curiosity_focus(session_factory, uow, test_user):
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
                INSERT INTO agency_goals
                  (goal_id, user_id, origin, goal_type, title, description, status, priority, metadata_json, created_at, updated_at)
                VALUES
                  (:goal_id, :user_id, :origin, :goal_type, :title, :description, :status, :priority, :metadata_json, :created_at, :updated_at)
                """
            ),
            {
                "goal_id": str(uuid.uuid4()),
                "user_id": test_user.uuid,
                "origin": "curiosity",
                "goal_type": "exploration",
                "title": "Curiosity Goal",
                "description": "",
                "status": "retired",
                "priority": "normal",
                "metadata_json": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        await local_uow.commit()

    before = await uow.ethics_value_profiles.get_by_user_id(test_user.uuid)
    before_intensity = float(before.curiosity_intensity) if before else 0.5

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied == 0

    after = await uow.ethics_value_profiles.get_by_user_id(test_user.uuid)
    if after is None:
        assert before is None
    else:
        assert float(after.curiosity_intensity) == before_intensity
