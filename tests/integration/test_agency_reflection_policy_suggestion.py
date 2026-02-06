import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from aico.core.config import ConfigurationManager
from aico.data.ethics.policy_models import EthicsPolicyRule
from aico.data.uow import UnitOfWork

from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_reflection_allow_amend_applies_policy_suggestion_by_creating_user_override_rule(
    session_factory, uow, test_user
):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "allow_amend", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)

    base_rule_id = str(uuid.uuid4())
    base_rule = EthicsPolicyRule(
        rule_id=base_rule_id,
        rule_name="Test Rule",
        target_type="curiosity_signal",
        conditions_json={"curiosity_intensity": 0.7},
        effect="block",
        user_message_template=None,
        priority=50,
        enabled=True,
        scope="global",
        scope_id=None,
        created_at=now,
        updated_at=now,
    )

    async with UnitOfWork(session_factory) as local_uow:
        await local_uow.ethics_policy_rules.create(base_rule)
        await local_uow.commit()

        # Record repeated blocks referencing the rule
        for _ in range(3):
            await local_uow._session.execute(
                text(
                    """
                    INSERT INTO ethics_gate_audit
                      (audit_id, user_id, target_type, target_id, decision, reasoning, policy_rules_applied,
                       check_level, cached, processing_time_ms, created_at)
                    VALUES
                      (:audit_id, :user_id, :target_type, :target_id, :decision, :reasoning, :policy_rules_applied,
                       :check_level, :cached, :processing_time_ms, :created_at)
                    """
                ),
                {
                    "audit_id": str(uuid.uuid4()),
                    "user_id": test_user.uuid,
                    "target_type": "curiosity_signal",
                    "target_id": str(uuid.uuid4()),
                    "decision": "block",
                    "reasoning": None,
                    "policy_rules_applied": f"[\"{base_rule_id}\"]",
                    "check_level": 1,
                    "cached": 0,
                    "processing_time_ms": 1,
                    "created_at": now.isoformat(),
                },
            )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied >= 1

    # Verify a user-scoped rule exists with tweaked curiosity_intensity threshold
    rules = await uow.ethics_policy_rules.list(filters={"target_type": "curiosity_signal", "enabled": True}, limit=50)
    user_rules = [r for r in rules if r.scope == "user" and r.scope_id == test_user.uuid]
    assert user_rules

    overridden = user_rules[0]
    assert isinstance(overridden.conditions_json, dict)
    assert float(overridden.conditions_json.get("curiosity_intensity")) >= 0.75


@pytest.mark.asyncio
async def test_reflection_observe_only_generates_policy_suggestion_but_does_not_apply(
    session_factory, uow, test_user
):
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    config.set("agency.self_reflection.enabled", True, persist=False)
    config.set("agency.self_reflection.policy_mode", "observe_only", persist=False)
    config.set("agency.self_reflection.min_sample_size", 1, persist=False)
    config.set("agency.self_reflection.confidence_threshold", 0.0, persist=False)

    now = datetime.now(UTC)

    base_rule_id = str(uuid.uuid4())
    base_rule = EthicsPolicyRule(
        rule_id=base_rule_id,
        rule_name="Test Rule",
        target_type="curiosity_signal",
        conditions_json={"curiosity_intensity": 0.7},
        effect="block",
        user_message_template=None,
        priority=50,
        enabled=True,
        scope="global",
        scope_id=None,
        created_at=now,
        updated_at=now,
    )

    async with UnitOfWork(session_factory) as local_uow:
        await local_uow.ethics_policy_rules.create(base_rule)
        await local_uow.commit()

        await local_uow._session.execute(
            text(
                """
                INSERT INTO ethics_gate_audit
                  (audit_id, user_id, target_type, target_id, decision, reasoning, policy_rules_applied,
                   check_level, cached, processing_time_ms, created_at)
                VALUES
                  (:audit_id, :user_id, :target_type, :target_id, :decision, :reasoning, :policy_rules_applied,
                   :check_level, :cached, :processing_time_ms, :created_at)
                """
            ),
            {
                "audit_id": str(uuid.uuid4()),
                "user_id": test_user.uuid,
                "target_type": "curiosity_signal",
                "target_id": str(uuid.uuid4()),
                "decision": "block",
                "reasoning": None,
                "policy_rules_applied": f"[\"{base_rule_id}\"]",
                "check_level": 1,
                "cached": 0,
                "processing_time_ms": 1,
                "created_at": now.isoformat(),
            },
        )
        await local_uow.commit()

    engine = SelfReflectionEngine(config=config, session_factory=session_factory)
    result = await engine.run_reflection(user_id=test_user.uuid, analysis_window_days=7)

    assert result.lessons_generated >= 1
    assert result.lessons_applied == 0

    rules = await uow.ethics_policy_rules.list(filters={"target_type": "curiosity_signal", "enabled": True}, limit=50)
    user_rules = [r for r in rules if r.scope == "user" and r.scope_id == test_user.uuid]
    assert not user_rules
