import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork
from aico.ai.user.models import UserProfile

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_generates_persona_style_lesson_from_relationship_churn(session_factory, uow, test_user):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)
    related_uuid = f"test_related_{uuid.uuid4().hex[:8]}"

    async with UnitOfWork(session_factory) as local_uow:
        related_user = UserProfile(
            uuid=related_uuid,
            full_name="Related User",
            nickname="related",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=now,
            updated_at=now,
        )
        await local_uow.users.create(related_user)

        await local_uow._session.execute(
            text(
                """
                INSERT INTO user_relationships
                  (uuid, user_uuid, related_user_uuid, relationship_type, is_active, created_at, updated_at)
                VALUES
                  (:uuid, :user_uuid, :related_user_uuid, :relationship_type, :is_active, :created_at, :updated_at)
                """
            ),
            {
                "uuid": str(uuid.uuid4()),
                "user_uuid": test_user.uuid,
                "related_user_uuid": related_uuid,
                "relationship_type": "friend",
                "is_active": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1

    lessons = await uow.lessons.list(filters={"user_id": test_user.uuid}, limit=50)
    persona_lessons = [l for l in lessons if l.lesson_type == "persona_style"]
    assert persona_lessons
    assert any(
        l.proposed_change and l.proposed_change.get("change_type") == "template_update" for l in persona_lessons
    )
