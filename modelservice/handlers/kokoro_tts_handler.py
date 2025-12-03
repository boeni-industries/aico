"""
Kokoro TTS Handler - Fast, high-quality neural TTS synthesis.

Kokoro is a lightweight 82M parameter TTS model with excellent quality.
Features ONNX Runtime for fast CPU/GPU inference and word-level timestamps.
"""

import asyncio
import io
import os
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.ai.utils import detect_language


class KokoroTtsHandler:
    """
    Kokoro TTS handler for fast, high-quality speech synthesis.
    
    Features:
    - Fast synthesis with ONNX Runtime (~1-3s on CPU)
    - 82M parameter model (~300MB full, ~80MB quantized)
    - High-quality natural voices
    - Automatic language detection
    - Streaming audio output
    - Word-level timestamps (for lip-sync)
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize Kokoro TTS handler.
        
        Args:
            config_manager: Configuration manager instance
        """
        self._pipeline = None
        self._initialized = False
        self._config = config_manager
        self._voices = {}  # Language -> voice name mapping
        self._model_variant = "full"  # full or quantized
        self._use_gpu = False
        self._logger = get_logger("modelservice", "kokoro_tts_handler")
        
    async def initialize(self):
        """Initialize Kokoro TTS system."""
        try:
            self._logger.info("🚀 Initializing Kokoro TTS (fast, high-quality synthesis)")
            
            # Import Kokoro (lazy import to avoid loading if not used)
            try:
                from kokoro import KPipeline
            except ImportError:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: kokoro package not installed!\n"
                    "Please install: pip install kokoro\n"
                    "Or run: uv sync --extra modelservice\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("kokoro package not installed")
            
            # Get TTS configuration
            if not self._config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: No configuration manager provided to Kokoro TTS handler!\n"
                    "This indicates a serious initialization problem.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No configuration manager provided to Kokoro TTS handler")
            
            tts_config = self._config.get("core.modelservice.tts.kokoro", None)
            if tts_config is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Kokoro TTS configuration not found!\n"
                    "Expected path: core.modelservice.tts.kokoro\n"
                    "Check config/defaults/core.yaml for proper structure.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No Kokoro TTS configuration found in core.modelservice.tts.kokoro")
            
            if not tts_config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Kokoro TTS configuration is empty!\n"
                    "Path: core.modelservice.tts.kokoro\n"
                    "Configuration exists but contains no data.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("Kokoro TTS configuration is empty")
            
            self._logger.info(f"✅ Found Kokoro config: {tts_config}")
            
            # Load voice configuration
            self._voices = tts_config.get("voices", None)
            if self._voices is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: No voices section in Kokoro configuration!\n"
                    "Expected path: core.modelservice.tts.kokoro.voices\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No voices configured for Kokoro TTS")
            
            if not self._voices:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Voices configuration is empty!\n"
                    "Path: core.modelservice.tts.kokoro.voices\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("Voices configuration is empty")
            
            self._logger.info(f"✅ Loaded voice mappings: {self._voices}")
            
            # Load model variant and GPU settings
            self._model_variant = tts_config.get("model_variant", "full")
            self._use_gpu = tts_config.get("use_gpu", False)
            
            self._logger.info(f"📦 Model variant: {self._model_variant}")
            self._logger.info(f"🎮 GPU acceleration: {self._use_gpu}")
            
            # Set up Kokoro cache directory (following AICO patterns)
            kokoro_cache_dir = AICOPaths.get_cache_directory() / "kokoro"
            kokoro_cache_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"📁 Kokoro cache directory: {kokoro_cache_dir}")
            
            # Set environment variable for Kokoro model cache
            # Kokoro uses Hugging Face Hub, which respects HF_HOME (not XDG_CACHE_HOME)
            # Models will be downloaded to: {HF_HOME}/hub/models--hexgrad--Kokoro-82M/
            os.environ["HF_HOME"] = str(kokoro_cache_dir)
            
            # Initialize Kokoro pipeline
            # Note: KPipeline auto-downloads models on first run via Hugging Face Hub
            self._logger.info("📥 Loading Kokoro pipeline (may download models on first run)...")
            
            # Determine language code (Kokoro uses 'a' for American English by default)
            # We'll initialize with 'a' and switch languages per-request
            self._pipeline = await asyncio.to_thread(
                KPipeline,
                lang_code='a'  # American English
            )
            
            self._logger.info("✅ Kokoro pipeline loaded successfully")
            
            # Warm up with a test synthesis
            self._logger.info("🔥 Warming up Kokoro with test synthesis...")
            test_voice = self._voices.get("en", "af_bella")
            
            def warmup():
                """Warm up synthesis in thread."""
                generator = self._pipeline("Hello", voice=test_voice)
                for _, _, audio in generator:
                    break  # Just generate first chunk
                return True
            
            await asyncio.to_thread(warmup)
            
            self._initialized = True
            self._logger.info("✅ Kokoro TTS initialization complete")
            print("=" * 80)
            print("✅ KOKORO TTS READY")
            print(f"   Model: Kokoro-82M ({self._model_variant})")
            print(f"   Voices: {', '.join(self._voices.keys())}")
            print(f"   GPU: {'Enabled' if self._use_gpu else 'CPU only'}")
            print("=" * 80)
            
        except Exception as e:
            self._logger.error(f"Failed to initialize Kokoro TTS: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def synthesize_stream(
        self,
        text: str,
        language: str = "en",
        speed: float = 1.0
    ) -> AsyncGenerator[tuple[bytes, int], None]:
        """
        Synthesize text to speech and stream audio chunks.
        
        Args:
            text: Text to synthesize
            language: ISO 639-1 language code (e.g., "en", "de") - auto-detected if not provided
            speed: Speech speed multiplier (default: 1.0)
            
        Yields:
            Tuple of (audio_bytes, sample_rate) for each chunk
        """
        try:
            import time
            import numpy as np
            import soundfile as sf
            
            overall_start = time.time()
            
            # Auto-detect language if enabled (or if language is empty/invalid)
            auto_detect = self._config.get("core.modelservice.tts.auto_detect_language", None)
            if auto_detect is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: auto_detect_language configuration missing!\n"
                    "Expected path: core.modelservice.tts.auto_detect_language\n"
                    "This must be explicitly set to true or false.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("auto_detect_language configuration missing")
            
            auto_detect = bool(auto_detect)
            
            # Debug logging
            print(f"🔍 [DEBUG] auto_detect={auto_detect}, language='{language}', language.strip()='{language.strip() if language else 'None'}'", flush=True)
            self._logger.info(f"🔍 [DEBUG] auto_detect={auto_detect}, language='{language}'")
            
            if auto_detect or not language or language.strip() == "":
                # Use 'en' as fallback if detection fails
                fallback_lang = language if language and language.strip() else "en"
                result = detect_language(text, fallback=fallback_lang)
                self._logger.info(f"🔍 Detected language: {result.language} (confidence: {result.confidence:.2f})")
                print(f"🔍 Detected language: {result.language} (confidence: {result.confidence:.2f})", flush=True)
                language = result.language
            else:
                print(f"🔍 [DEBUG] Skipping detection - using provided language: {language}", flush=True)
                self._logger.info(f"🔍 [DEBUG] Skipping detection - using provided language: {language}")
            
            # Clean markdown and special formatting from text
            clean_start = time.time()
            cleaned_text = self._clean_text_for_tts(text)
            clean_time = time.time() - clean_start
            self._logger.info(f"🎤 Original text: {len(text)} chars, cleaned: {len(cleaned_text)} chars")
            
            self._logger.info(f"🎤 Synthesizing with Kokoro (language: {language})")
            print("=" * 80)
            print(f"📝 [KOKORO TTS] CLEANED TEXT ({len(cleaned_text)} chars):")
            print(cleaned_text)
            print(f"⏱️ [KOKORO TIMING] Text cleaning: {clean_time*1000:.2f}ms")
            print("=" * 80)
            
            # Get voice for language
            voice_name = self._voices.get(language)
            if not voice_name:
                self._logger.warning(f"No Kokoro voice configured for language '{language}', using English")
                voice_name = self._voices.get("en", "af_bella")
                language = "en"
            
            self._logger.info(f"🎤 Using voice: {voice_name}")
            
            # Synthesize audio
            synthesis_start = time.time()
            
            def synthesize():
                """Synthesize audio in thread."""
                # Kokoro's pipeline returns generator of (graphemes, phonemes, audio)
                audio_chunks = []
                
                for gs, ps, audio in self._pipeline(cleaned_text, voice=voice_name):
                    # audio is numpy array of float32 samples
                    audio_chunks.append(audio)
                
                # Concatenate all chunks
                if audio_chunks:
                    full_audio = np.concatenate(audio_chunks)
                    return full_audio
                else:
                    return np.array([], dtype=np.float32)
            
            audio_np = await asyncio.to_thread(synthesize)
            
            synthesis_time = time.time() - synthesis_start
            print(f"⏱️ [KOKORO TIMING] 🎯 SYNTHESIS COMPLETE: {synthesis_time*1000:.2f}ms")
            
            # Convert to PCM int16 and prepare for streaming
            pcm_start = time.time()
            sample_rate = 24000  # Kokoro outputs at 24kHz
            
            # Convert float32 [-1, 1] to int16 [-32768, 32767]
            pcm_data = (audio_np * 32767).astype(np.int16)
            pcm_bytes = pcm_data.tobytes()
            
            # Split into smaller chunks for progressive playback
            chunk_size = 48000  # ~0.5s of audio per chunk at 24kHz
            chunks = [pcm_bytes[i:i+chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]
            
            pcm_time = time.time() - pcm_start
            print(f"⏱️ [KOKORO TIMING] PCM conversion: {pcm_time*1000:.2f}ms ({len(chunks)} chunks)")
            
            # Yield chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    first_chunk_time = time.time() - overall_start
                    print(f"⏱️ [KOKORO TIMING] 🎯 TIME TO FIRST CHUNK: {first_chunk_time*1000:.2f}ms")
                
                print(f"🎤 [KOKORO] Chunk {i+1}/{len(chunks)}: {len(chunk)} bytes")
                yield (chunk, sample_rate)
            
            overall_time = time.time() - overall_start
            print(f"⏱️ [KOKORO TIMING] ========== TOTAL TIME: {overall_time*1000:.2f}ms ==========")
            self._logger.info(f"✅ Kokoro synthesis complete ({len(chunks)} chunks) in {overall_time:.2f}s")
            
        except Exception as e:
            self._logger.error(f"Kokoro synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for TTS by removing markdown and special formatting.
        
        Args:
            text: Raw text with markdown
            
        Returns:
            Cleaned text suitable for TTS
        """
        import re
        
        # Remove markdown headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove markdown bold/italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)  # Bold+italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)      # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)          # Italic
        text = re.sub(r'__(.+?)__', r'\1', text)          # Bold (underscore)
        text = re.sub(r'_(.+?)_', r'\1', text)            # Italic (underscore)
        
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove markdown code blocks
        text = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove markdown lists
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove blockquotes
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        
        # Remove horizontal rules
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
        text = re.sub(r' {2,}', ' ', text)      # Max 1 space
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
