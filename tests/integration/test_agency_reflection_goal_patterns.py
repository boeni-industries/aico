import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_allow_amend_creates_arbiter_adjustment_from_goal_patterns(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "allow_amend", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)
    goal_type = "learning"

    async with UnitOfWork(session_factory) as local_uow:
        # Create a retired goal to push retirement_rate over 0.5
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
                "origin": "test",
                "goal_type": goal_type,
                "title": "Test goal",
                "description": "",
                "status": "retired",
                "priority": "normal",
                "metadata_json": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied >= 1

    adjustment_key = f"goal_type_{goal_type}"
    adj = await uow.agency_arbiter_adjustments.get_by_id(adjustment_key)
    assert adj is not None
    assert adj.active is True
