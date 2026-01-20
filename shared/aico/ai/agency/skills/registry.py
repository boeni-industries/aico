"""
Skill Registry

Central registry for all available agency skills with discovery and validation.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Type
from enum import Enum

from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.skills.registry")


class SkillParameterType(Enum):
    """Parameter types for skill inputs."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""
    name: str
    type: SkillParameterType
    description: str
    required: bool = True
    default: Any = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate parameter value."""
        if value is None:
            if self.required:
                return False, f"Required parameter '{self.name}' is missing"
            return True, None
        
        # Type validation
        if self.type == SkillParameterType.STRING and not isinstance(value, str):
            return False, f"Parameter '{self.name}' must be a string"
        elif self.type == SkillParameterType.INTEGER and not isinstance(value, int):
            return False, f"Parameter '{self.name}' must be an integer"
        elif self.type == SkillParameterType.FLOAT and not isinstance(value, (int, float)):
            return False, f"Parameter '{self.name}' must be a number"
        elif self.type == SkillParameterType.BOOLEAN and not isinstance(value, bool):
            return False, f"Parameter '{self.name}' must be a boolean"
        elif self.type == SkillParameterType.OBJECT and not isinstance(value, dict):
            return False, f"Parameter '{self.name}' must be an object"
        elif self.type == SkillParameterType.ARRAY and not isinstance(value, list):
            return False, f"Parameter '{self.name}' must be an array"
        
        return True, None


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class Skill(ABC):
    """
    Base class for all agency skills.
    
    Skills are executable actions that the agency can perform to achieve goals.
    Each skill must define its parameters, validation, and execution logic.
    """
    
    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Unique identifier for the skill."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the skill does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[SkillParameter]:
        """List of parameters this skill accepts."""
        pass
    
    @property
    def category(self) -> str:
        """Category of the skill (e.g., 'memory', 'analysis', 'communication')."""
        return "general"
    
    # ------------------------------------------------------------------
    # Optional metadata for registry-driven discovery and planning
    # ------------------------------------------------------------------

    @property
    def capability_tags(self) -> List[str]:
        """High-level capabilities this skill provides (e.g. 'check_health').

        Defaults to empty for legacy skills that have not been annotated yet.
        """

        return []

    @property
    def side_effect_tags(self) -> List[str]:
        """Side-effect classification (e.g. 'reads_database', 'writes_memory').

        Defaults to empty for legacy skills.
        """

        return []

    @property
    def safety_level(self) -> str:
        """Safety level hint (e.g. 'low', 'medium', 'high', 'privileged')."""

        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        """List of tool_ids this skill typically composes/invokes.

        This allows the planner, UI, and observability to understand
        which concrete tools back a given semantic skill. Defaults to an
        empty list for skills that are not yet wired to the ToolRegistry.
        """

        return []
    
    @property
    def timeout_seconds(self) -> int:
        """Default timeout for skill execution."""
        return 30
    
    def validate_inputs(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters.
        
        Returns:
            (is_valid, error_message)
        """
        for param in self.parameters:
            value = input_data.get(param.name)
            is_valid, error = param.validate(value)
            if not is_valid:
                return False, error
        
        return True, None
    
    @abstractmethod
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """
        Execute the skill.
        
        Args:
            user_id: User ID
            input_data: Input parameters
            context: Execution context (goal_id, plan_id, etc.)
            
        Returns:
            SkillResult with output or error
        """
        pass


class SkillRegistry:
    """
    Central registry for all available skills.
    
    Manages skill discovery, registration, and lookup.
    """
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}
        logger.debug("🔧 [SKILL_REGISTRY] Initialized skill registry")
    
    def register(self, skill: Skill) -> None:
        """
        Register a skill.
        
        Args:
            skill: Skill instance to register
        """
        skill_id = skill.skill_id
        
        if skill_id in self._skills:
            logger.warning(
                f"🔧 [SKILL_REGISTRY] Skill '{skill_id}' already registered, overwriting"
            )
        
        self._skills[skill_id] = skill
        
        # Add to category index
        category = skill.category
        if category not in self._categories:
            self._categories[category] = []
        if skill_id not in self._categories[category]:
            self._categories[category].append(skill_id)
        
        logger.debug(
            f"🔧 [SKILL_REGISTRY] Registered skill '{skill_id}' "
            f"({skill.name}) in category '{category}'"
        )
    
    def get(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        return self._skills.get(skill_id)
    
    def list_all(self) -> List[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
    
    def list_by_category(self, category: str) -> List[Skill]:
        """List skills in a category."""
        skill_ids = self._categories.get(category, [])
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]
    
    def get_categories(self) -> List[str]:
        """Get all skill categories."""
        return list(self._categories.keys())
    
    def skill_exists(self, skill_id: str) -> bool:
        """Check if skill exists."""
        return skill_id in self._skills
    
    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get skill metadata."""
        skill = self.get(skill_id)
        if not skill:
            return None
        
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "description": skill.description,
            "category": skill.category,
            "timeout_seconds": skill.timeout_seconds,
            "capability_tags": getattr(skill, "capability_tags", []),
            "side_effect_tags": getattr(skill, "side_effect_tags", []),
            "safety_level": getattr(skill, "safety_level", "low"),
            "implementation_tools": getattr(skill, "implementation_tools", []),
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in skill.parameters
            ],
        }
    
    def __len__(self) -> int:
        """Number of registered skills."""
        return len(self._skills)
    
    def __contains__(self, skill_id: str) -> bool:
        """Check if skill is registered."""
        return skill_id in self._skills
