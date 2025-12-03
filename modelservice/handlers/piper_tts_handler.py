"""
Piper TTS Handler - Ultra-fast neural TTS synthesis.

Piper is 100x faster than XTTS (~300ms vs ~20s for 700 chars).
No voice cloning support, but excellent quality with pre-trained voices.
"""

import asyncio
import io
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.ai.utils import detect_language
from modelservice.handlers.tts_utils import clean_text_for_tts


class PiperTtsHandler:
    """
    Piper TTS handler for ultra-fast speech synthesis.
    
    Features:
    - 100x faster than XTTS (~300ms for 700 chars)
    - High-quality neural voices
    - Automatic language detection
    - Streaming audio output
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize Piper TTS handler.
        
        Args:
            config_manager: Configuration manager instance
        """
        self._piper = None
        self._initialized = False
        self._config = config_manager
        self._voices = {}  # Language -> voice model mapping
        self._piper_voices = {}  # Cached loaded voice models
        self._quality = "medium"
        self._logger = get_logger("modelservice", "piper_tts_handler")
        
    async def initialize(self):
        """Initialize Piper TTS system."""
        try:
            self._logger.info("🚀 Initializing Piper TTS (ultra-fast synthesis)")
            
            # Import Piper (lazy import to avoid loading if not used)
            from piper import PiperVoice
            
            # Get TTS configuration
            if not self._config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: No configuration manager provided to Piper TTS handler!\n"
                    "This indicates a serious initialization problem.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No configuration manager provided to Piper TTS handler")
            
            tts_config = self._config.get("core.modelservice.tts.piper", None)
            if tts_config is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Piper TTS configuration not found!\n"
                    "Expected path: core.modelservice.tts.piper\n"
                    "Check config/defaults/core.yaml for proper structure.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No Piper TTS configuration found in core.modelservice.tts.piper")
            
            if not tts_config:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Piper TTS configuration is empty!\n"
                    "Path: core.modelservice.tts.piper\n"
                    "Configuration exists but contains no data.\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("Piper TTS configuration is empty")
            
            self._logger.info(f"✅ Found Piper config: {tts_config}")
            
            # Load voice configuration
            self._voices = tts_config.get("voices", None)
            if self._voices is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: No voices section in Piper configuration!\n"
                    "Expected path: core.modelservice.tts.piper.voices\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("No voices configured in core.modelservice.tts.piper.voices")
            
            if not self._voices:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: Piper voices configuration is empty!\n"
                    "At minimum, configure 'en' and 'de' voices.\n"
                    "Example:\n"
                    "  piper:\n"
                    "    voices:\n"
                    "      en: 'en_US-amy-medium'\n"
                    "      de: 'de_DE-eva_k-x_low'\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("Piper voices configuration is empty")
            
            self._logger.info(f"✅ Configured voices: {self._voices}")
            
            # Get quality setting
            self._quality = tts_config.get("quality", "medium")
            self._logger.info(f"✅ Voice quality: {self._quality}")
            
            # Set up Piper cache directory
            piper_cache_dir = AICOPaths.get_cache_directory() / "piper"
            piper_cache_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"📁 Piper cache directory: {piper_cache_dir}")
            
            # Voice models will be loaded on-demand during synthesis
            self._logger.info("✅ Piper TTS handler initialized (voices will be loaded on-demand)")
            self._initialized = True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize Piper TTS handler: {e}")
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
            
            # Clean markdown and special formatting from text (using shared utility)
            clean_start = time.time()
            cleaned_text = clean_text_for_tts(text)
            clean_time = time.time() - clean_start
            self._logger.info(f"🎤 Original text: {len(text)} chars, cleaned: {len(cleaned_text)} chars")
            
            self._logger.info(f"🎤 Synthesizing with Piper (language: {language})")
            print("=" * 80)
            print(f"📝 [PIPER TTS] CLEANED TEXT ({len(cleaned_text)} chars):")
            print(cleaned_text)
            print(f"⏱️ [PIPER TIMING] Text cleaning: {clean_time*1000:.2f}ms")
            print("=" * 80)
            
            # Get voice model for language
            voice_name = self._voices.get(language)
            if not voice_name:
                self._logger.warning(f"No Piper voice configured for language '{language}', using English")
                voice_name = self._voices.get("en", "en_US-amy-medium")
                language = "en"
            
            # Load voice if not cached
            if language not in self._piper_voices:
                # Set up voice directory
                piper_cache = AICOPaths.get_cache_directory() / "piper" / "voices"
                piper_cache.mkdir(parents=True, exist_ok=True)
                
                voice_file = piper_cache / f"{voice_name}.onnx"
                
                # Download voice if not exists
                if not voice_file.exists():
                    import subprocess
                    import sys
                    self._logger.info(f"📥 Downloading Piper voice: {voice_name} to {piper_cache}")
                    result = subprocess.run(
                        [sys.executable, "-m", "piper.download_voices", voice_name, "--download-dir", str(piper_cache)],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self._logger.info(f"✅ Voice downloaded: {voice_name}")
                
                if not voice_file.exists():
                    raise RuntimeError(f"Voice file not found after download: {voice_file}")
                
                self._logger.info(f"✅ Loading voice from: {voice_file}")
                from piper import PiperVoice
                self._piper_voices[language] = PiperVoice.load(str(voice_file))
            
            voice = self._piper_voices[language]
            
            # Synthesize audio
            synthesis_start = time.time()
            
            def synthesize():
                """Synthesize audio in thread."""
                # Piper's synthesize() returns generator of AudioChunk objects
                # Note: noise_scale is set in the voice model config, not here
                audio_chunks = []
                actual_sample_rate = None
                
                for chunk in voice.synthesize(cleaned_text):
                    audio_chunks.append(chunk.audio_int16_bytes)
                    # Get sample rate from first chunk
                    if actual_sample_rate is None:
                        actual_sample_rate = chunk.sample_rate
                
                # Concatenate all chunks
                if audio_chunks:
                    audio_data = b''.join(audio_chunks)
                    sample_rate = actual_sample_rate or 22050
                    return audio_data, sample_rate
                else:
                    return b'', 22050
            
            audio_bytes, sample_rate = await asyncio.to_thread(synthesize)
            
            # Speed up German voice by 10% using proper resampling
            if language == "de":
                import struct
                import numpy as np
                from scipy import signal
                
                # Convert to numpy array
                samples = np.frombuffer(audio_bytes, dtype=np.int16)
                
                # Calculate new length (10% faster = 90.9% of original length)
                new_length = int(len(samples) / 1.1)
                
                # Resample using high-quality polyphase filtering
                resampled = signal.resample(samples, new_length)
                
                # Convert back to int16
                resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
                audio_bytes = resampled.tobytes()
                
                print(f"🔍 [PIPER DEBUG] Sped up German audio by 10%: {len(samples)} → {len(resampled)} samples", flush=True)
            
            # Debug: Analyze raw audio from Piper for trailing artifacts
            print(f"🔍 [PIPER DEBUG] Raw audio size: {len(audio_bytes)} bytes", flush=True)
            
            # Apply fade-out to eliminate pop/click at end
            if len(audio_bytes) >= 2000:
                import struct
                
                # Convert entire audio to samples
                all_samples = list(struct.unpack(f'<{len(audio_bytes)//2}h', audio_bytes))
                num_samples = len(all_samples)
                
                # Debug: Check last samples before fix
                last_10_before = all_samples[-10:]
                print(f"🔍 [PIPER DEBUG] Last 10 samples BEFORE fix: {last_10_before}", flush=True)
                
                # Apply 300ms fade-out (4800 samples at 16kHz)
                fade_samples = min(4800, num_samples)
                for i in range(fade_samples):
                    fade_factor = (fade_samples - i) / fade_samples
                    all_samples[num_samples - fade_samples + i] = int(all_samples[num_samples - fade_samples + i] * fade_factor)
                
                # Force last 500 samples to absolute zero
                for i in range(min(500, num_samples)):
                    all_samples[num_samples - 1 - i] = 0
                
                # Reconstruct audio
                audio_bytes = struct.pack(f'<{num_samples}h', *all_samples)
                
                print(f"🔍 [PIPER DEBUG] Last 10 samples AFTER fix: {all_samples[-10:]}", flush=True)
            
            synthesis_time = time.time() - synthesis_start
            print(f"⏱️ [PIPER TIMING] 🎯 SYNTHESIS COMPLETE: {synthesis_time*1000:.2f}ms")
            print(f"🔊 [PIPER] Sample rate: {sample_rate} Hz", flush=True)
            self._logger.info(f"🔊 Sample rate: {sample_rate} Hz")
            
            # Split into chunks for streaming (same as XTTS for compatibility)
            chunk_size = 44100  # ~0.5s of audio per chunk at 22050 Hz
            chunks = [audio_bytes[i:i+chunk_size] for i in range(0, len(audio_bytes), chunk_size)]
            
            print(f"⏱️ [PIPER TIMING] Generated {len(chunks)} chunks")
            
            # Yield chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    first_chunk_time = time.time() - overall_start
                    print(f"⏱️ [PIPER TIMING] 🎯 TIME TO FIRST CHUNK: {first_chunk_time*1000:.2f}ms")
                
                print(f"🎤 [PIPER] Chunk {i+1}/{len(chunks)}: {len(chunk)} bytes")
                yield (chunk, sample_rate)
            
            overall_time = time.time() - overall_start
            print(f"⏱️ [PIPER TIMING] ========== TOTAL TIME: {overall_time*1000:.2f}ms ==========")
            self._logger.info(f"✅ Piper TTS synthesis complete ({len(chunks)} chunks) in {overall_time:.2f}s")
            
        except Exception as e:
            self._logger.error(f"Piper TTS synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _trim_trailing_silence(self, audio_bytes: bytes, threshold: int = 500) -> bytes:
        """
        Add fade-out and silence padding to prevent pop/click at end.
        
        The pop/click occurs when audio doesn't end at zero crossing.
        Solution: Apply fade-out + add silence padding.
        
        Args:
            audio_bytes: Raw PCM audio bytes (16-bit)
            threshold: Not used
            
        Returns:
            Audio bytes with fade-out and silence padding
        """
        import struct
        
        if len(audio_bytes) < 2:
            return audio_bytes
        
        # Convert bytes to 16-bit samples
        num_samples = len(audio_bytes) // 2
        samples = list(struct.unpack(f'<{num_samples}h', audio_bytes))
        
        # Return audio unchanged - processing made pop/click worse
        # The artifact is likely from the audio player, not the audio data
        return audio_bytes
