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
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from shared.aico.core.logging import get_logger
from shared.aico.core.config import ConfigurationManager
from shared.aico.core.paths import get_aico_root_path


class OllamaManager:
    """Manages Ollama binary installation, updates, and process lifecycle."""
    
    # GitHub API configuration
    GITHUB_API_URL = "https://api.github.com/repos/ollama/ollama/releases/latest"
    GITHUB_RELEASES_URL = "https://github.com/ollama/ollama/releases/download"
    
    # Platform-specific binary mappings
    PLATFORM_BINARIES = {
        "Windows": "ollama-windows-amd64.zip",
        "Darwin": "ollama-darwin",  # Universal binary
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
        
        # The configuration is in core.yaml, loaded under the 'core' key
        # Access it as: core.modelservice.ollama
        self.ollama_config = self.config_manager.get("core.modelservice.ollama", {})
        self.logs_dir = self.aico_root / "logs"
        self.ollama_process: Optional[subprocess.Popen] = None
        
        # Ensure directories exist
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform detection
        self.platform = platform.system()
        self.ollama_binary = self._get_ollama_binary_path()
    
    def _ensure_logger(self):
        """Ensure logger is initialized (lazy initialization)."""
        if self.logger is None:
            from aico.core.logging import get_logger
            self.logger = get_logger("externals", "ollama")

    def _get_ollama_binary_path(self) -> Path:
        """Get the expected path to the Ollama binary for this platform."""
        if self.platform == "Windows":
            return self.bin_dir / "ollama.exe"
        else:
            return self.bin_dir / "ollama"
    
    async def ensure_installed(self, force_update: bool = False) -> bool:
        """Ensure Ollama is installed and up to date, respecting config settings."""
        try:
            self._ensure_logger()
            # Check config for auto_install setting
            if not self.ollama_config.get("auto_install", True) and not force_update:
                self.logger.info("Auto-install disabled in config, skipping installation")
                return await self._is_ollama_installed()
            
            if not force_update and await self._is_ollama_installed():
                self.logger.info("Ollama already installed")
                return True
            
            self.logger.info("Installing/updating Ollama...")
            print("    → Downloading Ollama binary...")
            
            # Get latest release info
            release_info = await self._get_release_info()
            if not release_info:
                self.logger.error("Failed to get Ollama release information")
                return False
            
            # Get platform-specific download info
            download_url, binary_name = self._get_download_info(release_info)
            if not download_url:
                self.logger.error("No suitable download found for this platform")
                return False
            
            # Download and install
            success = await self._download_and_install(download_url, binary_name)
            if success:
                self.logger.info(f"Ollama {release_info['tag_name']} installed successfully")
                return True
            else:
                self.logger.error("Failed to install Ollama")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to ensure Ollama installation: {type(e).__name__}: {e}")
            self.logger.debug(f"Installation error details", exc_info=True)
            return False
    
    async def _is_ollama_installed(self) -> bool:
        """Check if Ollama binary exists and is executable."""
        self._ensure_logger()
        
        if not self.ollama_binary.exists():
            self.logger.error(f"Ollama binary not found at expected path: {self.ollama_binary}")
            return False
        
        file_size = self.ollama_binary.stat().st_size
        self.logger.debug(f"Found Ollama binary: {self.ollama_binary} ({file_size:,} bytes)")
            
        # Test if binary is executable
        try:
            import subprocess
            result = subprocess.run(
                [str(self.ollama_binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip() if result.stdout else "unknown"
                self.logger.info(f"Ollama binary verification successful: {version_info}")
                return True
            else:
                self.logger.error(f"Ollama binary version check failed (exit code {result.returncode})")
                if result.stderr:
                    self.logger.error(f"Version check stderr: {result.stderr.strip()}")
                if result.stdout:
                    self.logger.debug(f"Version check stdout: {result.stdout.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Ollama binary version check timed out after 10 seconds")
            return False
        except Exception as e:
            self.logger.error(f"Failed to execute Ollama binary version check: {type(e).__name__}: {e}")
            return False
    
    async def _should_update(self) -> bool:
        """Check if Ollama should be updated to latest version."""
        try:
            # Get current version
            current_version = await self._get_current_version()
            if not current_version:
                return True
                
            # Get latest version from GitHub
            latest_version = await self._get_latest_version()
            if not latest_version:
                return False
                
            self.logger.debug(f"Current: {current_version}, Latest: {latest_version}")
            return current_version != latest_version
            
        except Exception as e:
            self.logger.warning(f"Could not check for updates: {e}")
            return False
    
    async def _get_current_version(self) -> Optional[str]:
        """Get currently installed Ollama version."""
        try:
            import subprocess
            result = subprocess.run(
                [str(self.ollama_binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout:
                # Parse version from output like "ollama version is 0.11.8"
                version_line = result.stdout.strip()
                if "version is" in version_line:
                    return version_line.split("version is")[-1].strip()
                return version_line
            return None
        except Exception:
            return None
    
    async def _get_latest_version(self) -> Optional[str]:
        """Get latest Ollama version from GitHub releases."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.GITHUB_API_URL)
                response.raise_for_status()
                
                release_data = response.json()
                return release_data.get("tag_name", "").lstrip("v")
                
        except Exception as e:
            self.logger.error(f"Failed to get latest version: {e}")
            return None
    
    async def _install_ollama(self) -> bool:
        """Download and install Ollama binary."""
        try:
            # Get release information
            release_info = await self._get_release_info()
            if not release_info:
                return False
                
            binary_name = self.PLATFORM_BINARIES.get(self.platform)
            if not binary_name:
                self.logger.error(f"Unsupported platform: {self.platform}")
                return False
            
            # Find download URL for our platform
            download_url = None
            for asset in release_info.get("assets", []):
                if asset["name"] == binary_name:
                    download_url = asset["browser_download_url"]
                    break
            
            if not download_url:
                self.logger.error(f"No binary found for platform: {self.platform}")
                return False
            
            # Download and install
            self.logger.info(f"Downloading Ollama from {download_url}")
            return await self._download_and_install(download_url, binary_name)
            
        except Exception as e:
            self.logger.error(f"Failed to install Ollama: {e}")
            return False
    
    async def _get_release_info(self) -> Optional[Dict]:
        """Get latest release information from GitHub."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.GITHUB_API_URL)
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to get release info: {e}")
            return None
    
    def _get_download_info(self, release_info: Dict) -> tuple[Optional[str], Optional[str]]:
        """Extract platform-specific download URL and binary name from release info."""
        assets = release_info.get("assets", [])
        
        # Platform-specific asset patterns
        if self.platform == "Windows":
            pattern = "windows-amd64.zip"
            binary_name = "ollama-windows-amd64.zip"
        elif self.platform == "Darwin":
            pattern = "darwin"
            binary_name = "ollama-darwin"
        elif self.platform == "Linux":
            pattern = "linux-amd64"
            binary_name = "ollama-linux-amd64"
        else:
            return None, None
        
        # Find matching asset
        for asset in assets:
            if pattern in asset["name"]:
                return asset["browser_download_url"], asset["name"]
        
        return None, None
    
    async def _download_and_install(self, download_url: str, binary_name: str) -> bool:
        """Download and install Ollama binary."""
        try:
            temp_file = self.bin_dir / f"temp_{binary_name}"
            
            # Download file
            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    
                    with open(temp_file, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
            
            # Handle different file types
            if binary_name.endswith(".zip"):
                # Windows zip file
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    # Extract ollama.exe
                    zip_ref.extract("ollama.exe", self.bin_dir)
                temp_file.unlink()  # Remove zip file
                # Ensure the extracted binary is executable
                self.ollama_binary.chmod(0o755)
            else:
                # Unix binary - move and make executable
                shutil.move(str(temp_file), str(self.ollama_binary))
                self.ollama_binary.chmod(0o755)
            
            self.logger.info("Ollama binary installed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Ollama download/installation failed: {type(e).__name__}: {e}")
            self.logger.debug(f"Download error details", exc_info=True)
            
            # Cleanup on failure
            try:
                if 'temp_file' in locals() and temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            return False
    
    async def is_running(self) -> bool:
        """Check if Ollama server is running and responding."""
        try:
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{ollama_host}:{ollama_port}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def start_ollama(self) -> bool:
        """Start Ollama server if not already running, respecting config settings."""
        try:
            self._ensure_logger()
            # Check config for auto_start setting
            if not self.ollama_config.get("auto_start", True):
                self.logger.info("Auto-start disabled in config, skipping Ollama startup")
                return False
            
            if not await self._is_ollama_installed():
                self.logger.error("Ollama not installed, cannot start")
                return False
            
            if await self.is_running():
                self.logger.info("✓ Ollama server already running - skipping startup")
                print("    ✓ Found existing Ollama server")
                return True
            
            self.logger.info("Starting Ollama server...")
            
            # Start Ollama server with config-based environment
            env = os.environ.copy()
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            env["OLLAMA_HOST"] = f"{ollama_host}:{ollama_port}"
            env["OLLAMA_MODELS"] = str(self.models_dir)
            
            # Start process
            self.ollama_process = subprocess.Popen(
                [str(self.ollama_binary), "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.bin_dir)
            )
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            # Verify server startup
            if await self.is_running():
                self.logger.info(f"✓ Ollama server started successfully on {ollama_host}:{ollama_port}")
                
                # Auto-pull default models after server is running
                await self._ensure_default_models()
                return True
            else:
                # Collect detailed error information
                error_details = []
                
                if self.ollama_process:
                    if self.ollama_process.poll() is not None:
                        # Process has terminated
                        exit_code = self.ollama_process.returncode
                        error_details.append(f"Process exited with code {exit_code}")
                        
                        try:
                            stdout, stderr = self.ollama_process.communicate(timeout=1)
                            if stderr:
                                stderr_text = stderr.decode().strip()
                                error_details.append(f"stderr: {stderr_text}")
                            if stdout:
                                stdout_text = stdout.decode().strip()
                                error_details.append(f"stdout: {stdout_text}")
                        except subprocess.TimeoutExpired:
                            error_details.append("Could not retrieve process output (timeout)")
                    else:
                        error_details.append("Process is still running but not responding to health checks")
                else:
                    error_details.append("Process handle is None")
                
                # Check if port is already in use
                try:
                    import socket
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        result = s.connect_ex((ollama_host, ollama_port))
                        if result == 0:
                            error_details.append(f"Port {ollama_port} appears to be in use by another process")
                except Exception:
                    pass
                
                error_msg = "Ollama server failed to start"
                if error_details:
                    error_msg += f": {'; '.join(error_details)}"
                
                self.logger.error(error_msg)
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error during Ollama startup: {type(e).__name__}: {e}")
            self.logger.debug(f"Ollama startup exception details", exc_info=True)
            return False
    
    async def stop_ollama(self) -> bool:
        """Stop the Ollama server process."""
        if not self.ollama_process:
            return True
            
        try:
            self.logger.info("Stopping Ollama server...")
            
            # Try graceful shutdown first
            self.ollama_process.terminate()
            
            try:
                await asyncio.wait_for(self.ollama_process.wait(), timeout=10)
                self.logger.info("Ollama stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                self.logger.warning("Ollama did not stop gracefully, forcing shutdown")
                self.ollama_process.kill()
                await self.ollama_process.wait()
                
            self.ollama_process = None
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Ollama: {e}")
            return False
    
    async def _health_check(self) -> bool:
        """Check if Ollama API is responding using config URL."""
        try:
            ollama_url = self.ollama_config.get("url", "http://127.0.0.1:11434")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=5)
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def get_status(self) -> Dict:
        """
        Get comprehensive Ollama status information.
        
        Returns:
            Dict: Status information including process state, version, models
        """
        status = {
            "installed": await self._is_ollama_installed(),
            "running": False,
            "healthy": False,
            "version": await self._get_current_version(),
            "binary_path": str(self.ollama_binary),
            "models_dir": str(self.models_dir),
            "process_id": None
        }
        
        if self.ollama_process and self.ollama_process.poll() is None:
            status["running"] = True
            status["process_id"] = self.ollama_process.pid
            status["healthy"] = await self._health_check()
        
        return status
    
    async def _ensure_default_models(self) -> None:
        """Auto-pull default models based on config settings."""
        try:
            self._ensure_logger()
            default_models = self.ollama_config.get("default_models", {})
            
            if not default_models or not any(default_models.values()):
                self.logger.info("No models configured for auto-pull")
                return
            
            # Download each model that needs to be downloaded
            for config_key, model_config in default_models.items():
                if isinstance(model_config, dict) and model_config.get("auto_pull", False):
                    actual_model_name = model_config.get("name")
                    if actual_model_name and not await self._is_model_available(actual_model_name):
                        try:
                            self._print_status("🚀", f"Starting download: {actual_model_name}", "blue")
                            await self._pull_model_simple(actual_model_name)
                            self._print_status("✅", f"Model ready: {actual_model_name}", "green")
                            self.logger.info(f"Successfully pulled model: {actual_model_name}")
                        except Exception as e:
                            self._print_status("❌", f"Failed to download: {actual_model_name} - {e}", "red")
                            self.logger.error(f"Failed to pull model {actual_model_name}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error ensuring default models: {e}")
    
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
            ollama_url = self.ollama_config.get("url", "http://127.0.0.1:11434")
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
            
            ollama_url = self.ollama_config.get("url", "http://127.0.0.1:11434")
            
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
