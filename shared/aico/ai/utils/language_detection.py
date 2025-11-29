"""
Language Detection Utility

Ultra-fast, accurate language detection using FastText.
Optimized for minimal runtime overhead and high accuracy.

Based on Facebook's FastText language identification model:
- 217 languages supported
- ~95% accuracy
- <1ms inference time
- 1MB model size (lite version)
"""

from dataclasses import dataclass
from typing import Literal, Optional
import threading


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: str  # ISO 639-1 or ISO 639-3 code
    confidence: float  # 0.0 to 1.0
    
    @property
    def is_confident(self) -> bool:
        """Check if detection confidence is high (>0.7)."""
        return self.confidence > 0.7


class _LanguageDetector:
    """
    Singleton language detector using FastText.
    
    Lazy-loads the model on first use to avoid startup overhead.
    Thread-safe for concurrent access.
    """
    
    _instance: Optional['_LanguageDetector'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize detector (model loaded on first use)."""
        self._model = None
        self._model_lock = threading.Lock()
    
    def _ensure_model_loaded(self):
        """Lazy-load FastText model on first use."""
        if self._model is not None:
            return
        
        with self._model_lock:
            # Double-check after acquiring lock
            if self._model is not None:
                return
            
            try:
                from fast_langdetect import detect as ft_detect
                
                # Store the detection function
                self._detect_fn = ft_detect
                self._model = True  # Mark as loaded
                
            except ImportError as e:
                raise RuntimeError(
                    "fast-langdetect not installed. "
                    "Install with: uv sync"
                ) from e
    
    def detect(self, text: str, fallback: str = "en") -> LanguageDetectionResult:
        """
        Detect language from text.
        
        Args:
            text: Text to analyze
            fallback: Language code to return if detection fails (default: "en")
            
        Returns:
            LanguageDetectionResult with language code and confidence
        """
        # Ensure model is loaded
        self._ensure_model_loaded()
        
        # Handle empty or whitespace-only text
        if not text or not text.strip():
            return LanguageDetectionResult(language=fallback, confidence=0.0)
        
        try:
            # FastText detection returns list of dicts: [{'lang': 'en', 'score': 0.98}, ...]
            # Use model='lite' for offline, fast detection
            results = self._detect_fn(text, model='lite', k=1)
            
            if not results:
                return LanguageDetectionResult(language=fallback, confidence=0.0)
            
            # Get top result
            top_result = results[0]
            lang_code = top_result.get('lang', fallback)
            confidence = top_result.get('score', 0.0)
            
            # Convert ISO 639-3 to ISO 639-1 for common languages
            lang_code = self._normalize_language_code(lang_code)
            
            return LanguageDetectionResult(
                language=lang_code,
                confidence=float(confidence)
            )
            
        except Exception as e:
            # Detection failed - log and return fallback
            import logging
            logging.warning(f"Language detection failed: {e}")
            return LanguageDetectionResult(language=fallback, confidence=0.0)
    
    @staticmethod
    def _normalize_language_code(code: str) -> str:
        """
        Normalize language code to ISO 639-1 (2-letter) when possible.
        
        Args:
            code: ISO 639-1 or ISO 639-3 language code
            
        Returns:
            Normalized 2-letter code when available
        """
        # FastText returns ISO 639-3 codes, map common ones to ISO 639-1
        iso_639_3_to_639_1 = {
            'deu': 'de',  # German
            'eng': 'en',  # English
            'fra': 'fr',  # French
            'spa': 'es',  # Spanish
            'ita': 'it',  # Italian
            'por': 'pt',  # Portuguese
            'nld': 'nl',  # Dutch
            'pol': 'pl',  # Polish
            'rus': 'ru',  # Russian
            'jpn': 'ja',  # Japanese
            'kor': 'ko',  # Korean
            'zho': 'zh',  # Chinese
            'ara': 'ar',  # Arabic
            'hin': 'hi',  # Hindi
            'tur': 'tr',  # Turkish
            'ces': 'cs',  # Czech
            'hun': 'hu',  # Hungarian
        }
        
        # If already 2-letter, return as-is
        if len(code) == 2:
            return code.lower()
        
        # Convert 3-letter to 2-letter if mapping exists
        return iso_639_3_to_639_1.get(code.lower(), code.lower())
    
    @classmethod
    def get_instance(cls) -> '_LanguageDetector':
        """Get singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance


def detect_language(
    text: str,
    fallback: str = "en"
) -> LanguageDetectionResult:
    """
    Detect language from text using FastText.
    
    This is the main entry point for language detection across AICO.
    
    Features:
    - Ultra-fast: <1ms inference time
    - Accurate: ~95% accuracy
    - Lightweight: 1MB model size
    - 217 languages supported
    - Thread-safe
    
    Args:
        text: Text to analyze
        fallback: Language code to return if detection fails (default: "en")
        
    Returns:
        LanguageDetectionResult with language code and confidence
        
    Example:
        >>> result = detect_language("Hello world!")
        >>> result.language
        'en'
        >>> result.confidence
        0.98
        >>> result.is_confident
        True
        
        >>> result = detect_language("Guten Tag!")
        >>> result.language
        'de'
        >>> result.confidence
        0.95
    """
    detector = _LanguageDetector.get_instance()
    return detector.detect(text, fallback=fallback)
