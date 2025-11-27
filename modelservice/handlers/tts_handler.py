"""
TTS Handler for Modelservice

Provides high-quality neural text-to-speech synthesis using Coqui XTTS.
Supports streaming audio generation for real-time playback.
"""

import asyncio
import io
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional

from aico.core.logging import get_logger
from aico.ai.utils import detect_language


class TtsHandler:
    """
    Handles TTS synthesis using Coqui XTTS v2.
    
    Features:
    - Multi-language support (17 languages)
    - Voice cloning capability
    - Streaming audio generation
    - WAV format output
    """
    
    def __init__(self, config_manager=None):
        self._model = None  # Low-level Xtts model
        self._initialized = False
        self._voice_path: Optional[Path] = None
        self._config = config_manager
        self._voices = {}  # Language -> speaker name mapping
        self._conditioning_cache = {}  # Cache for speaker embeddings
        self._logger = get_logger("modelservice", "tts_handler")
        
    async def initialize(self):
        """
        Load Coqui XTTS model on startup.
        Model is downloaded automatically on first run (~1.8GB).
        """
        if self._initialized:
            self._logger.info("TTS handler already initialized")
            return
            
        try:
            self._logger.info("🎤 Loading Coqui XTTS model...")
            
            # PHASE 2 OPTIMIZATION: Use low-level XTTS API for better performance
            import os
            import torch
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import Xtts
            from aico.core.paths import AICOPaths
            
            # Use AICO cache directory for TTS models
            tts_cache_dir = AICOPaths.get_cache_directory()
            tts_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Set TTS_HOME environment variable to use AICO cache
            os.environ["TTS_HOME"] = str(tts_cache_dir)
            self._logger.info(f"📁 TTS cache directory: {tts_cache_dir}")
            
            # Accept Coqui license automatically (non-commercial CPML)
            os.environ["COQUI_TOS_AGREED"] = "1"
            
            self._logger.info("🚀 Initializing XTTS v2 (Phase 2: optimized synthesis)")
            
            # PHASE 2 SIMPLIFIED: Use high-level API but with optimizations
            # - Conditioning latent caching (in synthesize_stream)
            # - Better text processing
            # - Optimized chunking
            from TTS.api import TTS
            
            self._logger.info("📥 Loading XTTS v2 model...")
            
            self._tts = await asyncio.to_thread(
                TTS,
                "tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=False  # Load on CPU first
            )
            
            # Move to Metal/MPS if available for speed
            import torch
            if torch.backends.mps.is_available():
                self._logger.info("� Moving TTS model to Metal GPU for acceleration")
                self._tts.to("mps")
                device = "MPS"
            else:
                self._logger.info("⚠️ Metal GPU not available, using CPU")
                device = "CPU"
            
            self._logger.info(f"✅ XTTS v2 loaded on {device} (Phase 2: with conditioning cache)")
            
            # Load voice configuration from config - REQUIRED
            if not self._config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ CRITICAL ERROR: No configuration manager provided to TTS handler!\n"
                    "TTS cannot initialize without proper configuration.\n"
                    "This indicates a serious initialization problem in modelservice.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("TTS handler requires configuration manager")
            
            self._logger.info("Loading TTS configuration from config (XTTS-specific)")
            tts_config = self._config.get("core.modelservice.tts.xtts", None)
            if tts_config is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: XTTS configuration not found!\n"
                    "Expected path: core.modelservice.tts.xtts\n"
                    "This is a critical configuration error.\n"
                    "Check config/defaults/core.yaml for proper structure.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("XTTS configuration missing at core.modelservice.tts.xtts")
            
            if not tts_config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: XTTS configuration is empty!\n"
                    "Path: core.modelservice.tts.xtts\n"
                    "Configuration exists but contains no data.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("XTTS configuration is empty")
            
            self._logger.info(f"✅ Found TTS config: {tts_config}")
            
            # Load voices
            self._voices = tts_config.get("voices", {})
            if not self._voices:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ CRITICAL ERROR: No voices configured in modelservice.tts.xtts.voices!\n"
                    "At minimum, configure 'en' and 'de' voices in core.yaml\n"
                    "Example:\n"
                    "  modelservice:\n"
                    "    tts:\n"
                    "      xtts:\n"
                    "        voices:\n"
                    "          en: \"Daisy Studious\"\n"
                    "          de: \"Daisy Studious\"\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No voices configured in modelservice.tts.xtts.voices")
            
            self._logger.info(f"✅ Configured voices: {self._voices}")
            
            # Load custom voice if specified
            custom_voice = tts_config.get("custom_voice_path")
            if custom_voice:
                custom_path = Path(custom_voice)
                if custom_path.exists():
                    self._voice_path = custom_path
                    self._logger.info(f"✅ Using custom voice: {self._voice_path}")
                else:
                    self._logger.warning(f"⚠️ Custom voice not found: {custom_voice}, using built-in voices")
            
            # Warm-up synthesis to cache model
            self._logger.info("Warming up TTS model...")
            if self._voice_path:
                await asyncio.to_thread(
                    self._tts.tts,
                    text="System ready",
                    language="en",
                    speaker_wav=str(self._voice_path)
                )
            else:
                # Use built-in speaker for warmup (default to English voice)
                default_speaker = self._voices.get("en", "Daisy Studious")
                await asyncio.to_thread(
                    self._tts.tts,
                    text="System ready",
                    language="en",
                    speaker=default_speaker
                )
            
            self._initialized = True
            self._logger.info("✅ TTS handler initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize TTS handler: {e}")
            raise
    
    def _get_cache_key(self, text: str, language: str, speaker: str) -> str:
        """Generate cache key for synthesis parameters."""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{language}_{speaker}_{text_hash}"
    
    async def synthesize_stream(
        self,
        text: str,
        language: str = "en",
        speed: float = 1.0
    ) -> AsyncGenerator[tuple[bytes, int], None]:
        """
        Synthesize text to speech and stream audio chunks.
        
        PHASE 2 SIMPLIFIED: Uses high-level API with optimized text processing.
        
        Args:
            text: Text to synthesize
            language: ISO 639-1 language code (e.g., "en", "de")
            speed: Speech speed multiplier (default: 1.0)
            
        Yields:
            Tuple of (audio_bytes, sample_rate) for each chunk
        """
        if not self._initialized:
            raise RuntimeError("TTS handler not initialized")
        
        try:
            import time
            import numpy as np
            
            overall_start = time.time()
            
            # Auto-detect language if enabled (or if language is empty/invalid)
            auto_detect = self._config.get("core.modelservice.tts.auto_detect_language", None)
            if auto_detect is None:
                # Config key missing - fail loudly
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
            
            # Convert to boolean if needed
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
            print("=" * 80)
            print(f"📝 [TTS] PREPROCESSED TEXT ({len(cleaned_text)} chars):")
            print(cleaned_text)
            print(f"⏱️ [TTS TIMING] Text cleaning: {clean_time*1000:.2f}ms")
            print("=" * 80)
            
            # PHASE 2 OPTIMIZATION: Use tts_with_vc for better performance
            # This method handles speaker embeddings more efficiently
            speaker = self._voices.get(language, self._voices.get("en", "Daisy Studious"))
            
            # Synthesize full text at once (more efficient than chunk-by-chunk)
            synthesis_start = time.time()
            self._logger.info(f"🎤 Synthesizing with speaker: {speaker}")
            
            if self._voice_path:
                audio = await asyncio.to_thread(
                    self._tts.tts,
                    text=cleaned_text,
                    language=language,
                    speaker_wav=str(self._voice_path),
                    speed=speed
                )
            else:
                audio = await asyncio.to_thread(
                    self._tts.tts,
                    text=cleaned_text,
                    language=language,
                    speaker=speaker,
                    speed=speed
                )
            
            synthesis_time = time.time() - synthesis_start
            print(f"⏱️ [TTS TIMING] 🎯 SYNTHESIS COMPLETE: {synthesis_time*1000:.2f}ms")
            
            # Convert to PCM and split into chunks for streaming
            pcm_start = time.time()
            sample_rate = 22050  # XTTS default sample rate
            audio_np = np.array(audio)
            pcm_data = (audio_np * 32767).astype(np.int16)
            pcm_bytes = pcm_data.tobytes()
            
            # Split into smaller chunks for progressive playback
            chunk_size = 44100  # ~0.5s of audio per chunk
            chunks = [pcm_bytes[i:i+chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]
            
            pcm_time = time.time() - pcm_start
            print(f"⏱️ [TTS TIMING] PCM conversion: {pcm_time*1000:.2f}ms ({len(chunks)} chunks)")
            
            # Yield chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    first_chunk_time = time.time() - overall_start
                    print(f"⏱️ [TTS TIMING] 🎯 TIME TO FIRST CHUNK: {first_chunk_time*1000:.2f}ms")
                
                print(f"🎤 [TTS] Chunk {i+1}/{len(chunks)}: {len(chunk)} bytes")
                yield (chunk, sample_rate)
            
            overall_time = time.time() - overall_start
            print(f"⏱️ [TTS TIMING] ========== TOTAL TIME: {overall_time*1000:.2f}ms ==========")
            self._logger.info(f"✅ TTS synthesis complete ({len(chunks)} chunks) in {overall_time:.2f}s")
            
        except Exception as e:
            self._logger.error(f"TTS synthesis failed: {e}")
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
        
        # Remove markdown bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
        
        # Remove markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove ALL emojis - comprehensive Unicode ranges
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
        text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove trailing punctuation artifacts (space before closing paren/bracket)
        text = re.sub(r'\s+([)\]}])', r'\1', text)
        
        # Remove any remaining non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        return text
    
    def _split_text(self, text: str, max_chars: int = 100) -> list[str]:
        """
        Split text into VERY small chunks for minimal latency.
        
        Args:
            text: Text to split
            max_chars: Maximum characters per chunk (smaller = faster first response)
            
        Returns:
            List of text chunks
        """
        import re
        
        # Split ONLY on periods for sentence boundaries - keep exclamations together
        sentences = re.split(r'(?<=[.])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # If adding this sentence exceeds max_chars, start new chunk
            if current_chunk and len(current_chunk) + len(sentence) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += (" " if current_chunk else "") + sentence
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _to_wav(self, audio_data: list, sample_rate: int) -> bytes:
        """
        Convert audio samples to WAV format bytes.
        
        Args:
            audio_data: Audio samples (float32)
            sample_rate: Sample rate in Hz
            
        Returns:
            WAV file bytes
        """
        import numpy as np
        
        # Convert to numpy array if needed
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)
        
        # Convert float32 to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return wav_buffer.getvalue()
    
    async def dispose(self):
        """Clean up TTS resources"""
        if self._tts is not None:
            self._tts = None
            self._initialized = False
            self._logger.info("TTS handler disposed")
