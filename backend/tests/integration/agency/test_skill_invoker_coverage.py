"""
Skill Invoker Coverage Tests

Tests for SkillInvoker to improve coverage of skill_invoker.py.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import asyncio

from aico.ai.agency.skill_invoker import SkillInvoker
from aico.ai.agency.skills.registry import SkillRegistry, Skill, SkillResult, SkillParameter, SkillParameterType


class TestSkill(Skill):
    """Test skill implementation for testing."""
    
    def __init__(self, skill_id_val="test_skill", should_fail=False, delay=0):
        self._skill_id = skill_id_val
        self._name = "Test Skill"
        self._description = "A test skill"
        self._parameters = [
            SkillParameter(
                name="test_param",
                type=SkillParameterType.STRING,
                description="Test parameter",
                required=True
            )
        ]
        self.should_fail = should_fail
        self.delay = delay
        self.execution_count = 0
    
    @property
    def skill_id(self):
        return self._skill_id
    
    @property
    def name(self):
        return self._name
    
    @property
    def description(self):
        return self._description
    
    @property
    def parameters(self):
        return self._parameters
    
    async def execute(self, user_id, input_data, context):
        """Execute the test skill."""
        self.execution_count += 1
        
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise Exception("Test skill failure")
        
        return SkillResult(
            success=True,
            output={
                "result": f"Success with {input_data.get('test_param', 'no param')}",
                "execution_count": self.execution_count
            }
        )


class TestOptionalDefaultsSkill(Skill):
    """Test skill with optional parameters and defaults for normalization tests."""

    @property
    def skill_id(self):
        return "test_optional_defaults"

    @property
    def name(self):
        return "Test Optional Defaults"

    @property
    def description(self):
        return "Test optional parameter normalization"

    @property
    def parameters(self):
        return [
            SkillParameter(
                name="required_param",
                type=SkillParameterType.STRING,
                description="Required",
                required=True,
            ),
            SkillParameter(
                name="optional_list",
                type=SkillParameterType.ARRAY,
                description="Optional list",
                required=False,
                default=[],
            ),
        ]

    async def execute(self, user_id, input_data, context):
        return SkillResult(
            success=True,
            output={
                "optional_list": input_data.get("optional_list"),
            },
        )


@pytest.mark.asyncio
class TestSkillInvoker:
    """Test suite for SkillInvoker."""
    
    async def test_invoke_skill_success(self, test_db, test_user):
        """Test successful skill invocation."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="test_skill"))

        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
        )
        
        # Act
        result = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={"test_param": "hello"}
        )
        
        # Assert
        assert result["success"] is True
        assert "invocation_id" in result
        # SkillResult.output contains the actual output dict
        assert result["output"]["output"]["result"] == "Success with hello"
        assert result["duration_ms"] >= 0

    async def test_optional_defaults_normalized_when_none(self, test_db, test_user):
        """Optional params set to None should be replaced with their defaults before validation."""
        registry = SkillRegistry()
        registry.register(TestOptionalDefaultsSkill())

        with patch.object(SkillInvoker, '_record_invocation_start', new_callable=AsyncMock):
            with patch.object(SkillInvoker, '_record_invocation_complete', new_callable=AsyncMock):
                invoker = SkillInvoker(
                    skill_registry=registry,
                    default_timeout=5,
                    max_retries=0,
                )

                result = await invoker.invoke_skill(
                    skill_id="test_optional_defaults",
                    user_id=test_user,
                    input_data={"required_param": "ok", "optional_list": None},
                )

                assert result["success"] is True
                assert result["output"]["output"]["optional_list"] == []

    async def test_invoke_skill_not_found(self, test_db, test_user):
        """Test invoking non-existent skill."""
        # Arrange
        registry = SkillRegistry()
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
            session_factory=session_factory
        )
        
        # Act
        result = await invoker.invoke_skill(
            skill_id="nonexistent_skill",
            user_id=test_user,
            input_data={"test_param": "hello"}
        )
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
        assert result["duration_ms"] == 0
    
    async def test_invoke_skill_validation_failure(self, test_db, test_user):
        """Test skill invocation with invalid inputs."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="test_skill"))
        
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
            session_factory=session_factory
        )
        
        # Act - missing required test_param
        result = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={}
        )
        
        # Assert
        assert result["success"] is False
        assert "error" in result
    
    async def test_invoke_skill_execution_failure(self, test_db, test_user):
        """Test skill that fails during execution."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="failing_skill", should_fail=True))
        
        # Patch database recording to avoid foreign key constraints
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        with patch.object(SkillInvoker, '_record_invocation_start', new_callable=AsyncMock):
            with patch.object(SkillInvoker, '_record_invocation_complete', new_callable=AsyncMock):
                invoker = SkillInvoker(
                    skill_registry=registry,
                    default_timeout=5,
                    max_retries=3,
                    session_factory=session_factory
                )
                
                # Act
                result = await invoker.invoke_skill(
                    skill_id="failing_skill",
                    user_id=test_user,
                    input_data={"test_param": "test"}
                )
                
                # Assert
                assert result["success"] is False
                assert "error" in result
                assert "Test skill failure" in result["error"]
    
    async def test_invoke_skill_with_context(self, test_db, test_user):
        """Test skill invocation with context."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="test_skill"))
        
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
            session_factory=session_factory
        )
        
        context = {
            "execution_id": "exec-123",
            "step_id": "step-456",
            "metadata": {"key": "value"}
        }
        
        # Act
        result = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={"test_param": "test"},
            context=context
        )
        
        # Assert
        assert result["success"] is True
    
    async def test_invoke_skill_with_custom_timeout(self, test_db, test_user):
        """Test skill invocation with custom timeout."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="slow_skill", delay=0.1))
        
        # Patch database recording to avoid foreign key constraints
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        with patch.object(SkillInvoker, '_record_invocation_start', new_callable=AsyncMock):
            with patch.object(SkillInvoker, '_record_invocation_complete', new_callable=AsyncMock):
                invoker = SkillInvoker(
                    skill_registry=registry,
                    default_timeout=5,
                    max_retries=2,
                    session_factory=session_factory
                )
                
                # Act
                result = await invoker.invoke_skill(
                    skill_id="slow_skill",
                    user_id=test_user,
                    input_data={"test_param": "test"},
                    timeout=1
                )
                
                # Assert - should succeed since delay is 0.1s
                assert result["success"] is True
                assert result["duration_ms"] >= 100
    
    async def test_invoke_skill_returns_unique_ids(self, test_db, test_user):
        """Test that each invocation gets unique ID."""
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="test_skill"))
        
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
            session_factory=session_factory
        )
        
        # Act
        result1 = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={"test_param": "test1"}
        )
        
        result2 = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={"test_param": "test2"}
        )
        
        # Assert
        assert result1["invocation_id"] != result2["invocation_id"]
        assert isinstance(result1["invocation_id"], str)
        assert isinstance(result2["invocation_id"], str)
    
    async def test_invoke_skill_with_empty_context(self, test_db, test_user):
        """Test skill invocation with None context."""
        from aico.data.postgres.connection import get_session_factory
        
        # Arrange
        registry = SkillRegistry()
        registry.register(TestSkill(skill_id_val="test_skill"))
        
        session_factory = await get_session_factory()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=5,
            max_retries=2,
            session_factory=session_factory
        )
        
        # Act
        result = await invoker.invoke_skill(
            skill_id="test_skill",
            user_id=test_user,
            input_data={"test_param": "test"},
            context=None
        )
        
        # Assert
        assert result["success"] is True


class TestSkillInvokerInitialization:
    """Test SkillInvoker initialization."""
    
    def test_initialization_with_defaults(self, test_db):
        """Test initialization with default parameters."""
        registry = SkillRegistry()
        invoker = SkillInvoker(skill_registry=registry)
        
        assert invoker.skill_registry == registry
        assert invoker.default_timeout == 30
        assert invoker.max_retries == 2
    
    def test_initialization_with_custom_params(self, test_db):
        """Test initialization with custom parameters."""
        registry = SkillRegistry()
        invoker = SkillInvoker(
            skill_registry=registry,
            default_timeout=60,
            max_retries=5
        )
        
        assert invoker.default_timeout == 60
        assert invoker.max_retries == 5
    
    def test_initialization_with_custom_logger(self, test_db):
        """Test initialization with custom logger."""
        registry = SkillRegistry()
        custom_logger = MagicMock()
        
        invoker = SkillInvoker(
            skill_registry=registry,
            logger=custom_logger
        )
        
        assert invoker.logger == custom_logger
