"""
TTS Engine Factory - Dynamic selection between XTTS, Piper, and Kokoro.

Provides a unified interface for TTS synthesis with engine selection
based on configuration.
"""

from typing import Optional

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger


class TtsFactory:
    """
    Factory for creating TTS handlers based on configuration.
    
    Supports:
    - XTTS: High-quality voice cloning (slower)
    - Piper: Ultra-fast synthesis (no cloning)
    - Kokoro: Fast, high-quality synthesis (no cloning)
    """
    
    @staticmethod
    def create_handler(config_manager: Optional[ConfigurationManager] = None):
        """
        Create appropriate TTS handler based on configuration.
        
        Args:
            config_manager: Configuration manager instance
            
        Returns:
            TTS handler instance (TtsHandler or PiperTtsHandler)
            
        Raises:
            RuntimeError: If engine is not configured or invalid
        """
        logger = get_logger("modelservice", "tts_factory")
        
        if not config_manager:
            error_msg = (
                "\n" + "="*80 + "\n"
                "❌ FATAL: No configuration manager provided to TTS factory!\n"
                "Cannot determine which TTS engine to use.\n"
                "="*80
            )
            logger.error(error_msg)
            print(error_msg, flush=True)
            raise RuntimeError("Configuration manager required for TTS factory")
        
        # Get engine selection from config
        engine = config_manager.get("core.modelservice.tts.engine", None)
        if engine is None:
            error_msg = (
                "\n" + "="*80 + "\n"
                "❌ FATAL: TTS engine not configured!\n"
                "Expected path: core.modelservice.tts.engine\n"
                "Valid options: 'xtts', 'piper', 'kokoro'\n"
                "Check config/defaults/core.yaml\n"
                "="*80
            )
            logger.error(error_msg)
            print(error_msg, flush=True)
            raise RuntimeError("TTS engine not configured at core.modelservice.tts.engine")
        
        logger.info(f"🎤 Creating TTS handler for engine: {engine}")
        
        if engine == "xtts":
            from modelservice.handlers.tts_handler import TtsHandler
            logger.info("✅ Using XTTS (high-quality, voice cloning)")
            return TtsHandler(config_manager)
        
        elif engine == "piper":
            from modelservice.handlers.piper_tts_handler import PiperTtsHandler
            logger.info("✅ Using Piper TTS (ultra-fast, no cloning)")
            return PiperTtsHandler(config_manager)
        
        elif engine == "kokoro":
            from modelservice.handlers.kokoro_tts_handler import KokoroTtsHandler
            logger.info("✅ Using Kokoro TTS (fast, high-quality)")
            return KokoroTtsHandler(config_manager)
        
        else:
            raise RuntimeError(
                f"Invalid TTS engine '{engine}'. "
                f"Valid options: 'xtts', 'piper', 'kokoro'. "
                f"Check modelservice.tts.engine in core.yaml"
            )
