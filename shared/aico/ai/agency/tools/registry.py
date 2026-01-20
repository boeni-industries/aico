from __future__ import annotations

"""Tool Registry for Agency

Central registry for atomic tools used by Agency skills.

This follows the design in WIP-self-healing-skills-tools.md:
- Tools are small, atomic implementations (e.g. connectivity pings)
- Skills are semantic wrappers that reference tools by stable tool_id
- All metadata lives in a registry so selection and orchestration can be
  data-driven instead of hard-coded.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.tools.registry")


# Type alias for async tool handlers
AsyncToolHandler = Callable[..., Awaitable[Dict[str, Any]]]


class ToolParameterType(Enum):
    """Parameter types for tool inputs.

    Kept parallel (but decoupled) from SkillParameterType so tools can expose
    their own low-level input contracts without depending on the skills
    module. This is primarily for CLI / UI introspection.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class ToolParameter:
    """Definition of a tool parameter.

    This mirrors SkillParameter but is scoped to tools. Validation is kept
    simple for now; most connectivity tools are parameterless.
    """

    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Metadata and handler for a single tool.

    The handler implements the runtime behaviour; metadata is used for
    discovery, safety checks, and planner guidance.
    """

    tool_id: str  # e.g. "tool.db.postgres.ping"
    name: str
    description: str

    # Classification / discovery
    domain: str  # e.g. "connectivity", "db", "modelservice"
    backend: str  # e.g. "python", "http", "zmq"
    runtime_context: str = "backend_service"  # where it runs

    capability_tags: List[str] = field(default_factory=list)
    side_effect_tags: List[str] = field(default_factory=list)

    # Optional input contract for introspection / tooling
    parameters: List[ToolParameter] = field(default_factory=list)

    # Safety / resource hints
    safety_level: str = "low"  # low, medium, high, privileged
    resource_profile: str = "tiny"  # tiny, small, medium, large, heavy
    default_timeout_seconds: int = 5

    # Concrete implementation
    handler: AsyncToolHandler = field(default=None)

    # Optional free-form metadata
    extra: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """In-memory registry for tools.

    This is intentionally simple for now (process-local). If/when we move
    to a persisted registry, this class can become a facade over a storage
    layer without affecting callers.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        logger.debug("[TOOL_REGISTRY] Initialized tool registry")

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register or update a tool definition."""
        if tool.tool_id in self._tools:
            logger.warning(
                "[TOOL_REGISTRY] Tool '%s' already registered, overwriting",
                tool.tool_id,
            )
        self._tools[tool.tool_id] = tool
        logger.debug(
            "[TOOL_REGISTRY] Registered tool '%s' (domain=%s, backend=%s)",
            tool.tool_id,
            tool.domain,
            tool.backend,
        )

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def list_all(self) -> List[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_by_domain(self, domain: str) -> List[ToolDefinition]:
        """Return tools that belong to a given domain (e.g. 'connectivity')."""
        return [t for t in self._tools.values() if t.domain == domain]

    def list_by_capability(self, capability: str) -> List[ToolDefinition]:
        """Return tools that advertise a given capability tag."""
        return [
            t for t in self._tools.values()
            if capability in t.capability_tags
        ]

    def tool_exists(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:  # pragma: no cover - trivial
        return tool_id in self._tools


# Simple process-local singleton to make wiring easier without DI framework.
_tool_registry_singleton: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get (or create) the process-local ToolRegistry instance."""
    global _tool_registry_singleton
    if _tool_registry_singleton is None:
        _tool_registry_singleton = ToolRegistry()
    return _tool_registry_singleton
