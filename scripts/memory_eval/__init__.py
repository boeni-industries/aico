"""
AICO Memory Intelligence Evaluator

A comprehensive end-to-end testing framework for AICO's memory system that evaluates
all aspects of memory performance including working memory, semantic memory, episodic
memory, context adherence, entity extraction, and conversation continuity.

This framework leverages existing AICO shared modules and provides stunning visual
output using Typer and Rich for an award-winning user experience.
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

__version__ = "1.0.0"

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
