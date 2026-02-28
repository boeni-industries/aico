from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, func, select, update

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.agency.lesson_models import Lesson as DbLesson
from aico.data.agency.reflection_models import AgencyReflectionRun, AgencySelfModel
from aico.data.ethics.policy_models import EthicsPolicyRule
from aico.data.tables import (
    agency_goals,
    agency_skill_executions,
    ams_behavioral_feedback,
    agency_lessons,
    emotion_history,
    ethics_gate_audit,
    user_relationships,
)
from aico.data.uow import UnitOfWork

from .lesson_applicator import LessonApplicationService
from .models import LessonScope, LessonStatus, LessonType, ReflectionRun, RunStatus, RunType

logger = get_logger("agency.reflection")


class SelfReflectionEngine:
    def __init__(
        self,
        config: ConfigurationManager,
        session_factory,
        llm_client: Optional[Any] = None,
    ):
        self.config = config
        self.session_factory = session_factory
        self.llm_client = llm_client

        self.policy_mode = config.get("agency.self_reflection.policy_mode", "observe_only")
        self.min_sample_size = int(config.get("agency.self_reflection.min_sample_size", 10))
        self.confidence_threshold = float(config.get("agency.self_reflection.confidence_threshold", 0.7))

        self.lesson_applicator = LessonApplicationService(
            config=config,
            session_factory=session_factory,
        )

    def _should_apply_lessons(self) -> bool:
        mode = str(self.policy_mode or "observe_only").lower()
        self._validate_policy_mode(mode)
        return mode in {"allow_amend"}

    def _is_disabled(self) -> bool:
        mode = str(self.policy_mode or "observe_only").lower()
        self._validate_policy_mode(mode)
        return mode in {"disabled", "off", "false"}

    def _validate_policy_mode(self, mode: str) -> None:
        allowed = {"observe_only", "allow_amend", "disabled", "off", "false"}
        if mode not in allowed:
            raise ValueError(
                "Invalid agency.self_reflection.policy_mode: "
                f"{mode!r}. Allowed: observe_only | allow_amend | disabled"
            )

    async def run_reflection(
        self,
        user_id: str,
        run_type: RunType = RunType.SCHEDULED,
        trigger_reason: Optional[str] = None,
        analysis_window_days: int = 7,
    ) -> ReflectionRun:
        if self._is_disabled():
            raise RuntimeError("Self-reflection is disabled via agency.self_reflection.policy_mode")

        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        window_end = started_at
        window_start = window_end - timedelta(days=analysis_window_days)

        db_run = AgencyReflectionRun(
            run_id=run_id,
            user_id=user_id,
            run_type=run_type.value,
            trigger_reason=trigger_reason,
            analysis_window_start=window_start,
            analysis_window_end=window_end,
            lessons_generated=0,
            lessons_applied=0,
            started_at=started_at,
            completed_at=None,
            duration_seconds=None,
            status=RunStatus.RUNNING.value,
            error_message=None,
            created_at=started_at,
        )

        async with UnitOfWork(self.session_factory) as uow:
            await uow.agency_reflection_runs.create(db_run)
            await uow.commit()

        try:
            lessons: List[DbLesson] = []
            lessons.extend(await self._analyze_skill_executions(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_goal_patterns(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_user_feedback(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_curiosity_outcomes(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_emotion_patterns(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_social_patterns(user_id, window_start, window_end, run_id))
            lessons.extend(await self._analyze_policy_patterns(user_id, window_start, window_end, run_id))

            applied = 0
            async with UnitOfWork(self.session_factory) as uow:
                for lesson in lessons:
                    await uow.lessons.create(lesson)

                    now = datetime.now(UTC)
                    if getattr(lesson, "target_id", None) is not None:
                        await uow._session.execute(
                            update(agency_lessons)
                            .where(
                                and_(
                                    agency_lessons.c.user_id == lesson.user_id,
                                    agency_lessons.c.lesson_type == lesson.lesson_type,
                                    agency_lessons.c.target_kind == lesson.target_kind,
                                    agency_lessons.c.target_id == lesson.target_id,
                                    agency_lessons.c.status == LessonStatus.ACTIVE.value,
                                    agency_lessons.c.superseded_by.is_(None),
                                    agency_lessons.c.lesson_id != lesson.lesson_id,
                                )
                            )
                            .values(
                                superseded_by=lesson.lesson_id,
                                status=LessonStatus.SUPERSEDED.value,
                                updated_at=now,
                            )
                        )
                await uow.commit()

            if self._should_apply_lessons():
                for lesson in lessons:
                    try:
                        if float(lesson.confidence or 0.0) < self.confidence_threshold:
                            continue
                        did_apply = await self.lesson_applicator.apply_lesson(lesson)
                        if did_apply:
                            applied += 1
                    except Exception as e:
                        logger.exception(
                            f"[REFLECTION] Failed applying lesson {getattr(lesson, 'lesson_id', None)}: {e}"
                        )

            completed_at = datetime.now(UTC)
            duration_seconds = float((completed_at - started_at).total_seconds())

            async with UnitOfWork(self.session_factory) as uow:
                run_entity: Optional[AgencyReflectionRun] = await uow.agency_reflection_runs.get_by_id(run_id)
                if run_entity:
                    run_entity.lessons_generated = len(lessons)
                    run_entity.lessons_applied = applied
                    run_entity.completed_at = completed_at
                    run_entity.duration_seconds = duration_seconds
                    run_entity.status = RunStatus.COMPLETED.value
                    await uow.agency_reflection_runs.update(run_id, run_entity)
                await uow.commit()

            return ReflectionRun(
                run_id=run_id,
                user_id=user_id,
                run_type=run_type,
                trigger_reason=trigger_reason,
                analysis_window_start=window_start,
                analysis_window_end=window_end,
                lessons_generated=len(lessons),
                lessons_applied=applied,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                status=RunStatus.COMPLETED,
                error_message=None,
            )
        except Exception as e:
            completed_at = datetime.now(UTC)
            duration_seconds = float((completed_at - started_at).total_seconds())

            async with UnitOfWork(self.session_factory) as uow:
                run_entity: Optional[AgencyReflectionRun] = await uow.agency_reflection_runs.get_by_id(run_id)
                if run_entity:
                    run_entity.completed_at = completed_at
                    run_entity.duration_seconds = duration_seconds
                    run_entity.status = RunStatus.FAILED.value
                    run_entity.error_message = str(e)
                    await uow.agency_reflection_runs.update(run_id, run_entity)
                await uow.commit()

            raise

    async def get_active_lessons(self, user_id: str, lesson_type: Optional[str] = None) -> List[DbLesson]:
        async with UnitOfWork(self.session_factory) as uow:
            return await uow.lessons.get_active_lessons(user_id, lesson_type)

    async def get_self_model(self, user_id: str, entity_type: str, entity_id: str) -> Optional[AgencySelfModel]:
        async with UnitOfWork(self.session_factory) as uow:
            return await uow.agency_self_model.get_by_entity(user_id, entity_type, entity_id)

    async def get_skill_performance(self, user_id: str, skill_id: str) -> Optional[Dict[str, Any]]:
        model = await self.get_self_model(user_id, "skill", skill_id)
        if not model:
            return None
        try:
            return json.loads(model.performance_summary) if model.performance_summary else None
        except Exception:
            return None

    async def get_goal_type_performance(self, user_id: str, goal_type: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific goal type."""
        model = await self.get_self_model(user_id, "goal_type", goal_type)
        if not model:
            return None
        try:
            return json.loads(model.performance_summary) if model.performance_summary else None
        except Exception:
            return None

    async def get_all_skill_performances(self, user_id: str) -> Dict[str, Any]:
        """Get performance metrics for all skills."""
        async with UnitOfWork(self.session_factory) as uow:
            models = await uow.agency_self_model.get_user_models(user_id, entity_type="skill")
            performances = {}
            for model in models:
                try:
                    perf = json.loads(model.performance_summary) if model.performance_summary else {}
                    performances[model.entity_id] = perf
                except Exception:
                    continue
            return performances

    async def _analyze_skill_executions(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        def _percentile(values: List[float], p: float) -> Optional[float]:
            if not values:
                return None
            if p <= 0:
                return float(min(values))
            if p >= 1:
                return float(max(values))
            sorted_vals = sorted(values)
            k = (len(sorted_vals) - 1) * p
            f = int(k)
            c = min(f + 1, len(sorted_vals) - 1)
            if f == c:
                return float(sorted_vals[f])
            d0 = sorted_vals[f] * (c - k)
            d1 = sorted_vals[c] * (k - f)
            return float(d0 + d1)

        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    ams_behavioral_feedback.c.skill_id.label("skill_id"),
                    ams_behavioral_feedback.c.outcome.label("outcome"),
                    func.count().label("count"),
                    func.avg(ams_behavioral_feedback.c.reward).label("avg_reward"),
                    func.avg(ams_behavioral_feedback.c.execution_time_ms).label("avg_exec_ms"),
                )
                .where(
                    and_(
                        ams_behavioral_feedback.c.user_id == user_id,
                        ams_behavioral_feedback.c.skill_id.is_not(None),
                        ams_behavioral_feedback.c.timestamp >= window_start,
                        ams_behavioral_feedback.c.timestamp <= window_end,
                    )
                )
                .group_by(ams_behavioral_feedback.c.skill_id, ams_behavioral_feedback.c.outcome)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()

            raw_stmt = (
                select(
                    ams_behavioral_feedback.c.skill_id.label("skill_id"),
                    ams_behavioral_feedback.c.outcome.label("outcome"),
                    ams_behavioral_feedback.c.reward.label("reward"),
                    ams_behavioral_feedback.c.execution_time_ms.label("execution_time_ms"),
                )
                .where(
                    and_(
                        ams_behavioral_feedback.c.user_id == user_id,
                        ams_behavioral_feedback.c.skill_id.is_not(None),
                        ams_behavioral_feedback.c.timestamp >= window_start,
                        ams_behavioral_feedback.c.timestamp <= window_end,
                    )
                )
            )
            raw_result = await session.execute(raw_stmt)
            raw_rows = raw_result.fetchall()

        per_skill: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            skill_id = str(row.skill_id or "")
            if not skill_id:
                continue
            outcome = str(row.outcome or "")
            count = int(row.count or 0)
            if skill_id not in per_skill:
                per_skill[skill_id] = {
                    "success": 0,
                    "failure": 0,
                    "total": 0,
                    "outcomes": {},
                    "reward_sum": 0.0,
                    "reward_n": 0,
                    "exec_ms_sum": 0.0,
                    "exec_ms_n": 0,
                }
            if outcome in {"success", "ok"}:
                per_skill[skill_id]["success"] += count
            else:
                per_skill[skill_id]["failure"] += count
            per_skill[skill_id]["total"] += count

            outcomes = per_skill[skill_id].setdefault("outcomes", {})
            outcomes[outcome] = int(outcomes.get(outcome, 0) or 0) + count

            if row.avg_reward is not None:
                per_skill[skill_id]["reward_sum"] += float(row.avg_reward) * float(count)
                per_skill[skill_id]["reward_n"] += count
            if row.avg_exec_ms is not None:
                per_skill[skill_id]["exec_ms_sum"] += float(row.avg_exec_ms) * float(count)
                per_skill[skill_id]["exec_ms_n"] += count

        per_skill_samples: Dict[str, Dict[str, List[float]]] = {}
        for row in raw_rows:
            skill_id = str(row.skill_id or "")
            if not skill_id:
                continue
            if skill_id not in per_skill_samples:
                per_skill_samples[skill_id] = {"rewards": [], "exec_ms": []}

            if row.reward is not None:
                try:
                    per_skill_samples[skill_id]["rewards"].append(float(row.reward))
                except Exception:
                    pass
            if row.execution_time_ms is not None:
                try:
                    per_skill_samples[skill_id]["exec_ms"].append(float(row.execution_time_ms))
                except Exception:
                    pass

        lessons: List[DbLesson] = []
        now = datetime.now(UTC)

        for skill_id, stats in per_skill.items():
            total = int(stats.get("total", 0) or 0)
            if total < self.min_sample_size:
                continue

            success = int(stats.get("success", 0) or 0)
            failure = int(stats.get("failure", 0) or 0)
            success_rate = (success / total) if total else 0.0

            avg_reward = None
            if int(stats.get("reward_n", 0) or 0) > 0:
                avg_reward = float(stats.get("reward_sum", 0.0) or 0.0) / float(stats.get("reward_n", 1) or 1)

            avg_exec_ms = None
            if int(stats.get("exec_ms_n", 0) or 0) > 0:
                avg_exec_ms = float(stats.get("exec_ms_sum", 0.0) or 0.0) / float(stats.get("exec_ms_n", 1) or 1)

            samples = per_skill_samples.get(skill_id, {"rewards": [], "exec_ms": []})
            reward_values = samples.get("rewards", [])
            exec_values = samples.get("exec_ms", [])

            reward_min = float(min(reward_values)) if reward_values else None
            reward_max = float(max(reward_values)) if reward_values else None

            latency_p50_ms = _percentile(exec_values, 0.50)
            latency_p90_ms = _percentile(exec_values, 0.90)
            latency_p99_ms = _percentile(exec_values, 0.99)

            outcomes = stats.get("outcomes", {}) if isinstance(stats.get("outcomes", {}), dict) else {}

            model = AgencySelfModel(
                model_id=str(uuid.uuid4()),
                user_id=user_id,
                entity_type="skill",
                entity_id=skill_id,
                performance_summary=json.dumps(
                    {
                        "success_rate": success_rate,
                        "total": total,
                        "failure": failure,
                        "avg_reward": avg_reward,
                        "reward_min": reward_min,
                        "reward_max": reward_max,
                        "avg_execution_time_ms": avg_exec_ms,
                        "latency_p50_ms": latency_p50_ms,
                        "latency_p90_ms": latency_p90_ms,
                        "latency_p99_ms": latency_p99_ms,
                        "outcome_breakdown": outcomes,
                    }
                ),
                window_start=window_start,
                window_end=window_end,
                sample_size=total,
                confidence=min(1.0, total / max(self.min_sample_size, 1)),
                last_updated=now,
                created_at=now,
            )

            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_self_model.create(model)
                await uow.commit()

            if failure <= 0 and (avg_reward is None or avg_reward >= 0.0):
                continue

            confidence = min(1.0, max(failure / total if total else 0.0, abs(avg_reward) if avg_reward is not None else 0.0))

            lesson = DbLesson(
                lesson_id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_type=LessonType.SKILL_TUNING.value,
                target_kind="skill",
                target_id=skill_id,
                summary_text="Adjust skill usage based on observed outcomes.",
                proposed_change={
                    "change_type": "weight_tweak",
                    "notes": {
                        "success_rate": success_rate,
                        "total": total,
                        "failure": failure,
                        "avg_reward": avg_reward,
                        "reward_min": reward_min,
                        "reward_max": reward_max,
                        "avg_execution_time_ms": avg_exec_ms,
                        "latency_p50_ms": latency_p50_ms,
                        "latency_p90_ms": latency_p90_ms,
                        "latency_p99_ms": latency_p99_ms,
                        "outcome_breakdown": outcomes,
                    },
                },
                confidence=float(confidence),
                metrics_basis={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "success": success,
                    "failure": failure,
                    "total": total,
                    "outcome_breakdown": outcomes,
                },
                scope=LessonScope.THIS_USER.value,
                status=LessonStatus.ACTIVE.value,
                superseded_by=None,
                applied_at=None,
                applied_by=None,
                source_reflection_run_id=run_id,
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                related_goal_ids=[],
                related_trajectory_ids=[],
                related_event_ids=[],
                metadata=None,
                created_at=now,
                updated_at=now,
            )
            lessons.append(lesson)

        return lessons

    async def _analyze_goal_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    agency_goals.c.goal_type.label("goal_type"),
                    agency_goals.c.status.label("status"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        agency_goals.c.user_id == user_id,
                        agency_goals.c.created_at >= window_start,
                        agency_goals.c.created_at <= window_end,
                    )
                )
                .group_by(agency_goals.c.goal_type, agency_goals.c.status)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()

        stats: Dict[str, Dict[str, int]] = {}
        for row in rows:
            gt = str(row.goal_type or "")
            if not gt:
                continue
            if gt not in stats:
                stats[gt] = {"completed": 0, "retired": 0, "active": 0, "total": 0}
            status = str(row.status or "")
            count = int(row.count or 0)
            if status in stats[gt]:
                stats[gt][status] += count
            stats[gt]["total"] += count

        lessons: List[DbLesson] = []
        now = datetime.now(UTC)

        for goal_type, s in stats.items():
            total = int(s.get("total", 0) or 0)
            if total < self.min_sample_size:
                continue

            completed = int(s.get("completed", 0) or 0)
            retired = int(s.get("retired", 0) or 0)
            completion_rate = (completed / total) if total else 0.0
            retirement_rate = (retired / total) if total else 0.0

            model = AgencySelfModel(
                model_id=str(uuid.uuid4()),
                user_id=user_id,
                entity_type="goal_type",
                entity_id=goal_type,
                performance_summary=json.dumps(
                    {
                        "completion_rate": completion_rate,
                        "retirement_rate": retirement_rate,
                        "total": total,
                    }
                ),
                window_start=window_start,
                window_end=window_end,
                sample_size=total,
                confidence=min(1.0, total / max(self.min_sample_size, 1)),
                last_updated=now,
                created_at=now,
            )
            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_self_model.create(model)
                await uow.commit()

            if retirement_rate <= 0.5:
                continue

            confidence = min(1.0, retired / total) if total else 0.0
            adjustment_key = f"goal_type_{goal_type}"
            new_weight = max(0.1, 1.0 - (0.5 * retirement_rate))

            lessons.append(
                DbLesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.PLANNER_HEURISTIC.value,
                    target_kind="arbiter_weight",
                    target_id=adjustment_key,
                    summary_text="Adjust goal prioritization based on observed goal outcomes.",
                    proposed_change={
                        "change_type": "weight_tweak",
                        "adjustment_key": adjustment_key,
                        "adjustment_value": new_weight,
                        "notes": {
                            "completion_rate": completion_rate,
                            "retirement_rate": retirement_rate,
                            "total": total,
                        },
                    },
                    confidence=float(confidence),
                    metrics_basis={
                        "window_start": window_start.isoformat(),
                        "window_end": window_end.isoformat(),
                        "completed": completed,
                        "retired": retired,
                        "total": total,
                    },
                    scope=LessonScope.THIS_USER.value,
                    status=LessonStatus.ACTIVE.value,
                    superseded_by=None,
                    applied_at=None,
                    applied_by=None,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                    related_goal_ids=[],
                    related_trajectory_ids=[],
                    related_event_ids=[],
                    metadata=None,
                    created_at=now,
                    updated_at=now,
                )
            )

        return lessons

    async def _analyze_user_feedback(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    func.avg(ams_behavioral_feedback.c.user_satisfaction).label("avg_satisfaction"),
                    func.avg(ams_behavioral_feedback.c.reward).label("avg_reward"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        ams_behavioral_feedback.c.user_id == user_id,
                        ams_behavioral_feedback.c.timestamp >= window_start,
                        ams_behavioral_feedback.c.timestamp <= window_end,
                    )
                )
            )
            result = await session.execute(stmt)
            row = result.fetchone()

            reason_stmt = (
                select(
                    ams_behavioral_feedback.c.reason.label("reason"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        ams_behavioral_feedback.c.user_id == user_id,
                        ams_behavioral_feedback.c.timestamp >= window_start,
                        ams_behavioral_feedback.c.timestamp <= window_end,
                        ams_behavioral_feedback.c.reason.is_not(None),
                    )
                )
                .group_by(ams_behavioral_feedback.c.reason)
            )
            reason_result = await session.execute(reason_stmt)
            reason_rows = reason_result.fetchall()

        if not row:
            return []

        avg_sat = row.avg_satisfaction
        avg_reward = row.avg_reward
        count = int(row.count or 0)
        if count < self.min_sample_size:
            return []

        reasons: Dict[str, int] = {}
        for r in reason_rows:
            reason = str(r.reason or "")
            if not reason:
                continue
            reasons[reason] = int(r.count or 0)

        now = datetime.now(UTC)

        sat_bad = avg_sat is not None and float(avg_sat) < 0.5
        reward_bad = avg_reward is not None and float(avg_reward) < 0.0
        if not (sat_bad or reward_bad):
            return []

        confidence = min(1.0, count / max(self.min_sample_size, 1))
        return [
            DbLesson(
                lesson_id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_type=LessonType.PERSONA_STYLE.value,
                target_kind="persona_trait",
                target_id="response_style",
                summary_text="Adjust interaction style based on user satisfaction signals.",
                proposed_change={
                    "change_type": "template_update",
                    "notes": {
                        "avg_satisfaction": float(avg_sat) if avg_sat is not None else None,
                        "avg_reward": float(avg_reward) if avg_reward is not None else None,
                        "reasons": reasons,
                        "count": count,
                    },
                },
                confidence=float(confidence),
                metrics_basis={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "avg_satisfaction": float(avg_sat) if avg_sat is not None else None,
                    "avg_reward": float(avg_reward) if avg_reward is not None else None,
                    "reasons": reasons,
                    "count": count,
                },
                scope=LessonScope.THIS_USER.value,
                status=LessonStatus.ACTIVE.value,
                superseded_by=None,
                applied_at=None,
                applied_by=None,
                source_reflection_run_id=run_id,
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                related_goal_ids=[],
                related_trajectory_ids=[],
                related_event_ids=[],
                metadata=None,
                created_at=now,
                updated_at=now,
            )
        ]

    def _parse_policy_rules_applied(self, raw: Optional[str]) -> List[str]:
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x]
            if isinstance(parsed, dict):
                return [str(x) for x in parsed.get("rule_ids", []) if x]
        except Exception:
            pass

        parts = [p.strip() for p in str(raw).replace(";", ",").split(",")]
        return [p for p in parts if p]

    async def _analyze_policy_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        """Generate policy suggestion lessons based on repeated ethics gate blocks.

        This is intentionally conservative: it proposes small threshold relaxations
        (increase numeric condition thresholds) only when a specific rule repeatedly
        blocks within the analysis window.
        """

        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    ethics_gate_audit.c.decision.label("decision"),
                    ethics_gate_audit.c.policy_rules_applied.label("policy_rules_applied"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        ethics_gate_audit.c.user_id == user_id,
                        ethics_gate_audit.c.created_at >= window_start,
                        ethics_gate_audit.c.created_at <= window_end,
                    )
                )
                .group_by(ethics_gate_audit.c.decision, ethics_gate_audit.c.policy_rules_applied)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()

        counts_by_rule: Dict[str, Dict[str, int]] = {}
        for row in rows:
            decision = str(row.decision or "")
            count = int(row.count or 0)
            for rule_id in self._parse_policy_rules_applied(row.policy_rules_applied):
                if rule_id not in counts_by_rule:
                    counts_by_rule[rule_id] = {"block": 0, "total": 0}
                if decision == "block":
                    counts_by_rule[rule_id]["block"] += count
                counts_by_rule[rule_id]["total"] += count

        lessons: List[DbLesson] = []
        now = datetime.now(UTC)

        async with UnitOfWork(self.session_factory) as uow:
            for rule_id, stats in counts_by_rule.items():
                total = int(stats.get("total", 0) or 0)
                block = int(stats.get("block", 0) or 0)
                if total < self.min_sample_size:
                    continue

                block_rate = (block / total) if total else 0.0
                if block_rate < 0.7:
                    continue

                rule: Optional[EthicsPolicyRule] = await uow.ethics_policy_rules.get_by_id(rule_id)
                if not rule:
                    continue

                conditions = rule.conditions_json if isinstance(rule.conditions_json, dict) else {}
                numeric_keys = [k for k, v in conditions.items() if isinstance(v, (int, float))]
                if not numeric_keys:
                    continue

                key = numeric_keys[0]
                old = float(conditions[key])
                new = max(old, min(1.0, old + 0.05))
                if abs(new - old) < 1e-9:
                    continue

                confidence = min(1.0, block / max(self.min_sample_size, 1))

                lessons.append(
                    DbLesson(
                        lesson_id=str(uuid.uuid4()),
                        user_id=user_id,
                        lesson_type=LessonType.POLICY_SUGGESTION.value,
                        target_kind="policy_rule",
                        target_id=rule_id,
                        summary_text="Adjust policy threshold based on repeated ethics blocks.",
                        proposed_change={
                            "change_type": "threshold_tweak",
                            "field": f"conditions_json.{key}",
                            "old": old,
                            "new": new,
                            "notes": {
                                "block": block,
                                "total": total,
                                "block_rate": block_rate,
                            },
                        },
                        confidence=float(confidence),
                        metrics_basis={
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "block": block,
                            "total": total,
                            "block_rate": block_rate,
                        },
                        scope=LessonScope.THIS_USER.value,
                        status=LessonStatus.ACTIVE.value,
                        superseded_by=None,
                        applied_at=None,
                        applied_by=None,
                        source_reflection_run_id=run_id,
                        evidence_window_start=window_start,
                        evidence_window_end=window_end,
                        related_goal_ids=[],
                        related_trajectory_ids=[],
                        related_event_ids=[],
                        metadata=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

            await uow.commit()

        return lessons

    async def _analyze_social_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        """Analyze relationship changes as a conservative proxy for social churn.

        Note: user_relationships is relationship metadata, not interaction telemetry.
        We therefore only infer coarse signals (e.g., many deactivations).
        """

        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    func.count().label("changed_count"),
                    func.sum(case((user_relationships.c.is_active.is_(False), 1), else_=0)).label("deactivated_count"),
                )
                .where(
                    and_(
                        user_relationships.c.user_uuid == user_id,
                        user_relationships.c.updated_at >= window_start,
                        user_relationships.c.updated_at <= window_end,
                    )
                )
            )
            result = await session.execute(stmt)
            row = result.fetchone()

        if not row:
            return []

        changed_count = int(row.changed_count or 0)
        deactivated_count = int(row.deactivated_count or 0)

        if changed_count < self.min_sample_size:
            return []

        churn_rate = (deactivated_count / changed_count) if changed_count else 0.0
        if churn_rate <= 0.5:
            return []

        now = datetime.now(UTC)
        confidence = min(1.0, changed_count / max(self.min_sample_size, 1))

        return [
            DbLesson(
                lesson_id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_type=LessonType.PERSONA_STYLE.value,
                target_kind="persona_trait",
                target_id="response_style",
                summary_text="Adjust interaction style based on social/relationship churn signals.",
                proposed_change={
                    "change_type": "template_update",
                    "notes": {
                        "changed_count": changed_count,
                        "deactivated_count": deactivated_count,
                        "churn_rate": churn_rate,
                    },
                },
                confidence=float(confidence),
                metrics_basis={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "changed_count": changed_count,
                    "deactivated_count": deactivated_count,
                    "churn_rate": churn_rate,
                },
                scope=LessonScope.THIS_USER.value,
                status=LessonStatus.ACTIVE.value,
                superseded_by=None,
                applied_at=None,
                applied_by=None,
                source_reflection_run_id=run_id,
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                related_goal_ids=[],
                related_trajectory_ids=[],
                related_event_ids=[],
                metadata=None,
                created_at=now,
                updated_at=now,
            )
        ]

    async def _analyze_emotion_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    func.avg(emotion_history.c.valence).label("avg_valence"),
                    func.avg(emotion_history.c.arousal).label("avg_arousal"),
                    func.avg(emotion_history.c.intensity).label("avg_intensity"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        emotion_history.c.user_id == user_id,
                        emotion_history.c.timestamp >= window_start,
                        emotion_history.c.timestamp <= window_end,
                    )
                )
            )
            result = await session.execute(stmt)
            row = result.fetchone()

        if not row:
            return []

        count = int(row.count or 0)
        if count < self.min_sample_size:
            return []

        avg_valence = float(row.avg_valence) if row.avg_valence is not None else 0.0
        avg_intensity = float(row.avg_intensity) if row.avg_intensity is not None else 0.0
        avg_arousal = float(row.avg_arousal) if row.avg_arousal is not None else 0.0

        if avg_valence >= -0.2:
            return []

        if avg_intensity < 0.6:
            return []

        now = datetime.now(UTC)
        confidence = min(1.0, count / max(self.min_sample_size, 1))

        return [
            DbLesson(
                lesson_id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_type=LessonType.PERSONA_STYLE.value,
                target_kind="persona_trait",
                target_id="response_style",
                summary_text="Adjust interaction style based on sustained emotional distress signals.",
                proposed_change={
                    "change_type": "template_update",
                    "notes": {
                        "avg_valence": avg_valence,
                        "avg_arousal": avg_arousal,
                        "avg_intensity": avg_intensity,
                        "count": count,
                    },
                },
                confidence=float(confidence),
                metrics_basis={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "avg_valence": avg_valence,
                    "avg_arousal": avg_arousal,
                    "avg_intensity": avg_intensity,
                    "count": count,
                },
                scope=LessonScope.THIS_USER.value,
                status=LessonStatus.ACTIVE.value,
                superseded_by=None,
                applied_at=None,
                applied_by=None,
                source_reflection_run_id=run_id,
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                related_goal_ids=[],
                related_trajectory_ids=[],
                related_event_ids=[],
                metadata=None,
                created_at=now,
                updated_at=now,
            )
        ]

    async def _analyze_curiosity_outcomes(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[DbLesson]:
        async with UnitOfWork(self.session_factory) as uow:
            session = uow._session
            stmt = (
                select(
                    agency_goals.c.status.label("status"),
                    func.count().label("count"),
                )
                .where(
                    and_(
                        agency_goals.c.user_id == user_id,
                        agency_goals.c.origin == "curiosity",
                        agency_goals.c.created_at >= window_start,
                        agency_goals.c.created_at <= window_end,
                    )
                )
                .group_by(agency_goals.c.status)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()

            profile = await uow.ethics_value_profiles.get_by_user_id(user_id)

        stats: Dict[str, int] = {"completed": 0, "retired": 0, "active": 0, "total": 0}
        for row in rows:
            status = str(row.status or "")
            count = int(row.count or 0)
            if status in stats:
                stats[status] += count
            stats["total"] += count

        total = int(stats.get("total", 0) or 0)
        if total < self.min_sample_size:
            return []

        retired = int(stats.get("retired", 0) or 0)
        retirement_rate = (retired / total) if total else 0.0
        if retirement_rate <= 0.5:
            return []

        old_intensity = 0.5
        if profile and getattr(profile, "curiosity_intensity", None) is not None:
            try:
                old_intensity = float(profile.curiosity_intensity)
            except Exception:
                old_intensity = 0.5

        new_intensity = max(0.0, min(1.0, old_intensity - (0.2 * retirement_rate)))
        if abs(new_intensity - old_intensity) < 1e-6:
            return []

        now = datetime.now(UTC)
        confidence = min(1.0, retired / total) if total else 0.0

        return [
            DbLesson(
                lesson_id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_type=LessonType.CURIOSITY_FOCUS.value,
                target_kind="curiosity_policy",
                target_id="curiosity_intensity",
                summary_text="Adjust curiosity intensity based on outcomes of curiosity-origin goals.",
                proposed_change={
                    "change_type": "threshold_tweak",
                    "field": "curiosity_intensity",
                    "old": old_intensity,
                    "new": new_intensity,
                    "notes": {
                        "retirement_rate": retirement_rate,
                        "total": total,
                        "retired": retired,
                    },
                },
                confidence=float(confidence),
                metrics_basis={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "total": total,
                    "retired": retired,
                    "retirement_rate": retirement_rate,
                },
                scope=LessonScope.THIS_USER.value,
                status=LessonStatus.ACTIVE.value,
                superseded_by=None,
                applied_at=None,
                applied_by=None,
                source_reflection_run_id=run_id,
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                related_goal_ids=[],
                related_trajectory_ids=[],
                related_event_ids=[],
                metadata=None,
                created_at=now,
                updated_at=now,
            )
        ]


__all__ = ["SelfReflectionEngine"]
