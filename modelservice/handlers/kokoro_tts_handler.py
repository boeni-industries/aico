"""
Kokoro TTS Handler - Fast, high-quality neural TTS synthesis using ONNX Runtime.

Kokoro is a lightweight 82M parameter TTS model with excellent quality.
Uses ONNX Runtime for fast CPU/GPU inference with no system dependencies.
"""

import asyncio
import io
import os
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional
from urllib.request import urlretrieve

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.ai.utils import detect_language
from modelservice.handlers.tts_utils import clean_text_for_tts


class KokoroTtsHandler:
    """
    Handles TTS synthesis using Kokoro ONNX.
    
    Features:
    - Multi-language support (English, Japanese, Chinese, etc.)
    - Multiple voice options per language
    - Streaming audio generation
    - WAV format output
    - No system dependencies (pure Python + ONNX Runtime)
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize Kokoro TTS handler.
        
        Args:
            config_manager: Configuration manager instance
        """
        self._kokoro = None
        self._initialized = False
        self._config = config_manager
        self._voices = {}  # Language -> voice name mapping
        self._model_path = None
        self._voices_path = None
        self._logger = get_logger("modelservice", "kokoro_tts_handler")
        
    async def initialize(self):
        """Initialize Kokoro TTS system."""
        try:
            self._logger.info("🚀 Initializing Kokoro TTS (ONNX Runtime)")
            
            # Import Kokoro ONNX (lazy import to avoid loading if not used)
            try:
                from kokoro_onnx import Kokoro
                import soundfile as sf
            except ImportError:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "❌ FATAL: kokoro-onnx package not installed!\n"
                    "Please install: pip install kokoro-onnx soundfile\n"
                    "Or run: uv sync --extra modelservice\n"
                    "="*80
                )
                self._logger.error(error_msg)
                print(error_msg, flush=True)
                raise RuntimeError("kokoro-onnx package not installed")
            
            # Get TTS configuration
            if not self._config:
                raise RuntimeError("No configuration manager provided to Kokoro TTS handler")
            
            tts_config = self._config.get("core.modelservice.tts.kokoro", None)
            if not tts_config:
                raise RuntimeError("No Kokoro TTS configuration found in core.modelservice.tts.kokoro")
            
            self._logger.info(f"✅ Found Kokoro config: {tts_config}")
            
            # Load voice configuration
            self._voices = tts_config.get("voices", {})
            if not self._voices:
                raise RuntimeError("No voices configured for Kokoro TTS")
            
            self._logger.info(f"✅ Loaded voice mappings: {self._voices}")
            
            # Set up Kokoro cache directory
            kokoro_cache_dir = AICOPaths.get_cache_directory() / "kokoro"
            kokoro_cache_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"📁 Kokoro cache directory: {kokoro_cache_dir}")
            
            # Download model files if not present
            self._model_path = kokoro_cache_dir / "kokoro-v1.0.onnx"
            self._voices_path = kokoro_cache_dir / "voices-v1.0.bin"
            
            await self._download_model_files()
            
            # Configure ONNX Runtime for optimal performance (before loading model)
            cpu_count = os.cpu_count() or 4
            physical_cores = cpu_count // 2  # Estimate physical cores (hyperthreading)
            
            # Set environment variables for ONNX Runtime performance
            os.environ["OMP_NUM_THREADS"] = str(physical_cores)
            os.environ["OMP_WAIT_POLICY"] = "ACTIVE"  # Spin threads for lower latency
            
            # Enable GPU acceleration via CoreML (Apple Neural Engine on M-series Macs)
            import onnxruntime as rt
            available_providers = rt.get_available_providers()
            
            if "CoreMLExecutionProvider" in available_providers:
                os.environ["ONNX_PROVIDER"] = "CoreMLExecutionProvider"
                self._logger.info("🚀 GPU Acceleration: CoreML (Apple Neural Engine) enabled")
                print("🚀 GPU Acceleration: CoreML (Apple Neural Engine) enabled", flush=True)
            elif "CUDAExecutionProvider" in available_providers:
                os.environ["ONNX_PROVIDER"] = "CUDAExecutionProvider"
                self._logger.info("🚀 GPU Acceleration: CUDA enabled")
                print("🚀 GPU Acceleration: CUDA enabled", flush=True)
            else:
                self._logger.info(f"⚙️  CPU mode: {physical_cores} threads, active spinning")
            
            # Initialize Kokoro with model files
            self._logger.info("📥 Loading Kokoro ONNX model...")
            self._kokoro = await asyncio.to_thread(
                Kokoro,
                str(self._model_path),
                str(self._voices_path)
            )
            
            self._logger.info("✅ Kokoro ONNX model loaded successfully")
            
            # Warm up with a test synthesis
            self._logger.info("🔥 Warming up Kokoro with test synthesis...")
            test_voice = self._voices.get("en", "af_bella")
            
            def warmup():
                """Warm up synthesis in thread."""
                samples, sample_rate = self._kokoro.create(
                    "Hello",
                    voice=test_voice,
                    speed=1.0,
                    lang="en-us"
                )
                return True
            
            await asyncio.to_thread(warmup)
            
            self._initialized = True
            self._logger.info("✅ Kokoro TTS initialization complete")
            print("=" * 80)
            print("✅ KOKORO TTS READY")
            print(f"   Model: Kokoro-82M ONNX")
            print(f"   Voices: {', '.join(self._voices.keys())}")
            print(f"   Cache: {kokoro_cache_dir}")
            print("=" * 80)
            
        except Exception as e:
            self._logger.error(f"Failed to initialize Kokoro TTS: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _download_model_files(self):
        """Download Kokoro model files if not present."""
        model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
        voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
        
        # Download model file
        if not self._model_path.exists():
            self._logger.info(f"📥 Downloading Kokoro model (~300MB)...")
            print(f"📥 Downloading Kokoro model to {self._model_path}...")
            await asyncio.to_thread(urlretrieve, model_url, str(self._model_path))
            self._logger.info("✅ Model downloaded successfully")
        else:
            self._logger.info(f"✅ Model already cached: {self._model_path}")
        
        # Download voices file
        if not self._voices_path.exists():
            self._logger.info(f"📥 Downloading Kokoro voices (~80MB)...")
            print(f"📥 Downloading Kokoro voices to {self._voices_path}...")
            await asyncio.to_thread(urlretrieve, voices_url, str(self._voices_path))
            self._logger.info("✅ Voices downloaded successfully")
        else:
            self._logger.info(f"✅ Voices already cached: {self._voices_path}")
    
    async def synthesize_stream(
        self,
        text: str,
        language: str = "en",
        speed: float = 1.0
    ) -> AsyncGenerator[tuple[bytes, int], None]:
        """
        Synthesize speech from text and stream audio chunks.
        
        Args:
            text: Text to synthesize
            language: Language code (e.g., "en", "de")
            speed: Speech speed multiplier (default: 1.0)
            
        Yields:
            Tuple of (audio_bytes, sample_rate) for each chunk
        """
        try:
            import numpy as np
            import soundfile as sf
            
            if not self._initialized:
                raise RuntimeError("Kokoro TTS not initialized. Call initialize() first.")
            
            # Clean text for TTS (using shared utility)
            cleaned_text = clean_text_for_tts(text)
            if not cleaned_text.strip():
                self._logger.warning("Empty text after cleaning, skipping synthesis")
                return
            
            # Auto-detect language if needed
            if self._config and self._config.get("core.modelservice.tts.auto_detect_language", True):
                detected_result = detect_language(cleaned_text)
                if detected_result and detected_result.language:
                    detected_lang = detected_result.language
                    if detected_lang != language:
                        self._logger.info(f"🔍 Auto-detected language: {detected_lang} (requested: {language})")
                        language = detected_lang
            
            # Get voice for language
            voice_name = self._voices.get(language, self._voices.get("en", "af_bella"))
            self._logger.info(f"🎤 Using voice: {voice_name} for language: {language}")
            
            # Map language code to Kokoro format
            lang_map = {
                "en": "en-us",
                "de": "en-us",  # Fallback to English for German
                "ja": "ja",
                "zh": "zh-cn"
            }
            kokoro_lang = lang_map.get(language, "en-us")
            
            # Synthesize audio
            self._logger.info(f"🎵 Synthesizing: '{cleaned_text[:50]}...' (speed: {speed})")
            
            def synthesize():
                """Run synthesis in thread."""
                samples, sample_rate = self._kokoro.create(
                    cleaned_text,
                    voice=voice_name,
                    speed=speed,
                    lang=kokoro_lang
                )
                return samples, sample_rate
            
            samples, sample_rate = await asyncio.to_thread(synthesize)
            
            # Convert float32 samples to int16 PCM
            samples_int16 = (samples * 32767).astype(np.int16)
            
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(samples_int16.tobytes())
            
            # Get WAV bytes
            audio_bytes = wav_buffer.getvalue()
            
            self._logger.info(f"✅ Synthesized {len(audio_bytes)} bytes at {sample_rate}Hz")
            
            # Yield single chunk (Kokoro generates complete audio at once)
            yield (audio_bytes, sample_rate)
            
        except Exception as e:
            self._logger.error(f"Kokoro synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            raise
