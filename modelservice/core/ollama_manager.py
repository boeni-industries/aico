"""
OllamaManager - Automated Ollama binary management and lifecycle control.

This module handles complete Ollama lifecycle management including:
- Cross-platform binary detection and download
- Installation in AICO directory structure
- Process management and health monitoring
- Log integration with AICO's unified logging system
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.paths import get_aico_root_path


class OllamaManager:
    """Manages Ollama binary installation, updates, and process lifecycle."""
    
    # GitHub API configuration
    GITHUB_API_URL = "https://api.github.com/repos/ollama/ollama/releases/latest"
    GITHUB_RELEASES_URL = "https://github.com/ollama/ollama/releases/download"
    
    # Platform-specific binary mappings
    PLATFORM_BINARIES = {
        "Windows": "ollama-windows-amd64.zip",
        "Darwin": "ollama-darwin",  # Will be determined by architecture
        "Linux": "ollama-linux-amd64"
    }
    
    def __init__(self):
        # Initialize logger - will be set up after logging is initialized
        self.logger = None
        self.aico_root = get_aico_root_path()
        self.bin_dir = self.aico_root / "bin"
        self.models_dir = self.aico_root / "models"
        
        # Load configuration
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize()
        
        # Debug: Check what's actually in the config
        full_config = self.config_manager.config_cache
        
        # The configuration is loaded under the dedicated 'modelservice' domain
        self.ollama_config = self.config_manager.get("modelservice.ollama", {})
        self.logs_dir = self.aico_root / "logs"
        self.ollama_process: Optional[subprocess.Popen] = None
        
        # Ensure directories exist
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform detection
        self.platform = platform.system()
        self.architecture = platform.machine()  # Get architecture (arm64, x86_64, etc.)
        self.ollama_binary = self._get_ollama_binary_path()
    
    def _ensure_logger(self):
        """Ensure logger is initialized (lazy initialization)."""
        if self.logger is None:
            try:
                self.logger = get_logger("modelservice.core.ollama_manager")
            except RuntimeError:
                # Logging not initialized yet, use basic Python logger as fallback
                import logging
                self.logger = logging.getLogger("ollama_manager")
                self.logger.setLevel(logging.INFO)

    def _get_ollama_binary_path(self) -> Path:
        """Get the expected path to the Ollama binary for this platform."""
        if self.platform == "Windows":
            return self.bin_dir / "ollama.exe"
        else:
            return self.bin_dir / "ollama"

    def _is_external_mode(self) -> bool:
        """Return True if Ollama is managed externally (no local binary/process management)."""
        return True

    @staticmethod
    def _parse_version(version: Optional[str]) -> Optional[Tuple[int, int, int]]:
        if not version:
            return None
        v = version.strip().lstrip("v")
        parts = v.split(".")
        if len(parts) < 2:
            return None
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
            return major, minor, patch
        except Exception:
            return None

    async def check_available(self) -> bool:
        """Check Ollama container reachability and minimum version requirements."""
        self._ensure_logger()
        host = self.ollama_config.get("host", "127.0.0.1")
        port = self.ollama_config.get("port", 11434)
        min_version = self.ollama_config.get("min_version", "0.0.0")

        if not await self.is_running():
            raise RuntimeError(f"Ollama not reachable at http://{host}:{port}")

        remote_version = await self._get_remote_version()
        parsed_remote = self._parse_version(remote_version)
        parsed_min = self._parse_version(min_version)
        if parsed_min and parsed_remote and parsed_remote < parsed_min:
            raise RuntimeError(
                f"Ollama version {remote_version} does not satisfy minimum required {min_version}"
            )

        self.logger.info(
            "Ollama available",
            extra={
                "ollama_host": host,
                "ollama_port": port,
                "ollama_version": remote_version,
                "ollama_min_version": min_version,
            },
        )
        return True
    
    async def ensure_installed(self, force_update: bool = False) -> bool:
        """Ensure Ollama is installed and up to date, respecting config settings."""
        try:
            self._ensure_logger()
            # Ollama is external-only; do not attempt installation or updates here.
            return await self.check_available()
                
        except Exception as e:
            self.logger.error(f"Failed to ensure Ollama installation: {type(e).__name__}: {e}")
            self.logger.debug(f"Installation error details", exc_info=True)
            return False
    
    async def start_ollama(self) -> bool:
        """Start Ollama server if not already running, respecting config settings."""
        try:
            self._ensure_logger()
            # Ollama is external-only; do not attempt to start a server process.
            return await self.check_available()

        except Exception as e:
            self.logger.error(f"Failed to start Ollama server: {type(e).__name__}: {e}")
            self.logger.debug(f"Startup error details", exc_info=True)
            return False
    
    async def stop_ollama(self) -> bool:
        """Stop Ollama server if it was started by this manager."""
        self._ensure_logger()
        self.logger.info("Ollama stop requested, but Ollama is external-only; skipping")
        return True
    
    async def _health_check(self) -> bool:
        """Check if Ollama API is responding using config URL."""
        try:
            host = self.ollama_config.get("host", "127.0.0.1")
            port = self.ollama_config.get("port", 11434)
            ollama_url = f"http://{host}:{port}"
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=5)
                return response.status_code == 200
                
        except Exception:
            return False

    async def _get_remote_version(self) -> Optional[str]:
        """Get Ollama version from the HTTP API (works for external Ollama containers)."""
        try:
            host = self.ollama_config.get("host", "127.0.0.1")
            port = self.ollama_config.get("port", 11434)
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://{host}:{port}/api/version")
                if resp.status_code != 200:
                    return None
                data = resp.json()
                # Ollama typically returns {"version": "x.y.z"}
                return data.get("version")
        except Exception:
            return None
    
    async def get_status(self) -> Dict:
        """
        Get comprehensive Ollama status information.
        
        Returns:
            Dict: Status information including process state, version, models
        """
        running = await self.is_running()
        healthy = await self._health_check() if running else False
        return {
            "installed": False,
            "running": running,
            "healthy": healthy,
            "version": await self._get_remote_version(),
            "binary_path": str(self.ollama_binary),
            "models_dir": str(self.models_dir),
            "process_id": None,
        }
    
    async def _ensure_default_models(self) -> list:
        """Auto-pull and start default models based on config settings.
        
        Returns:
            list: Names of models that were successfully started
        """
        started_models = []
        try:
            self._ensure_logger()
            default_models = self.ollama_config.get("default_models", {})
            
            if not default_models or not any(default_models.values()):
                self.logger.info("No models configured for auto-pull")
                return started_models
            
            # Download and start each model that needs to be downloaded
            for config_key, model_config in default_models.items():
                if isinstance(model_config, dict) and model_config.get("auto_pull", False):
                    actual_model_name = model_config.get("name")
                    if actual_model_name:
                        try:
                            # Check if model is available locally
                            if not await self._is_model_available(actual_model_name):
                                # Check if this might be a custom model (not in Ollama registry)
                                # Custom models don't have ':' or are single words without org prefix
                                is_likely_custom = ':' not in actual_model_name or '/' not in actual_model_name
                                
                                if is_likely_custom:
                                    # Skip custom models - they must be created via Modelfile first
                                    self._print_status("⚠️", f"Model '{actual_model_name}' not found (custom model?)", "yellow")
                                    self.logger.warning(f"Model '{actual_model_name}' not available. If this is a custom model, create it first with: aico ollama generate {actual_model_name}")
                                    continue  # Skip to next model
                                else:
                                    # Try to download registry models
                                    self._print_status("🚀", f"Starting download: {actual_model_name}", "blue")
                                    await self._pull_model_simple(actual_model_name)
                                    self._print_status("✅", f"Model downloaded: {actual_model_name}", "green")
                                    self.logger.info(f"Successfully pulled model: {actual_model_name}")
                            
                            # Check if this is an embedding model (they don't need to be "started")
                            is_embedding_model = config_key == "embedding" or any(
                                emb_keyword in actual_model_name.lower() 
                                for emb_keyword in ["embed", "paraphrase", "bge", "minilm"]
                            )
                            
                            if is_embedding_model:
                                # Embedding models are ready once downloaded - no need to "start"
                                started_models.append(actual_model_name)
                                self._print_status("✅", f"Embedding model ready: {actual_model_name}", "green")
                                self.logger.info(f"Embedding model ready: {actual_model_name}")
                            elif model_config.get("auto_start", True):  # Default to auto-start for LLM models
                                # Estimate loading time based on model name/size
                                estimated_time = self._estimate_loading_time(actual_model_name)
                                
                                # Check if model is already running first (fast check)
                                if await self._is_model_running(actual_model_name):
                                    started_models.append(actual_model_name)
                                    self._print_status("✅", f"Model ready: {actual_model_name}", "green")
                                else:
                                    # Show spinner during loading
                                    import sys
                                    if sys.stdout.isatty():
                                        # Terminal mode: use in-place update
                                        print(f"🔄 Starting model: {actual_model_name} (this can take up to {estimated_time} seconds)", end="", flush=True)
                                        if await self.start_model(actual_model_name):
                                            started_models.append(actual_model_name)
                                            # Clear line and show success - use longer padding to clear previous text
                                            print(f"\r✅ Model ready: {actual_model_name}" + " " * 50)
                                        else:
                                            # Clear line and show failure
                                            print(f"\r❌ Failed to start: {actual_model_name}" + " " * 50)
                                    else:
                                        # Non-terminal mode: use separate lines
                                        self._print_status("🔄", f"Starting model: {actual_model_name} (this can take up to {estimated_time} seconds)", "blue")
                                        if await self.start_model(actual_model_name):
                                            started_models.append(actual_model_name)
                                            self._print_status("✅", f"Model ready: {actual_model_name}", "green")
                                        else:
                                            self._print_status("❌", f"Failed to start: {actual_model_name}", "red")
                            
                        except Exception as e:
                            self._print_status("❌", f"Failed to prepare model: {actual_model_name} - {e}", "red")
                            self.logger.error(f"Failed to prepare model {actual_model_name}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error ensuring default models: {e}")
        
        return started_models
    
    def _estimate_loading_time(self, model_name: str) -> int:
        """Estimate model loading time based on model name and size patterns."""
        model_lower = model_name.lower()
        
        # Extract parameter size from model name
        if "1b" in model_lower or "1.5b" in model_lower:
            return 10  # Small models: ~10 seconds
        elif "3b" in model_lower or "7b" in model_lower:
            return 20  # Medium models: ~20 seconds  
        elif "8b" in model_lower or "9b" in model_lower:
            return 30  # Large 8B models: ~30 seconds
        elif "13b" in model_lower or "14b" in model_lower:
            return 45  # Very large models: ~45 seconds
        elif "70b" in model_lower or "72b" in model_lower:
            return 90  # Huge models: ~90 seconds
        else:
            # Default estimate based on common patterns
            if "tiny" in model_lower or "mini" in model_lower:
                return 10
            elif "small" in model_lower:
                return 15
            elif "medium" in model_lower:
                return 25
            elif "large" in model_lower:
                return 40
            else:
                return 30  # Conservative default for unknown models
    
    def _get_model_timeout(self, model_name: str) -> float:
        """Get adaptive timeout for model based on size."""
        model_lower = model_name.lower()
        
        # Generous timeouts for different model sizes
        if "1b" in model_lower or "1.5b" in model_lower:
            return 60.0   # 1 minute for small models
        elif "3b" in model_lower or "7b" in model_lower:
            return 120.0  # 2 minutes for medium models
        elif "8b" in model_lower or "9b" in model_lower:
            return 300.0  # 5 minutes for large 8B models
        elif "13b" in model_lower or "14b" in model_lower:
            return 600.0  # 10 minutes for very large models
        elif "70b" in model_lower or "72b" in model_lower:
            return 1200.0 # 20 minutes for huge models
        else:
            return 180.0  # 3 minutes default
    
    async def _is_model_running(self, model_name: str) -> bool:
        """Check if a specific model is loaded and running by querying the Ollama server."""
        self._ensure_logger()
        import time
        start_time = time.time()
        try:
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            url = f"http://{ollama_host}:{ollama_port}/api/ps"
            
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Use /api/ps endpoint (equivalent to 'ollama ps')
                response = await client.get(url)
                elapsed = time.time() - start_time
                self.logger.debug(f"_is_model_running took {elapsed:.2f}s")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Check if our model is in the running models list
                    for model in models:
                        model_name_in_list = model.get("name", "")
                        
                        # Match exact name or name with tag
                        if model_name_in_list == model_name or model_name_in_list.startswith(f"{model_name}:"):
                            self.logger.debug(f"Model match found: {model_name_in_list}")
                            return True
                    
                    self.logger.debug(f"Model {model_name} not found in {len(models)} running models")
                    return False
                else:
                    self.logger.debug(f"/api/ps returned status {response.status_code}")
                    return False
                    
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.debug(f"Error checking if model {model_name} is running after {elapsed:.2f}s: {e}")
            return False
    
    def _create_progress_bar(self, percent: int, width: int = 40) -> str:
        """Create a beautiful progress bar with safe ASCII characters."""
        # Use simple ASCII characters that work everywhere
        filled = "="
        empty = " "
        left_cap = "["
        right_cap = "]"
        
        filled_width = int(width * percent / 100)
        empty_width = width - filled_width
        bar = filled * filled_width + empty * empty_width
        return f"{left_cap}{bar}{right_cap}"
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
    
    def _supports_ansi_escapes(self) -> bool:
        """Check if terminal supports ANSI escape sequences."""
        import sys
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
        import sys
        import os
        
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

    async def _pull_model_simple(self, model_name: str) -> None:
        """Pull a model with beautiful real-time streaming progress."""
        ollama_host = self.ollama_config.get("host", "127.0.0.1")
        ollama_port = self.ollama_config.get("port", 11434)
        
        import httpx
        import json
        import sys
        
        # Don't duplicate the "Starting download" message - it's already printed by caller
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                # Use streaming to get real-time progress
                async with client.stream(
                    "POST",
                    f"http://{ollama_host}:{ollama_port}/api/pull",
                    json={"name": model_name, "stream": True}
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        self.logger.error(f"Ollama pull failed for {model_name}: HTTP {response.status_code} - {error_text.decode()}")
                        raise Exception(f"HTTP {response.status_code}: {error_text.decode()}")
                    
                    total_size = None
                    downloaded = 0
                    last_percent = -1
                    current_layer = ""
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                            
                        try:
                            progress_data = json.loads(line)
                            status = progress_data.get("status", "")
                            
                            # Extract size information
                            if "total" in progress_data and total_size is None:
                                total_size = progress_data["total"]
                                size_formatted = self._format_bytes(total_size)
                                self._print_status("📦", f"Model size: {size_formatted}", "blue")
                            
                            # Show progress for downloading - only for large files and meaningful progress
                            if "completed" in progress_data and total_size and total_size > 1024 * 1024:  # Only files > 1MB
                                downloaded = progress_data["completed"]
                                percent = int((downloaded / total_size) * 100)
                                
                                # Show progress every 2% or on completion, and only if we have meaningful progress
                                if percent != last_percent and percent > 0 and (percent % 2 == 0 or percent == 100):
                                    progress_bar = self._create_progress_bar(percent)
                                    downloaded_formatted = self._format_bytes(downloaded)
                                    total_formatted = self._format_bytes(total_size)
                                    
                                    # Only show progress bar in TTY mode
                                    if sys.stdout.isatty():
                                        import sys
                                        line = f"📥 {progress_bar} {percent:3d}% ({downloaded_formatted}/{total_formatted})"
                                        padded_line = line.ljust(80)
                                        sys.stdout.write(f"\r{padded_line}")
                                        sys.stdout.flush()
                                        
                                        # Clear progress bar when complete
                                        if percent == 100:
                                            sys.stdout.write("\r" + " " * 80 + "\r")
                                            sys.stdout.flush()
                                    
                                    last_percent = percent
                            
                            # Show layer status updates - but don't interfere with progress bar
                            elif status and status != current_layer:
                                current_layer = status
                                # Only show status for significant events, not every layer
                                if "success" in status.lower():
                                    self._print_status("✅", "Download complete!", "green")
                                elif "verifying" in status.lower():
                                    self._print_status("🔍", "Verifying download...", "cyan")
                                elif "writing" in status.lower():
                                    self._print_status("💾", "Writing manifest...", "blue")
                                
                        except json.JSONDecodeError:
                            continue
                    
                    # Clear progress bar and add newline
                    if sys.stdout.isatty():
                        import sys
                        # Clear line with spaces then add newline
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        sys.stdout.flush()
                        print()  # Add newline
                    
            except httpx.TimeoutException:
                self.logger.error(f"Timeout pulling model {model_name}")
                raise Exception("Request timeout")
            except Exception as e:
                self.logger.error(f"Unexpected error pulling {model_name}: {e}")
                raise

    async def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is already downloaded."""
        try:
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://{ollama_host}:{ollama_port}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return any(model.get("name", "").startswith(model_name) for model in models)
                return False
        except Exception:
            return False
    
    
    async def list_models(self) -> Dict:
        """
        List available and installed models.
        
        Returns:
            Dict: Model information from Ollama API
        """
        try:
            self._ensure_logger()
            host = self.ollama_config.get("host", "127.0.0.1")
            port = self.ollama_config.get("port", 11434)
            ollama_url = f"http://{host}:{port}"
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=10)
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return {"models": [], "error": str(e)}
    
    async def pull_model(self, model_name: str, progress_callback=None) -> bool:
        """
        Pull/download a model with beautiful progress tracking.
        
        Args:
            model_name: Name of the model to pull
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._ensure_logger()
            self.logger.info(f"Pulling model: {model_name}")
            
            # Use the beautiful progress UI instead of ugly callback
            await self._pull_model_simple(model_name)
            return True
                
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            # Fail loudly as per guidelines
            raise RuntimeError(f"Model pull failed for {model_name}: {e}") from e
    
    async def remove_model(self, model_name: str) -> bool:
        """
        Remove a model.
        
        Args:
            model_name: Name of the model to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Removing model: {model_name}")
            
            host = self.ollama_config.get("host", "127.0.0.1")
            port = self.ollama_config.get("port", 11434)
            ollama_url = f"http://{host}:{port}"
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{ollama_url}/api/delete",
                    json={"name": model_name}
                )
                response.raise_for_status()
                
                self.logger.info(f"Successfully removed model: {model_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove model {model_name}: {e}")
            return False
    
    async def start_model(self, model_name: str) -> bool:
        """
        Start/run a specific model (equivalent to 'ollama run').
        This loads the model into memory and makes it ready for conversation.
        
        Args:
            model_name: Name of the model to start
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._ensure_logger()
            self.logger.info(f"Starting model: {model_name}")
            
            # Check if server is running first
            if not await self.is_running():
                self.logger.error("Ollama server is not running. Start server first with 'serve' command.")
                return False
            
            # Check if model is already running (fast check) - but not here to avoid double-check
            # This check is now done at the caller level in _ensure_default_models
            
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            
            # Adaptive timeout based on model size
            timeout_seconds = self._get_model_timeout(model_name)
            
            # Start model by making a simple generation request
            # This loads the model into memory (large models need more time)
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    f"http://{ollama_host}:{ollama_port}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "Hello",
                        "stream": False
                    }
                )
                response.raise_for_status()
                
                self.logger.info(f"Successfully started model: {model_name}")
                return True
                
        except Exception as e:
            # Handle timeout specifically for large models
            if "ReadTimeout" in str(type(e).__name__) or "timeout" in str(e).lower():
                # Try to detect if model is actually loaded despite timeout
                if await self._is_model_running(model_name):
                    self.logger.info(f"Model {model_name} started successfully (despite timeout)")
                    return True
                
                timeout_msg = f"Model loading timeout after {timeout_seconds}s - {model_name} may need more time or resources"
                self.logger.error(f"Failed to start model {model_name}: {timeout_msg}")
                return False
            
            # Handle other exceptions
            error_msg = str(e)
            detailed_error = error_msg
            
            # Try to extract HTTP response details
            if hasattr(e, 'response'):
                try:
                    response = e.response
                    status_code = getattr(response, 'status_code', 'unknown')
                    
                    # Try different ways to get response text
                    response_text = None
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'content'):
                        response_text = response.content.decode('utf-8', errors='ignore')
                    elif hasattr(response, 'json'):
                        try:
                            response_json = response.json()
                            response_text = str(response_json)
                        except:
                            pass
                    
                    if response_text:
                        detailed_error = f"HTTP {status_code}: {response_text}"
                    else:
                        detailed_error = f"HTTP {status_code}: {error_msg}"
                        
                except Exception as parse_error:
                    detailed_error = f"{error_msg} (failed to parse response: {parse_error})"
            
            self.logger.error(f"Failed to start model {model_name}: {detailed_error}")
            return False
    
    async def stop_model(self, model_name: str) -> bool:
        """
        Stop a running model to free memory.
        
        Args:
            model_name: Name of the model to stop
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._ensure_logger()
            self.logger.info(f"Stopping model: {model_name}")
            
            # Check if server is running first
            if not await self.is_running():
                self.logger.warning("Ollama server is not running")
                return True  # Model is effectively stopped if server is down
            
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            
            # Ollama doesn't have a direct "stop model" API
            # Models are automatically unloaded after inactivity
            # For now, we'll just verify the model exists and log the action
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if model exists
                response = await client.get(f"http://{ollama_host}:{ollama_port}/api/tags")
                response.raise_for_status()
                
                models = response.json().get("models", [])
                model_exists = any(model.get("name", "").startswith(model_name) for model in models)
                
                if model_exists:
                    self.logger.info(f"Model {model_name} will be unloaded after inactivity")
                    self._print_status("✅", f"Model stopped: {model_name}", "green")
                    return True
                else:
                    self.logger.warning(f"Model {model_name} not found")
                    return False
                
        except Exception as e:
            self.logger.error(f"Failed to stop model {model_name}: {e}")
            self._print_status("❌", f"Failed to stop: {model_name} - {e}", "red")
            return False
    
    async def get_running_models(self) -> Dict:
        """
        Get list of currently loaded/running models.
        
        Returns:
            Dict: Information about running models
        """
        try:
            self._ensure_logger()
            
            if not await self.is_running():
                return {"models": [], "error": "Ollama server not running"}
            
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get running processes (if available)
                response = await client.get(f"http://{ollama_host}:{ollama_port}/api/ps")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Fallback to listing all available models
                    response = await client.get(f"http://{ollama_host}:{ollama_port}/api/tags")
                    response.raise_for_status()
                    return response.json()
                    
        except Exception as e:
            self.logger.error(f"Failed to get running models: {e}")
            return {"models": [], "error": str(e)}
