"""AICO memory benchmark suite.

This package provides an end-to-end benchmark runner that drives the live backend via
the API gateway using transport encryption and JWT authentication.

The benchmark focuses on context/working-memory quality by scoring the assistant's
responses against scenario expectations, without reading internal storage directly.
"""

import sys
from pathlib import Path

# Add shared path for AICO modules
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from .evaluator import MemoryIntelligenceEvaluator
from .scenarios import ConversationScenario, ScenarioLibrary
from .metrics import MemoryMetrics, EvaluationResult
from .reporters import RichReporter, JSONReporter, DetailedReporter

__version__ = "2.0.0"

__all__ = [
    "MemoryIntelligenceEvaluator",
    "ConversationScenario", 
    "ScenarioLibrary",
    "MemoryMetrics",
    "EvaluationResult",
    "RichReporter",
    "JSONReporter", 
    "DetailedReporter"
]
