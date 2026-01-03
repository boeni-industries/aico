"""
Additional coverage tests for lesson_projector.py - targeting uncovered lines.

Focuses on error handling, edge cases, and all conditional branches.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
import uuid

from aico.ai.agency.models import (
    Lesson,
    LessonType,
    TargetKind,
    LessonStatus,
    ProposedChange,
    MetricsBasis,
    ChangeType,
    SelfModelEntry,
    EntityType,
    PerformanceSummary,
    ReflectionRun,
    RunType,
    RunStatus,
)
from aico.ai.agency.lesson_projector import LessonMemoryProjector


class TestLessonProjectorErrorHandling:
    """Tests for error handling and edge cases in LessonMemoryProjector."""
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_memory_with_metrics_basis(self, test_config, test_db, test_user):
        """Test projecting lesson with metrics_basis to memory."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test lesson with metrics",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            metrics_basis=MetricsBasis(
                time_span="7 days",
                sample_size=20,
                outcome_counts={"success": 16, "failure": 4}
            ),
            status=LessonStatus.ACTIVE,
            scope="this_user",
        )
        
        result = await projector.project_lesson_to_memory(lesson)
        
        assert result["success"] is True
        assert result["lesson_id"] == lesson.lesson_id
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_memory_handles_exception(self, test_config, test_db, test_user):
        """Test that project_lesson_to_memory handles exceptions gracefully."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        # Mock _generate_relevance_tags to raise exception
        with patch.object(projector, '_generate_relevance_tags', side_effect=Exception("Test error")):
            lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                user_id=test_user,
                lesson_type=LessonType.SKILL_TUNING,
                target_kind=TargetKind.SKILL,
                target_id="test_skill",
                summary_text="Test",
                proposed_change=ProposedChange(
                    change_type=ChangeType.WEIGHT_TWEAK,
                    field="weight",
                    old=1.0,
                    new=1.2,
                    notes="Test"
                ),
                confidence=0.85,
                status=LessonStatus.ACTIVE,
                scope="this_user",
            )
            
            result = await projector.project_lesson_to_memory(lesson)
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_kg_with_kg_storage(self, test_config, test_db, test_user):
        """Test projecting lesson to KG with KG storage available."""
        mock_kg_storage = Mock()
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=mock_kg_storage)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.PLANNER_TEMPLATE,
            target_id="test_template",
            summary_text="Test planner lesson",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="steps",
                old=1.0,
                new=1.2,
                notes="Add step"
            ),
            confidence=0.9,
            status=LessonStatus.ACTIVE,
            scope="this_user",
        )
        
        result = await projector.project_lesson_to_kg(lesson)
        
        assert result["success"] is True
        assert result["lesson_id"] == lesson.lesson_id
        assert "edges_created" in result
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_kg_with_reflection_run(self, test_config, test_db, test_user):
        """Test projecting lesson to KG with reflection run provenance."""
        mock_kg_storage = Mock()
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=mock_kg_storage)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test lesson",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope="this_user",
        )
        
        reflection_run = ReflectionRun(
            run_id=str(uuid.uuid4()),
            user_id=test_user,
            run_type=RunType.SCHEDULED,
            trigger_reason="test",
            analysis_window_start=datetime.now(UTC),
            analysis_window_end=datetime.now(UTC),
            lessons_generated=1,
            lessons_applied=0,
            started_at=datetime.now(UTC),
            status=RunStatus.COMPLETED,
        )
        
        result = await projector.project_lesson_to_kg(lesson, reflection_run)
        
        # Should succeed with KG storage
        assert result["success"] is True
        assert "edges_created" in result
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_kg_without_kg_storage(self, test_config, test_db, test_user):
        """Test projecting to KG when KG storage is None."""
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=None)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope="this_user",
        )
        
        result = await projector.project_lesson_to_kg(lesson)
        
        assert result["success"] is False
        assert "error" in result
        assert "KG storage not configured" in result["error"]
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_kg_handles_exception(self, test_config, test_db, test_user):
        """Test that project_lesson_to_kg handles exceptions gracefully."""
        mock_kg_storage = Mock()
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=mock_kg_storage)
        
        # Mock _get_target_node_id to raise exception
        with patch.object(projector, '_get_target_node_id', side_effect=Exception("Test error")):
            lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                user_id=test_user,
                lesson_type=LessonType.SKILL_TUNING,
                target_kind=TargetKind.SKILL,
                target_id="test_skill",
                summary_text="Test",
                proposed_change=ProposedChange(
                    change_type=ChangeType.WEIGHT_TWEAK,
                    field="weight",
                    old=1.0,
                    new=1.2,
                    notes="Test"
                ),
                confidence=0.85,
                status=LessonStatus.ACTIVE,
                scope="this_user",
            )
            
            result = await projector.project_lesson_to_kg(lesson)
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_project_self_model_to_kg_without_kg_storage(self, test_config, test_db, test_user):
        """Test projecting self-model when KG storage is None."""
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=None)
        
        entry = SelfModelEntry(
            model_id=str(uuid.uuid4()),
            user_id=test_user,
            entity_type=EntityType.SKILL,
            entity_id="test_skill",
            performance_summary=PerformanceSummary(
                success_rate=0.8,
                avg_completion_time=120.0,
                total_attempts=25,
                recent_trend="improving"
            ),
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=25,
            confidence=0.85,
            last_updated=datetime.now(UTC),
        )
        
        result = await projector.project_self_model_to_kg(entry)
        
        assert result["success"] is False
        assert "error" in result
        assert "KG storage not configured" in result["error"]
    
    @pytest.mark.asyncio
    async def test_project_self_model_to_kg_with_kg_storage(self, test_config, test_db, test_user):
        """Test projecting self-model with KG storage available."""
        mock_kg_storage = Mock()
        projector = LessonMemoryProjector(test_config, test_db, kg_storage=mock_kg_storage)
        
        entry = SelfModelEntry(
            model_id=str(uuid.uuid4()),
            user_id=test_user,
            entity_type=EntityType.GOAL_TYPE,
            entity_id="project",
            performance_summary=PerformanceSummary(
                success_rate=0.75,
                avg_completion_time=3600.0,
                total_attempts=40,
                recent_trend="stable"
            ),
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
            sample_size=40,
            confidence=0.9,
            last_updated=datetime.now(UTC),
        )
        
        result = await projector.project_self_model_to_kg(entry)
        
        assert result["success"] is True
        assert result["model_id"] == entry.model_id
    
    
    @pytest.mark.asyncio
    async def test_query_active_lessons_with_target_id(self, test_config, test_db, test_user):
        """Test querying lessons with target_id filter."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        # Create and store a lesson
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="specific_skill",
            summary_text="Test lesson",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope="this_user",
        )
        
        await projector.lesson_store.create_lesson(lesson)
        
        # Query with target_id
        results = await projector.query_active_lessons(
            user_id=test_user,
            target_kind=TargetKind.SKILL,
            target_id="specific_skill",
            limit=5
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_query_active_lessons_error(self, test_config, test_db, test_user):
        """Test error handling in query_active_lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        # Mock lesson_store to raise error
        with patch.object(projector.lesson_store, 'get_active_lessons', side_effect=Exception("DB error")):
            results = await projector.query_active_lessons(test_user)
            
            # Should return empty list on error
            assert results == []


class TestRelevanceTagGeneration:
    """Tests for relevance tag generation for all lesson types."""
    
    @pytest.mark.asyncio
    async def test_generate_tags_skill_tuning(self, test_config, test_db):
        """Test tag generation for SKILL_TUNING lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Mock()
        lesson.lesson_type = LessonType.SKILL_TUNING
        lesson.target_kind = TargetKind.SKILL
        lesson.target_id = "test_skill"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert "skill_learning" in tags
        assert "skill:test_skill" in tags
    
    @pytest.mark.asyncio
    async def test_generate_tags_planner_heuristic(self, test_config, test_db):
        """Test tag generation for PLANNER_HEURISTIC lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Mock()
        lesson.lesson_type = LessonType.PLANNER_HEURISTIC
        lesson.target_kind = TargetKind.PLANNER_TEMPLATE
        lesson.target_id = "test_template"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert "goal_learning" in tags
        assert "planning" in tags
    
    @pytest.mark.asyncio
    async def test_generate_tags_persona_style(self, test_config, test_db):
        """Test tag generation for PERSONA_STYLE lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Mock()
        lesson.lesson_type = LessonType.PERSONA_STYLE
        lesson.target_kind = TargetKind.PERSONA_TRAIT
        lesson.target_id = "formality"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert "persona" in tags
        assert "interaction_style" in tags
    
    @pytest.mark.asyncio
    async def test_generate_tags_policy_suggestion(self, test_config, test_db):
        """Test tag generation for POLICY_SUGGESTION lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Mock()
        lesson.lesson_type = LessonType.POLICY_SUGGESTION
        lesson.target_kind = TargetKind.POLICY_RULE
        lesson.target_id = "test_policy"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert "policy" in tags
        assert "values_ethics" in tags
    
    @pytest.mark.asyncio
    async def test_generate_tags_curiosity_focus(self, test_config, test_db):
        """Test tag generation for CURIOSITY_FOCUS lessons."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        lesson = Mock()
        lesson.lesson_type = LessonType.CURIOSITY_FOCUS
        lesson.target_kind = TargetKind.CURIOSITY_POLICY
        lesson.target_id = "test_curiosity"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert "curiosity" in tags
        assert "exploration" in tags


class TestTargetNodeIdGeneration:
    """Tests for target node ID generation for all target kinds."""
    
    @pytest.mark.asyncio
    async def test_get_node_id_skill(self, test_config, test_db):
        """Test node ID for SKILL target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.SKILL, "my_skill")
        assert node_id == "skill:my_skill"
    
    @pytest.mark.asyncio
    async def test_get_node_id_planner_template(self, test_config, test_db):
        """Test node ID for PLANNER_TEMPLATE target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.PLANNER_TEMPLATE, "template1")
        assert node_id == "planner_template:template1"
    
    @pytest.mark.asyncio
    async def test_get_node_id_arbiter_weight(self, test_config, test_db):
        """Test node ID for ARBITER_WEIGHT target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.ARBITER_WEIGHT, "priority")
        assert node_id == "arbiter_weight:priority"
    
    @pytest.mark.asyncio
    async def test_get_node_id_curiosity_policy(self, test_config, test_db):
        """Test node ID for CURIOSITY_POLICY target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.CURIOSITY_POLICY, "policy1")
        assert node_id == "curiosity_policy:policy1"
    
    @pytest.mark.asyncio
    async def test_get_node_id_persona_trait(self, test_config, test_db):
        """Test node ID for PERSONA_TRAIT target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.PERSONA_TRAIT, "friendliness")
        assert node_id == "persona_trait:friendliness"
    
    @pytest.mark.asyncio
    async def test_get_node_id_policy_rule(self, test_config, test_db):
        """Test node ID for POLICY_RULE target."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        node_id = projector._get_target_node_id(TargetKind.POLICY_RULE, "rule1")
        assert node_id == "policy_rule:rule1"
    
    @pytest.mark.asyncio
    async def test_get_node_id_unknown_target(self, test_config, test_db):
        """Test node ID for unknown target kind returns None."""
        projector = LessonMemoryProjector(test_config, test_db)
        
        # Create a mock unknown target kind
        unknown_kind = Mock()
        unknown_kind.value = "unknown"
        
        node_id = projector._get_target_node_id(unknown_kind, "test")
        assert node_id is None
