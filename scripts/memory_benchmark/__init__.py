"""
AICO Memory Benchmark Suite (V2)

Performance benchmarking framework for AICO's fact-centric memory system that measures
GLiNER + LLM fact extraction performance, 2-tier storage efficiency (LMDB + ChromaDB), 
context adherence accuracy, entity extraction precision, and conversation continuity.

This framework provides comprehensive memory system performance analysis with stunning
visual output using Rich for tracking memory improvements over time.
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
