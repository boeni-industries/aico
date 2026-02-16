from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Optional

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.agency.arbiter_models import AgencyArbiterAdjustment
from aico.data.agency.skill_models import AgencySkillLearningData
from aico.data.ethics.policy_models import EthicsPolicyRule
from aico.data.ethics.value_models import EthicsValueProfile
from aico.data.uow import UnitOfWork

logger = get_logger("agency.lesson_applicator")


class LessonApplicationService:
    def __init__(
        self,
        config: ConfigurationManager,
        session_factory,
    ):
        self.config = config
        self.session_factory = session_factory
        self.min_confidence = float(config.get("agency.self_reflection.confidence_threshold", 0.7))

    async def apply_lesson(self, lesson) -> bool:
        confidence = float(getattr(lesson, "confidence", 0.0) or 0.0)
        if confidence < self.min_confidence:
            return False

        lesson_type = str(getattr(lesson, "lesson_type", "") or "")
        target_kind = str(getattr(lesson, "target_kind", "") or "")

        applied = False

        if lesson_type == "skill_tuning" and target_kind == "skill":
            applied = await self._apply_skill_tuning(lesson)

        if lesson_type == "planner_heuristic" and target_kind == "arbiter_weight":
            applied = await self._apply_arbiter_weight(lesson)

        if lesson_type == "curiosity_focus" and target_kind == "curiosity_policy":
            applied = await self._apply_curiosity_policy(lesson)

        if lesson_type == "policy_suggestion" and target_kind == "policy_rule":
            applied = await self._apply_policy_suggestion(lesson)

        if applied:
            now = datetime.now(UTC)
            lesson.applied_at = now
            lesson.applied_by = "self_reflection"
            lesson.updated_at = now

            async with UnitOfWork(self.session_factory) as uow:
                await uow.lessons.update(lesson)
                await uow.commit()

        return applied

    async def _apply_policy_suggestion(self, lesson) -> bool:
        proposed = getattr(lesson, "proposed_change", None) or {}
        if not isinstance(proposed, dict):
            return False

        change_type = proposed.get("change_type")
        if change_type != "threshold_tweak":
            return False

        field = proposed.get("field")
        if not isinstance(field, str) or not field.startswith("conditions_json."):
            return False

        condition_key = field.split(".", 1)[1].strip()
        if not condition_key:
            return False

        new_value = proposed.get("new")
        if new_value is None:
            return False

        try:
            new_threshold = float(new_value)
        except Exception:
            return False

        new_threshold = max(0.0, min(1.0, new_threshold))

        user_id = getattr(lesson, "user_id", None)
        rule_id = getattr(lesson, "target_id", None)
        if not user_id or not rule_id:
            return False

        async with UnitOfWork(self.session_factory) as uow:
            rule = await uow.ethics_policy_rules.get_by_id(str(rule_id))
            if not rule:
                return False

            conditions = rule.conditions_json if isinstance(rule.conditions_json, dict) else {}
            if condition_key not in conditions or not isinstance(conditions.get(condition_key), (int, float)):
                return False

            amended_conditions = dict(conditions)
            amended_conditions[condition_key] = new_threshold

            amended_rule_id = rule.rule_id

            if str(rule.scope) != "user" or str(rule.scope_id or "") != str(user_id):
                amended_rule_id = str(uuid.uuid4())
                amended = EthicsPolicyRule(
                    rule_id=amended_rule_id,
                    rule_name=str(rule.rule_name),
                    target_type=str(rule.target_type),
                    conditions_json=amended_conditions,
                    effect=str(rule.effect),
                    user_message_template=getattr(rule, "user_message_template", None),
                    priority=int(getattr(rule, "priority", 100) or 100),
                    enabled=bool(getattr(rule, "enabled", True)),
                    scope="user",
                    scope_id=str(user_id),
                    created_at=None,
                    updated_at=None,
                )
                await uow.ethics_policy_rules.create(amended)
            else:
                rule.conditions_json = amended_conditions
                await uow.ethics_policy_rules.update(rule)

            await uow.commit()

        logger.info(
            f"[LESSON_APPLICATOR] Applied policy threshold tweak rule_id={rule_id} amended_rule_id={amended_rule_id} "
            f"key={condition_key} new={new_threshold} user_id={user_id}"
        )
        return True

    async def _apply_curiosity_policy(self, lesson) -> bool:
        proposed = getattr(lesson, "proposed_change", None) or {}
        if not isinstance(proposed, dict):
            return False

        field = proposed.get("field") or getattr(lesson, "target_id", None)
        if field != "curiosity_intensity":
            return False

        new_value = proposed.get("new")
        if new_value is None:
            return False

        try:
            new_intensity = float(new_value)
        except Exception:
            return False

        new_intensity = max(0.0, min(1.0, new_intensity))

        user_id = getattr(lesson, "user_id", None)
        if not user_id:
            return False

        async with UnitOfWork(self.session_factory) as uow:
            profile = await uow.ethics_value_profiles.get_by_user_id(user_id)
            now = datetime.now(UTC)

            if profile is None:
                profile = EthicsValueProfile(
                    profile_id=str(uuid.uuid4()),
                    user_id=user_id,
                    sensitive_life_areas=json.dumps([]),
                    allowed_curiosity_domains=json.dumps([]),
                    curiosity_intensity=new_intensity,
                    autonomy_level="balanced",
                    storage_preferences=json.dumps({}),
                    created_at=now,
                    updated_at=now,
                )
                await uow.ethics_value_profiles.create(profile)
            else:
                profile.curiosity_intensity = new_intensity
                await uow.ethics_value_profiles.update(profile)

            await uow.commit()

        logger.info(f"[LESSON_APPLICATOR] Applied curiosity_intensity={new_intensity} for user_id={user_id}")
        return True

    async def _apply_arbiter_weight(self, lesson) -> bool:
        proposed = getattr(lesson, "proposed_change", None) or {}
        if not isinstance(proposed, dict):
            return False

        adjustment_key = proposed.get("adjustment_key") or getattr(lesson, "target_id", None)
        adjustment_value = proposed.get("adjustment_value")
        if not adjustment_key or adjustment_value is None:
            return False

        try:
            adjustment_value = float(adjustment_value)
        except Exception:
            return False

        now = datetime.now(UTC)
        entity = AgencyArbiterAdjustment(
            adjustment_key=str(adjustment_key),
            adjustment_value=adjustment_value,
            lesson_id=getattr(lesson, "lesson_id"),
            user_id=getattr(lesson, "user_id"),
            applied_at=now,
            confidence=float(getattr(lesson, "confidence", 0.0) or 0.0),
            active=True,
            notes=None,
        )

        async with UnitOfWork(self.session_factory) as uow:
            await uow.agency_arbiter_adjustments.create(entity)
            await uow.commit()

        logger.info(
            f"[LESSON_APPLICATOR] Applied arbiter_weight adjustment_key={adjustment_key} value={adjustment_value}"
        )
        return True

    async def _apply_skill_tuning(self, lesson) -> bool:
        skill_id = getattr(lesson, "target_id", None)
        if not skill_id:
            return False

        proposed = getattr(lesson, "proposed_change", None) or {}
        notes = proposed.get("notes") if isinstance(proposed, dict) else None
        failure = None
        total = None
        if isinstance(notes, dict):
            failure = notes.get("failure")
            total = notes.get("total")

        try:
            failure = int(failure) if failure is not None else 0
            total = int(total) if total is not None else 0
        except Exception:
            failure = 0
            total = 0

        failure_rate = (failure / total) if total else 0.0
        delta = max(-0.2, min(0.0, -0.1 * failure_rate))

        async with UnitOfWork(self.session_factory) as uow:
            existing: Optional[AgencySkillLearningData] = await uow.agency_skill_learning_data.get_by_id(skill_id)
            now = datetime.now(UTC).isoformat()

            if existing and existing.dimension_vector:
                try:
                    vec = json.loads(existing.dimension_vector)
                    if not isinstance(vec, list):
                        vec = [0.0] * 11
                except Exception:
                    vec = [0.0] * 11
            else:
                vec = [0.0] * 11

            if len(vec) < 1:
                vec = [0.0] * 11

            vec[0] = float(vec[0]) + float(delta)
            vec[0] = max(-1.0, min(1.0, vec[0]))

            entity = AgencySkillLearningData(
                skill_id=skill_id,
                dimension_vector=json.dumps(vec),
                created_at=getattr(existing, "created_at", None) or now,
                updated_at=now,
            )

            if existing:
                await uow.agency_skill_learning_data.update(skill_id, entity)
            else:
                await uow.agency_skill_learning_data.create(entity)

            await uow.commit()

        logger.info(
            f"[LESSON_APPLICATOR] Applied skill_tuning lesson to skill_id={skill_id} delta={delta}"
        )
        return True


__all__ = ["LessonApplicationService"]
