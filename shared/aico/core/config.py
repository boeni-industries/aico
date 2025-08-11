"""
AICO Configuration Management System

Provides unified, hierarchical configuration management across all AICO subsystems
with encryption, validation, and hot reloading capabilities.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

import jsonschema


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation errors."""
    pass


@dataclass
class ConfigSource:
    """Configuration source metadata."""
    name: str
    priority: int
    path: Optional[Path] = None
    data: Optional[Dict[str, Any]] = None


class ConfigurationManager:
    """
    Unified configuration management for AICO.
    
    Provides hierarchical configuration loading with the following priority order:
    1. Default Values (lowest priority)
    2. Environment Configuration Files
    3. User Configuration Files  
    4. Environment Variables
    5. Runtime Configuration Changes (highest priority)
    
    Features:
    - Dot-notation access (e.g., 'api.port', 'personality.traits.openness')
    - Schema validation using JSON Schema
    - Hot reloading with file watchers
    - Encrypted storage for sensitive configuration
    - Audit trail for configuration changes
    
    This class implements a singleton pattern to prevent multiple file watchers
    on the same directory, which causes issues on macOS FSEvents.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config_dir: Path = None):
        if cls._instance is None:
            cls._instance = super(ConfigurationManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: Path = None):
        """
        Initialize ConfigurationManager.
        
        Args:
            config_dir: Configuration directory path. Defaults to project root config
        """
        # Only initialize once for singleton
        if ConfigurationManager._initialized:
            return
            
        if config_dir is None:
            # Find project root by looking for config directory
            current = Path(__file__).parent
            while current.parent != current:  # Not at filesystem root
                config_path = current.parent / "config"
                if config_path.exists():
                    config_dir = config_path
                    break
                current = current.parent
            else:
                # Fallback to relative path
                config_dir = Path("./config")
        
        self.config_dir = config_dir
        self.schemas: Dict[str, Dict] = {}
        self.config_cache: Dict[str, Any] = {}
        self.sources: List[ConfigSource] = []
        self.watchers: List[Observer] = []
        self.encryption_key: Optional[bytes] = None
        self._instance_initialized = False
        
    def initialize(self, encryption_key: Optional[bytes] = None, lightweight: bool = False) -> None:
        """
        Initialize configuration system.
        
        Args:
            encryption_key: Optional encryption key for sensitive configuration
            lightweight: If True, skip heavy operations like file watchers for simple commands
        """
        if self._instance_initialized:
            return
            
        self.encryption_key = encryption_key
        self._ensure_directories()
        self._load_schemas()
        self._load_configurations()
        
        # Skip file watchers in lightweight mode (for --help, version, etc.)
        if not lightweight:
            self._setup_file_watchers()
            
        self._instance_initialized = True
        ConfigurationManager._initialized = True
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'api.port')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._instance_initialized:
            self.initialize()
            
        keys = key.split('.')
        value = self.config_cache
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
            persist: Whether to persist change to storage
        """
        if not self._initialized:
            self.initialize()
            
        keys = key.split('.')
        config = self.config_cache
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set value
        old_value = config.get(keys[-1])
        config[keys[-1]] = value
        
        # Log configuration change
        self._log_config_change(key, old_value, value)
        
        if persist:
            self._persist_configuration()
            
    def validate(self, domain: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.
        
        Args:
            domain: Configuration domain (e.g., 'core', 'security')
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ConfigurationValidationError: If validation fails with details
        """
        if domain not in self.schemas:
            raise ConfigurationError(f"Unknown configuration domain: {domain}")
            
        try:
            jsonschema.validate(config, self.schemas[domain])
            return True
        except jsonschema.ValidationError as e:
            raise ConfigurationValidationError(f"Validation failed for domain '{domain}': {e.message}")
            
    def reload(self) -> None:
        """Reload all configuration from files."""
        self.config_cache.clear()
        self.sources.clear()
        self._load_configurations()
        
    def export_config(self, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export configuration for backup or transfer.
        
        Args:
            domains: Optional list of domains to export. If None, exports all.
            
        Returns:
            Configuration dictionary
        """
        if not self._initialized:
            self.initialize()
            
        if domains is None:
            return self.config_cache.copy()
        
        return {
            domain: self.config_cache.get(domain, {})
            for domain in domains
        }
        
    def import_config(self, config: Dict[str, Any], validate: bool = True) -> None:
        """
        Import configuration from backup or transfer.
        
        Args:
            config: Configuration dictionary to import
            validate: Whether to validate against schemas
        """
        if validate:
            for domain, domain_config in config.items():
                if domain in self.schemas:
                    self.validate(domain, domain_config)
                    
        # Deep merge imported configuration
        self._deep_merge(self.config_cache, config)
        self._persist_configuration()
        
    def get_domains(self) -> List[str]:
        """Get list of available configuration domains."""
        return list(self.schemas.keys())
        
    def get_schema(self, domain: str) -> Dict[str, Any]:
        """
        Get schema for a configuration domain.
        
        Args:
            domain: Configuration domain name
            
        Returns:
            JSON Schema dictionary
        """
        if domain not in self.schemas:
            raise ConfigurationError(f"Unknown configuration domain: {domain}")
        return self.schemas[domain].copy()
        
    def _ensure_directories(self) -> None:
        """Ensure required configuration directories exist."""
        directories = [
            self.config_dir,
            self.config_dir / "schemas",
            self.config_dir / "defaults", 
            self.config_dir / "environments",
            self.config_dir / "user",
            self.config_dir / "user" / "plugins"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def _load_schemas(self) -> None:
        """Load all configuration schemas."""
        schema_dir = self.config_dir / "schemas"
        
        for schema_file in schema_dir.glob("*.schema.json"):
            domain = schema_file.stem.replace(".schema", "")
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    self.schemas[domain] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                raise ConfigurationError(f"Failed to load schema '{schema_file}': {e}")
                
    def _load_configurations(self) -> None:
        """Load configuration from all sources in hierarchy order."""
        # 1. Load defaults
        self._load_default_configs()
        
        # 2. Load environment-specific configs
        self._load_environment_configs()
        
        # 3. Load user overrides
        self._load_user_configs()
        
        # 4. Apply environment variables
        self._apply_environment_variables()
        
        # 5. Load runtime configurations (if encrypted storage exists)
        self._load_runtime_configs()
        
    def _load_default_configs(self) -> None:
        """Load default configuration values."""
        defaults_dir = self.config_dir / "defaults"
        
        for config_file in defaults_dir.glob("*.yaml"):
            domain = config_file.stem
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    self.config_cache[domain] = config
                    self.sources.append(ConfigSource(
                        name=f"defaults/{domain}",
                        priority=1,
                        path=config_file,
                        data=config
                    ))
            except (yaml.YAMLError, IOError) as e:
                raise ConfigurationError(f"Failed to load default config '{config_file}': {e}")
                
    def _load_environment_configs(self) -> None:
        """Load environment-specific configurations."""
        # Get environment directly from cache to avoid circular dependency during initialization
        env = self.config_cache.get("system", {}).get("environment", "development")
        env_file = self.config_dir / "environments" / f"{env}.yaml"
        
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_config = yaml.safe_load(f) or {}
                    self._deep_merge(self.config_cache, env_config)
                    self.sources.append(ConfigSource(
                        name=f"environment/{env}",
                        priority=2,
                        path=env_file,
                        data=env_config
                    ))
            except (yaml.YAMLError, IOError) as e:
                raise ConfigurationError(f"Failed to load environment config '{env_file}': {e}")
                
    def _load_user_configs(self) -> None:
        """Load user override configurations."""
        user_dir = self.config_dir / "user"
        
        for config_file in user_dir.glob("*.yaml"):
            domain = config_file.stem
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                    if domain in self.config_cache:
                        self._deep_merge(self.config_cache[domain], user_config)
                    else:
                        self.config_cache[domain] = user_config
                    self.sources.append(ConfigSource(
                        name=f"user/{domain}",
                        priority=3,
                        path=config_file,
                        data=user_config
                    ))
            except (yaml.YAMLError, IOError) as e:
                raise ConfigurationError(f"Failed to load user config '{config_file}': {e}")
                
    def _apply_environment_variables(self) -> None:
        """Apply environment variable overrides."""
        # Map environment variables to configuration keys
        env_mappings = {
            "AICO_LOG_LEVEL": "system.log_level",
            "AICO_API_PORT": "api.port",
            "AICO_ENVIRONMENT": "system.environment",
            "AICO_API_HOST": "api.host",
            # Path-related environment variables are handled by AICOPaths class
            # AICO_DATA_DIR, AICO_CONFIG_DIR, etc. are used directly by AICOPaths
        }
        
        env_overrides = {}
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Try to parse as JSON for complex values, fallback to string
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                env_overrides[config_key] = parsed_value
                
        if env_overrides:
            self.sources.append(ConfigSource(
                name="environment_variables",
                priority=4,
                data=env_overrides
            ))
            
            # Apply environment variable overrides
            for key, value in env_overrides.items():
                self.set(key, value, persist=False)
                
    def _load_runtime_configs(self) -> None:
        """Load runtime configuration changes from encrypted store."""
        # TODO: Implement encrypted runtime configuration storage
        # This will be implemented when we add the encryption layer
        pass
        
    def _persist_configuration(self) -> None:
        """Persist current configuration to encrypted store."""
        # TODO: Implement encrypted configuration persistence
        # This will be implemented when we add the encryption layer
        pass
        
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """
        Deep merge override dictionary into base dictionary.
        
        Args:
            base: Base dictionary to merge into
            override: Override dictionary to merge from
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
                
    def _setup_file_watchers(self) -> None:
        """Setup file system watchers for hot reloading."""
        # Lazy import watchdog only when file watchers are actually needed
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, config_manager):
                self.config_manager = config_manager
                
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(('.yaml', '.yml', '.json')):
                    try:
                        self.config_manager.reload()
                    except Exception as e:
                        # Log error but don't crash
                        print(f"Error reloading configuration: {e}")
                        
        handler = ConfigFileHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.config_dir), recursive=True)
        observer.start()
        self.watchers.append(observer)
        
    def _log_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Log configuration change for audit trail.
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        # TODO: Implement audit logging
        # This will be implemented when we add the audit system
        pass
        
    @classmethod
    def reset_singleton(cls):
        """Reset singleton instance for testing or cleanup."""
        if cls._instance is not None:
            # Clean up watchers before resetting
            for watcher in cls._instance.watchers:
                try:
                    watcher.stop()
                    watcher.join()
                except:
                    pass  # Ignore cleanup errors
            cls._instance = None
            cls._initialized = False
    
    def __del__(self):
        """Cleanup file watchers on destruction."""
        for watcher in self.watchers:
            try:
                watcher.stop()
                watcher.join()
            except:
                pass  # Ignore cleanup errors during destruction
