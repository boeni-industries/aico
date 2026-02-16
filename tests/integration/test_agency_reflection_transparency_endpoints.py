import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine

from backend.api.agency.router import (
    get_skill_performance,
    list_reflection_lessons,
    list_reflection_runs,
    list_self_model,
)


@pytest.mark.asyncio
async def test_reflection_transparency_endpoints_return_data(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    skill_id = "test_skill_transparency"
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

    runs = await list_reflection_runs(user=user_ctx, uow=uow, limit=10)
    assert runs.total >= 1
    assert any(r.run_id == run.run_id for r in runs.runs)

    lessons = await list_reflection_lessons(user=user_ctx, uow=uow, active_only=False, lesson_type=None, limit=50)
    assert lessons.total >= 1

    models = await list_self_model(user=user_ctx, uow=uow, entity_type=None, limit=50)
    assert models.total >= 1
    assert any(m.entity_type == "skill" and m.entity_id == skill_id for m in models.models)

    perf = await get_skill_performance(skill_id=skill_id, user=user_ctx, uow=uow)
    assert perf.skill_id == skill_id
    assert isinstance(perf.performance_summary, dict)
    assert perf.performance_summary.get("latency_p50_ms") is not None
    assert perf.performance_summary.get("latency_p90_ms") is not None
    assert perf.performance_summary.get("latency_p99_ms") is not None
    assert perf.performance_summary.get("reward_min") is not None
    assert perf.performance_summary.get("reward_max") is not None
    assert isinstance(perf.performance_summary.get("outcome_breakdown"), dict)
    assert perf.performance_summary["outcome_breakdown"].get("failure") == 1
