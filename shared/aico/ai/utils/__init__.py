"""
AICO AI Utilities

Shared utilities for AI processing across the AICO system.
"""

from .language_detection import detect_language, LanguageDetectionResult

__all__ = [
    'detect_language',
    'LanguageDetectionResult',
]
