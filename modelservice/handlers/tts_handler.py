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
        self._tts = None
        self._initialized = False
        self._voice_path: Optional[Path] = None
        self._config = config_manager
        self._voices = {}  # Language -> speaker name mapping
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
            
            # Import TTS here to avoid loading if not needed
            import os
            from TTS.api import TTS
            from aico.core.paths import AICOPaths
            
            # Use AICO cache directory for TTS models
            tts_cache_dir = AICOPaths.get_cache_directory()
            tts_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Set TTS_HOME environment variable to use AICO cache
            os.environ["TTS_HOME"] = str(tts_cache_dir)
            self._logger.info(f"📁 TTS cache directory: {tts_cache_dir}")
            
            # Accept Coqui license automatically (non-commercial CPML)
            os.environ["COQUI_TOS_AGREED"] = "1"
            
            # Load XTTS v2 model (auto-downloads on first run)
            self._tts = await asyncio.to_thread(
                TTS,
                "tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=False  # Use CPU for compatibility
            )
            
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
            
            self._logger.info("Loading TTS configuration from core.yaml...")
            tts_config = self._config.get("core.modelservice.tts", {})
            
            if not tts_config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ CRITICAL ERROR: No 'modelservice.tts' section found in core.yaml!\n"
                    "Expected configuration path: modelservice.tts\n"
                    "TTS cannot initialize without voice configuration.\n"
                    "Please check config/defaults/core.yaml\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("Missing modelservice.tts configuration in core.yaml")
            
            self._logger.info(f"✅ Found TTS config: {tts_config}")
            
            # Load voices
            self._voices = tts_config.get("voices", {})
            if not self._voices:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ CRITICAL ERROR: No voices configured in modelservice.tts.voices!\n"
                    "At minimum, configure 'en' and 'de' voices in core.yaml\n"
                    "Example:\n"
                    "  modelservice:\n"
                    "    tts:\n"
                    "      voices:\n"
                    "        en: \"Daisy Studious\"\n"
                    "        de: \"Daisy Studious\"\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No voices configured in modelservice.tts.voices")
            
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
            language: ISO 639-1 language code (e.g., "en", "de")
            speed: Speech speed multiplier (default: 1.0)
            
        Yields:
            Tuple of (audio_bytes, sample_rate) for each chunk
        """
        if not self._initialized:
            raise RuntimeError("TTS handler not initialized")
        
        try:
            # Split text into sentences for streaming
            chunks = self._split_text(text)
            self._logger.info(f"🎤 Synthesizing {len(chunks)} chunks for language: {language}")
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                self._logger.debug(f"Synthesizing chunk {i+1}/{len(chunks)}: {chunk[:50]}...")
                
                # Synthesize chunk
                if self._voice_path:
                    audio = await asyncio.to_thread(
                        self._tts.tts,
                        text=chunk,
                        language=language,
                        speaker_wav=str(self._voice_path),
                        speed=speed
                    )
                else:
                    # Get voice for language, fallback to English voice
                    speaker = self._voices.get(language, self._voices.get("en", "Daisy Studious"))
                    audio = await asyncio.to_thread(
                        self._tts.tts,
                        text=chunk,
                        language=language,
                        speaker=speaker,
                        speed=speed
                    )
                
                # Convert to WAV bytes
                sample_rate = 22050  # XTTS default sample rate
                wav_bytes = self._to_wav(audio, sample_rate)
                
                yield (wav_bytes, sample_rate)
                
            self._logger.info(f"✅ TTS synthesis complete ({len(chunks)} chunks)")
            
        except Exception as e:
            self._logger.error(f"TTS synthesis failed: {e}")
            raise
    
    def _split_text(self, text: str, max_chars: int = 500) -> list[str]:
        """
        Split text into chunks at sentence boundaries.
        
        Args:
            text: Text to split
            max_chars: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        import re
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
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
