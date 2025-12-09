"""
World Model Service

Unified API for querying knowledge graph and semantic memory to provide
contextual awareness for agency, planning, and curiosity systems.

Phase 2: Basic queries for entities, projects, open loops, and contexts.
"""

from .service import WorldModelService
from .models import (
    UserContext,
    OpenLoop,
    WorldContext,
    Entity,
    Project,
    Context,
    UncertainArea,
)

__all__ = [
    "WorldModelService",
    "UserContext",
    "OpenLoop",
    "WorldContext",
    "Entity",
    "Project",
    "Context",
    "UncertainArea",
]
