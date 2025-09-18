"""
SpaCyManager - Cross-platform spaCy model management and lifecycle control.

This module handles complete spaCy model lifecycle management including:
- Cross-platform model detection and download
- Installation in AICO directory structure using proper paths
- Multi-language model support with fallback strategies
- UV-compatible download mechanisms
- Integration with AICO's unified logging system
"""

import asyncio
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import httpx
from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths


class SpaCyManager:
    """Manages spaCy model installation, updates, and lifecycle."""
    
    # spaCy model release URLs
    SPACY_MODELS_GITHUB = "https://github.com/explosion/spacy-models/releases"
    SPACY_MODELS_API = "https://api.github.com/repos/explosion/spacy-models/releases"
    
    # Multi-language model configuration with download priorities
    LANGUAGE_MODELS = {
        "en": {
            "name": "en_core_web_sm",
            "priority": 1,  # Highest priority - required
            "description": "English (small)",
            "required": True
        },
        "de": {
            "name": "de_core_news_sm", 
            "priority": 2,
            "description": "German (small)",
            "required": False
        },
        "fr": {
            "name": "fr_core_news_sm",
            "priority": 3,
            "description": "French (small)", 
            "required": False
        },
        "es": {
            "name": "es_core_news_sm",
            "priority": 4,
            "description": "Spanish (small)",
            "required": False
        },
        "it": {
            "name": "it_core_news_sm",
            "priority": 5,
            "description": "Italian (small)",
            "required": False
        },
        "pt": {
            "name": "pt_core_news_sm",
            "priority": 6,
            "description": "Portuguese (small)",
            "required": False
        },
        "nl": {
            "name": "nl_core_news_sm",
            "priority": 7,
            "description": "Dutch (small)",
            "required": False
        },
        "zh": {
            "name": "zh_core_web_sm",
            "priority": 8,
            "description": "Chinese (small)",
            "required": False
        }
    }
    
    def __init__(self):
        # Initialize logger - will be set up after logging is initialized
        self.logger = None
        
        # Load configuration
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize()
        
        # Get spaCy-specific config from core.modelservice.spacy
        self.spacy_config = self.config_manager.get("core.modelservice.spacy", {})
        
        # Loaded models cache
        self.nlp_models: Dict[str, any] = {}
        
        # Platform detection
        self.platform = platform.system()
        self.architecture = platform.machine()
    
    def _ensure_logger(self):
        """Ensure logger is initialized (lazy initialization)."""
        if self.logger is None:
            try:
                self.logger = get_logger("modelservice", "core.spacy_manager")
            except RuntimeError:
                # Logging not initialized yet, use basic Python logger as fallback
                import logging
                self.logger = logging.getLogger("spacy_manager")
                self.logger.setLevel(logging.INFO)
    
    def _get_python_executable(self) -> str:
        """Get the correct Python executable for the current environment."""
        # In UV environment, use sys.executable which points to the venv Python
        return sys.executable
    
    def _supports_ansi_escapes(self) -> bool:
        """Check if terminal supports ANSI escape sequences."""
        import os
        
        # Not a TTY - no ANSI support needed
        if not sys.stdout.isatty():
            return False
            
        # Windows Terminal and modern terminals
        if os.getenv("WT_SESSION") or os.getenv("TERM_PROGRAM"):
            return True
            
        # GitBash/MSYS2/Cygwin on Windows
        if sys.platform == "win32" and (
            os.getenv("MSYSTEM") or 
            "bash" in os.getenv("SHELL", "").lower() or
            "Git" in os.getenv("TERM_PROGRAM", "")
        ):
            return True
            
        # Linux/macOS terminals
        if sys.platform in ["linux", "darwin"] and os.getenv("TERM"):
            return True
            
        # Windows with ANSICON
        if os.getenv("ANSICON"):
            return True
            
        # Default: assume no ANSI support (Windows CMD/PowerShell)
        return False

    def _print_status(self, icon: str, message: str, color_code: str = ""):
        """Print a beautifully formatted status message."""
        # ANSI color codes (safe fallback if not supported)
        colors = {
            "blue": "\033[94m",
            "green": "\033[92m", 
            "yellow": "\033[93m",
            "red": "\033[91m",
            "cyan": "\033[96m",
            "reset": "\033[0m"
        }
        
        # Check for color support
        supports_color = self._supports_ansi_escapes() and color_code in colors
        
        if supports_color:
            print(f"{colors[color_code]}{icon} {message}{colors['reset']}")
        else:
            print(f"{icon} {message}")
    
    async def ensure_models_installed(self, force_update: bool = False) -> Dict[str, bool]:
        """
        Ensure spaCy models are installed and up to date.
        
        Args:
            force_update: Force re-download even if models exist
            
        Returns:
            Dict mapping language codes to installation success status
        """
        self._ensure_logger()
        installation_results = {}
        
        try:
            # Check config for auto_install setting
            if not self.spacy_config.get("auto_install", True) and not force_update:
                self.logger.info("Auto-install disabled in config, skipping model installation")
                return await self._check_existing_models()
            
            # Import spaCy to verify it's available
            try:
                import spacy
                self.logger.info("spaCy library available, proceeding with model management")
            except ImportError as e:
                self.logger.error(f"spaCy not available: {e}")
                self.logger.error("Install modelservice dependencies with: uv sync --extra modelservice")
                return {}
            
            # Get configured languages or default to English only
            target_languages = self.spacy_config.get("languages", ["en"])
            if not isinstance(target_languages, list):
                target_languages = ["en"]  # Fallback to English
            
            self.logger.info(f"Managing spaCy models for languages: {target_languages}")
            
            # Install models in priority order
            for lang_code in sorted(target_languages, key=lambda x: self.LANGUAGE_MODELS.get(x, {}).get("priority", 999)):
                if lang_code not in self.LANGUAGE_MODELS:
                    self.logger.warning(f"Unsupported language code: {lang_code}")
                    installation_results[lang_code] = False
                    continue
                
                model_config = self.LANGUAGE_MODELS[lang_code]
                model_name = model_config["name"]
                
                try:
                    # Check if model is already available
                    if not force_update and await self._is_model_available(model_name):
                        self.logger.info(f"Model {model_name} already available")
                        installation_results[lang_code] = True
                        continue
                    
                    # Download and install model
                    self._print_status("📥", f"Installing {model_config['description']} model: {model_name}", "blue")
                    success = await self._install_model(model_name, lang_code)
                    installation_results[lang_code] = success
                    
                    if success:
                        self._print_status("✅", f"Model ready: {model_name}", "green")
                        self.logger.info(f"Successfully installed model: {model_name}")
                    else:
                        self._print_status("❌", f"Failed to install: {model_name}", "red")
                        self.logger.error(f"Failed to install model: {model_name}")
                        
                        # If this is a required model (English), this is critical
                        if model_config.get("required", False):
                            self.logger.error("Critical model installation failed - NER system may not function properly")
                    
                except Exception as e:
                    self.logger.error(f"Error installing model {model_name}: {e}")
                    installation_results[lang_code] = False
            
            # Load successfully installed models
            await self._load_models()
            
            return installation_results
            
        except Exception as e:
            self.logger.error(f"Failed to ensure spaCy models installation: {type(e).__name__}: {e}")
            return {}
    
    async def _check_existing_models(self) -> Dict[str, bool]:
        """Check which models are already available without installing new ones."""
        results = {}
        
        try:
            import spacy
            
            for lang_code, model_config in self.LANGUAGE_MODELS.items():
                model_name = model_config["name"]
                results[lang_code] = await self._is_model_available(model_name)
            
        except ImportError:
            # spaCy not available
            pass
        
        return results
    
    async def _is_model_available(self, model_name: str) -> bool:
        """Check if a spaCy model is available for loading."""
        try:
            import spacy
            
            # Try to load the model to verify it's available
            try:
                # Use spacy.util.is_package to check if model is installed
                if hasattr(spacy.util, 'is_package'):
                    return spacy.util.is_package(model_name)
                else:
                    # Fallback: try to load the model
                    nlp = spacy.load(model_name)
                    return nlp is not None
            except (OSError, IOError):
                return False
                
        except ImportError:
            return False
    
    async def _install_model(self, model_name: str, lang_code: str) -> bool:
        """
        Install a spaCy model using UV-compatible methods.
        
        Args:
            model_name: Name of the spaCy model (e.g., 'en_core_web_sm')
            lang_code: Language code (e.g., 'en')
            
        Returns:
            True if installation successful, False otherwise
        """
        self._ensure_logger()
        
        try:
            # Method 1: Try using spaCy's download command with UV
            if await self._install_via_spacy_download(model_name):
                return True
            
            # Method 2: Try direct pip install with model URL
            if await self._install_via_direct_url(model_name):
                return True
            
            # Method 3: Try installing pip in the environment and retry
            if await self._install_with_pip_fallback(model_name):
                return True
            
            # Method 4: Try simple pip install (some models might be on PyPI)
            if await self._install_via_simple_pip(model_name):
                return True
            
            self.logger.error(f"All installation methods failed for model: {model_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error installing model {model_name}: {e}")
            return False
    
    async def _install_via_spacy_download(self, model_name: str) -> bool:
        """Try installing using spaCy's download command."""
        try:
            self.logger.info(f"Attempting spaCy download for {model_name}")
            
            # Use UV run to execute spaCy download
            cmd = [
                "uv", "run", "--", 
                "python", "-m", "spacy", "download", model_name
            ]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            
            if process.returncode == 0:
                self.logger.info(f"Successfully downloaded {model_name} via spaCy download")
                return True
            else:
                self.logger.warning(f"spaCy download failed for {model_name}: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            self.logger.error(f"spaCy download timed out for {model_name}")
            return False
        except Exception as e:
            self.logger.warning(f"spaCy download method failed for {model_name}: {e}")
            return False
    
    async def _install_via_direct_url(self, model_name: str) -> bool:
        """Try installing using direct URL with pip."""
        try:
            # Get the latest model URL from GitHub releases
            model_url = await self._get_model_download_url(model_name)
            if not model_url:
                return False
            
            self.logger.info(f"Attempting direct URL install for {model_name}: {model_url}")
            
            # Use UV to install directly from URL
            cmd = [
                "uv", "pip", "install", model_url
            ]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            
            if process.returncode == 0:
                self.logger.info(f"Successfully installed {model_name} via direct URL")
                return True
            else:
                self.logger.warning(f"Direct URL install failed for {model_name}: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Direct URL install method failed for {model_name}: {e}")
            return False
    
    async def _install_with_pip_fallback(self, model_name: str) -> bool:
        """Try installing pip in the environment and then installing the model."""
        try:
            self.logger.info(f"Attempting pip fallback method for {model_name}")
            
            # First, ensure pip is available in the UV environment
            pip_install_cmd = ["uv", "add", "pip"]
            
            process = await asyncio.create_subprocess_exec(
                *pip_install_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            # Now try the spaCy download again
            return await self._install_via_spacy_download(model_name)
            
        except Exception as e:
            self.logger.warning(f"Pip fallback method failed for {model_name}: {e}")
            return False
    
    async def _install_via_simple_pip(self, model_name: str) -> bool:
        """Try installing using simple pip install (some models might be on PyPI)."""
        try:
            self.logger.info(f"Attempting simple pip install for {model_name}")
            
            # Use UV pip to install the model directly
            cmd = ["uv", "pip", "install", model_name]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            
            if process.returncode == 0:
                self.logger.info(f"Successfully installed {model_name} via simple pip")
                return True
            else:
                self.logger.warning(f"Simple pip install failed for {model_name}: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Simple pip install method failed for {model_name}: {e}")
            return False
    
    async def _get_model_download_url(self, model_name: str) -> Optional[str]:
        """Get the download URL for a spaCy model using spaCy's info command."""
        try:
            # Use spaCy's built-in info command to get the download URL
            # This is the proper way to get model URLs dynamically
            cmd = ["uv", "run", "--", "python", "-m", "spacy", "info", model_name, "--url"]
            
            self.logger.debug(f"Getting model URL with command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            if process.returncode == 0 and stdout:
                url = stdout.decode().strip()
                if url.startswith('http'):
                    self.logger.info(f"Found official download URL for {model_name}: {url}")
                    return url
            
            self.logger.debug(f"spaCy info command failed for {model_name}: {stderr.decode() if stderr else 'No output'}")
            return None
                
        except Exception as e:
            self.logger.debug(f"Failed to get download URL for {model_name}: {e}")
            return None
    
    async def _load_models(self) -> None:
        """Load all available spaCy models into memory."""
        self._ensure_logger()
        
        try:
            import spacy
            
            loaded_count = 0
            for lang_code, model_config in self.LANGUAGE_MODELS.items():
                model_name = model_config["name"]
                
                try:
                    if await self._is_model_available(model_name):
                        self.logger.info(f"Loading {model_config['description']} model: {model_name}")
                        nlp = spacy.load(model_name)
                        self.nlp_models[lang_code] = nlp
                        loaded_count += 1
                        self.logger.info(f"Successfully loaded {model_name}")
                    else:
                        self.logger.debug(f"Model {model_name} not available for loading")
                        
                except Exception as e:
                    self.logger.error(f"Failed to load model {model_name}: {e}")
            
            if loaded_count > 0:
                loaded_langs = ", ".join([
                    f"{lang.upper()}" for lang in sorted(self.nlp_models.keys())
                ])
                self._print_status("✅", f"NER system ready ({loaded_langs})", "green")
                self.logger.info(f"NER system initialization successful - loaded {loaded_count} models: {loaded_langs}")
            else:
                self._print_status("⚠️", "NER system unavailable (no models loaded)", "yellow")
                self.logger.warning("NER system initialization completed but no models were loaded")
                
        except ImportError as e:
            self._print_status("❌", "NER system unavailable (spaCy not installed)", "red")
            self.logger.error(f"spaCy not installed - NER system unavailable: {e}")
            self.logger.error("Install modelservice dependencies with: uv sync --extra modelservice")
    
    def get_model_for_text(self, text: str):
        """Get the most appropriate spaCy model for the given text."""
        if not self.nlp_models:
            return None
        
        # Detect language
        detected_lang = self._detect_language(text)
        
        # Try to get model for detected language
        if detected_lang in self.nlp_models:
            return self.nlp_models[detected_lang]
        
        # Fallback to English
        if "en" in self.nlp_models:
            return self.nlp_models["en"]
        
        # Fallback to any available model
        if self.nlp_models:
            fallback_lang = next(iter(self.nlp_models))
            return self.nlp_models[fallback_lang]
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Detect language of input text. Returns language code or 'en' as fallback."""
        try:
            # Simple heuristic-based language detection
            # For production, consider using langdetect or similar
            
            # Check for common patterns
            if any(char in text for char in "äöüßÄÖÜ"):
                return "de"  # German
            elif any(char in text for char in "àâäéèêëïîôöùûüÿç"):
                return "fr"  # French  
            elif any(char in text for char in "ñáéíóúü"):
                return "es"  # Spanish
            elif any(char in text for char in "àèéìíîòóù"):
                return "it"  # Italian
            elif any(char in text for char in "ãáâàéêíóôõú"):
                return "pt"  # Portuguese
            elif any(char in text for char in "áéíóúý"):
                return "nl"  # Dutch (simplified)
            elif any(ord(char) > 0x4e00 and ord(char) < 0x9fff for char in text):
                return "zh"  # Chinese
            else:
                return "en"  # Default to English
                
        except Exception as e:
            self.logger.debug(f"Language detection failed: {e}, defaulting to English")
            return "en"
    
    async def get_status(self) -> Dict:
        """
        Get comprehensive spaCy model status information.
        
        Returns:
            Dict: Status information including available models, loaded models, etc.
        """
        status = {
            "spacy_available": False,
            "models_dir": str(self.models_dir),
            "loaded_models": list(self.nlp_models.keys()),
            "available_models": {},
            "configured_languages": self.spacy_config.get("languages", ["en"])
        }
        
        try:
            import spacy
            status["spacy_available"] = True
            status["spacy_version"] = spacy.__version__
            
            # Check availability of each configured model
            for lang_code, model_config in self.LANGUAGE_MODELS.items():
                model_name = model_config["name"]
                is_available = await self._is_model_available(model_name)
                status["available_models"][lang_code] = {
                    "name": model_name,
                    "description": model_config["description"],
                    "available": is_available,
                    "loaded": lang_code in self.nlp_models
                }
                
        except ImportError:
            pass
        
        return status
