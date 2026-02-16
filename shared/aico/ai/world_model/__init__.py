"""
World Model Service

Unified API for querying knowledge graph and semantic memory.
Provides contextual awareness for agency, planning, and curiosity systems.
"""

from .service import WorldModelService
from .models import (
    Entity,
    Project,
    OpenLoop,
    Context,
    UncertainArea,
    UserContext,
    WorldContext,
    # Phase 6.4: Schema Learning, Hypothesis, and Drift Detection
    FieldSchema,
    Schema,
    ValidationResult,
    Hypothesis,
    HypothesisTestResult,
    DriftReport,
    Contradiction,
    ConfidenceDecayConfig,
)

__all__ = [
    "WorldModelService",
    "Entity",
    "Project",
    "OpenLoop",
    "Context",
    "UncertainArea",
    "UserContext",
    "WorldContext",
    # Phase 6.4
    "FieldSchema",
    "Schema",
    "ValidationResult",
    "Hypothesis",
    "HypothesisTestResult",
    "DriftReport",
    "Contradiction",
    "ConfidenceDecayConfig",
]
