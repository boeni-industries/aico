"""
Environment-Aware Credential Provider

Provides credentials with proper fallback chain for both local dev and containerized environments.
Prevents keyring blocking in non-interactive contexts.

Priority order:
1. Environment variables (AICO_<KEY_NAME>)
2. Docker/Kubernetes secrets (/run/secrets/<key_name>)
3. Encrypted local file (for persistent containers)
4. System keyring (local dev only, interactive only)
"""

import os
import sys
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CredentialProvider:
    """
    Non-blocking credential provider with environment-aware fallbacks.
    
    Designed to work in:
    - Local development (with keyring)
    - Docker containers (with env vars or secrets)
    - CI/CD pipelines (with env vars)
    - Non-interactive scripts (with env vars)
    """
    
    def __init__(self, service_name: str = "AICO"):
        self.service_name = service_name
        self._is_interactive = sys.stdin.isatty() and not os.getenv("AICO_NONINTERACTIVE")
        self._secrets_dir = Path("/run/secrets")  # Docker/K8s secrets
        
    def get(self, key_name: str, required: bool = False) -> Optional[str]:
        """
        Get credential with proper fallback chain.
        
        Args:
            key_name: Credential key name (e.g., "postgres_password", "jwt_secret")
            required: If True, raise error if credential not found
            
        Returns:
            Credential value or None
        """
        # 1. Environment variable (highest priority)
        env_var = f"AICO_{key_name.upper()}"
        if value := os.getenv(env_var):
            logger.debug(f"Credential '{key_name}' loaded from environment variable")
            return value
        
        # 2. Docker/Kubernetes secrets
        secret_file = self._secrets_dir / key_name.lower()
        if secret_file.exists():
            try:
                value = secret_file.read_text().strip()
                logger.debug(f"Credential '{key_name}' loaded from secrets file")
                return value
            except Exception as e:
                logger.warning(f"Failed to read secret file {secret_file}: {e}")
        
        # 3. System keyring (local dev only, interactive only)
        if self._is_interactive:
            try:
                import keyring
                value = keyring.get_password(self.service_name, key_name)
                if value:
                    logger.debug(f"Credential '{key_name}' loaded from system keyring")
                    return value
            except Exception as e:
                logger.debug(f"Keyring access failed for '{key_name}': {e}")
        
        # 4. Not found
        if required:
            raise ValueError(
                f"Required credential '{key_name}' not found. "
                f"Set {env_var} environment variable or configure keyring."
            )
        
        return None
    
    def set(self, key_name: str, value: str) -> bool:
        """
        Store credential (keyring only, for local dev).
        
        Args:
            key_name: Credential key name
            value: Credential value
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._is_interactive:
            logger.warning(
                f"Cannot store credential '{key_name}' in non-interactive mode. "
                f"Use environment variable AICO_{key_name.upper()} instead."
            )
            return False
        
        try:
            import keyring
            keyring.set_password(self.service_name, key_name, value)
            logger.info(f"Credential '{key_name}' stored in system keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential '{key_name}' in keyring: {e}")
            return False
    
    def delete(self, key_name: str) -> bool:
        """
        Delete credential from keyring (local dev only).
        
        Args:
            key_name: Credential key name
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._is_interactive:
            logger.warning(f"Cannot delete credential '{key_name}' in non-interactive mode")
            return False
        
        try:
            import keyring
            keyring.delete_password(self.service_name, key_name)
            logger.info(f"Credential '{key_name}' deleted from system keyring")
            return True
        except Exception as e:
            logger.debug(f"Failed to delete credential '{key_name}': {e}")
            return False
    
    def is_available(self, key_name: str) -> bool:
        """Check if credential is available without retrieving it."""
        return self.get(key_name) is not None
    
    @property
    def is_interactive(self) -> bool:
        """Check if running in interactive mode."""
        return self._is_interactive
    
    def get_source_info(self, key_name: str) -> dict:
        """Get information about where credential would be loaded from."""
        env_var = f"AICO_{key_name.upper()}"
        secret_file = self._secrets_dir / key_name.lower()
        
        info = {
            "key_name": key_name,
            "env_var": env_var,
            "env_var_set": bool(os.getenv(env_var)),
            "secret_file": str(secret_file),
            "secret_file_exists": secret_file.exists(),
            "keyring_available": self._is_interactive,
            "source": None
        }
        
        if info["env_var_set"]:
            info["source"] = "environment"
        elif info["secret_file_exists"]:
            info["source"] = "secrets_file"
        elif self._is_interactive:
            info["source"] = "keyring"
        
        return info
