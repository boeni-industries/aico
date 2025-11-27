"""
AICO AI Processing Framework

Minimal, clean foundation for AI component integration following AICO's
modular architecture principles. Ready for future AI algorithm implementations.
"""

from .base import ProcessingContext
from .processors import (
    EmotionProcessor,
    PersonalityProcessor, 
    MemoryProcessor,
    EmbodimentProcessor,
    AIProcessorRegistry,
    ai_registry
)
from .utils import detect_language, LanguageDetectionResult

__all__ = [
    'ProcessingContext',
    'EmotionProcessor',
    'PersonalityProcessor',
    'MemoryProcessor', 
    'EmbodimentProcessor',
    'AIProcessorRegistry',
    'ai_registry',
    'detect_language',
    'LanguageDetectionResult',
]
