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
        # Uses "externals.ollama" log level from config
        self.logger = get_logger("externals", "ollama")
        self.aico_root = get_aico_root_path()
        self.bin_dir = self.aico_root / "bin"
        self.models_dir = self.aico_root / "models"
        
        # Load configuration
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize()
        self.ollama_config = self.config_manager.get("modelservice", {}).get("ollama", {})
        self.logs_dir = self.aico_root / "logs"
        self.ollama_process: Optional[subprocess.Popen] = None
        
        # Ensure directories exist
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform detection
        self.platform = platform.system()
        self.ollama_binary = self._get_ollama_binary_path()
        
    def _get_ollama_binary_path(self) -> Path:
        """Get the expected path to the Ollama binary for this platform."""
        if self.platform == "Windows":
            return self.bin_dir / "ollama.exe"
        else:
            return self.bin_dir / "ollama"
    
    async def ensure_installed(self, force_update: bool = False) -> bool:
        """Ensure Ollama is installed and up to date, respecting config settings."""
        try:
            # Check config for auto_install setting
            if not self.ollama_config.get("auto_install", True) and not force_update:
                self.logger.info("Auto-install disabled in config, skipping installation")
                return self.is_installed()
            
            if not force_update and self.is_installed():
                self.logger.info("Ollama already installed")
                
                # Auto-pull default models if configured
                await self._ensure_default_models()
                return True
            
            self.logger.info("Installing/updating Ollama...")
            
            # Get latest release info
            release_info = await self._get_latest_release()
            if not release_info:
                self.logger.error("Failed to get Ollama release information")
                return False
            
            # Download and install
            success = await self._download_and_install(release_info)
            if success:
                self.logger.info(f"Ollama {release_info['tag_name']} installed successfully")
                
                # Auto-pull default models after installation
                await self._ensure_default_models()
                return True
            else:
                self.logger.error("Failed to install Ollama")
                return False
                
        except Exception as e:
            self.logger.error(f"Error ensuring Ollama installation: {e}")
            return False
    
    async def _is_ollama_installed(self) -> bool:
        """Check if Ollama binary exists and is executable."""
        if not self.ollama_binary.exists():
            return False
            
        # Test if binary is executable
        try:
            result = await asyncio.create_subprocess_exec(
                str(self.ollama_binary), "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except Exception:
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
            result = await asyncio.create_subprocess_exec(
                str(self.ollama_binary), "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                # Parse version from output like "ollama version is 0.1.XX"
                version_line = stdout.decode().strip()
                if "version is" in version_line:
                    return version_line.split("version is")[-1].strip()
                    
        except Exception as e:
            self.logger.debug(f"Could not get current version: {e}")
            
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
    
    async def _download_and_install(self, download_url: str, binary_name: str) -> bool:
        """Download and install Ollama binary."""
        try:
            temp_file = self.bin_dir / f"temp_{binary_name}"
            
            # Download file
            async with httpx.AsyncClient() as client:
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
            else:
                # Unix binary - move and make executable
                shutil.move(str(temp_file), str(self.ollama_binary))
                self.ollama_binary.chmod(0o755)
            
            self.logger.info("Ollama binary installed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download and install: {e}")
            # Cleanup on failure
            if temp_file.exists():
                temp_file.unlink()
            return False
    
    async def start_ollama(self) -> bool:
        """Start the Ollama server process, respecting config settings."""
        try:
            # Check config for auto_start setting
            if not self.ollama_config.get("auto_start", True):
                self.logger.info("Auto-start disabled in config, skipping Ollama startup")
                return False
            
            if not self.is_installed():
                self.logger.error("Ollama not installed, cannot start")
                return False
            
            if await self.is_running():
                self.logger.info("Ollama is already running")
                return True
            
            self.logger.info("Starting Ollama server...")
            
            # Start Ollama server with config-based environment
            env = os.environ.copy()
            env["OLLAMA_MODELS"] = str(self.models_dir)
            
            # Apply config settings to environment
            ollama_host = self.ollama_config.get("host", "127.0.0.1")
            ollama_port = self.ollama_config.get("port", 11434)
            env["OLLAMA_HOST"] = ollama_host
            env["OLLAMA_PORT"] = str(ollama_port)
            
            self.ollama_process = await asyncio.create_subprocess_exec(
                str(self.ollama_binary), "serve",
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for startup
            await asyncio.sleep(2)
            
            # Verify it's running
            if await self.is_running():
                self.logger.info(f"Ollama server started successfully on {ollama_host}:{ollama_port}")
                return True
            else:
                self.logger.error("Ollama server failed to start")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Ollama: {e}")
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
            default_models = self.ollama_config.get("default_models", {})
            
            for role, model_config in default_models.items():
                if model_config.get("auto_pull", False):
                    model_name = model_config.get("name")
                    if model_name:
                        self.logger.info(f"Auto-pulling default {role} model: {model_name}")
                        success = await self.pull_model(model_name)
                        if success:
                            self.logger.info(f"Successfully pulled {model_name}")
                        else:
                            self.logger.warning(f"Failed to pull {model_name}")
                            
        except Exception as e:
            self.logger.error(f"Error ensuring default models: {e}")
    
    async def list_models(self) -> Dict:
        """
        List available and installed models.
        
        Returns:
            Dict: Model information from Ollama API
        """
        try:
            ollama_url = self.ollama_config.get("url", "http://127.0.0.1:11434")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=10)
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return {"models": [], "error": str(e)}
    
    async def pull_model(self, model_name: str) -> bool:
        """
        Pull/download a model.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Pulling model: {model_name}")
            
            async with httpx.AsyncClient(timeout=300) as client:  # 5 minute timeout
                response = await client.post(
                    "http://127.0.0.1:11434/api/pull",
                    json={"name": model_name}
                )
                response.raise_for_status()
                
                # Stream the response to track progress
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "status" in data:
                                self.logger.info(f"Pull progress: {data['status']}")
                        except json.JSONDecodeError:
                            continue
                
                self.logger.info(f"Successfully pulled model: {model_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
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
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    "http://127.0.0.1:11434/api/delete",
                    json={"name": model_name}
                )
                response.raise_for_status()
                
                self.logger.info(f"Successfully removed model: {model_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove model {model_name}: {e}")
            return False
