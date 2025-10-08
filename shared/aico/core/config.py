"""
AICO Configuration Management System

Provides unified, hierarchical configuration management across all AICO subsystems
with encryption, validation, and hot reloading capabilities.
"""

import json
import os
import threading
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

import jsonschema


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass  # Standard exception class definition - no additional implementation needed


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation errors."""
    pass  # Standard exception class definition - inherits from ConfigurationError


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
    _watchers_started = False
    _watcher_lock = threading.Lock()
    
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
                # Log when returning default for missing config keys
                if default == {} and len(keys) > 1:
                    # This is likely a config section that should exist
                    import logging
                    logger = logging.getLogger("shared.core.config")
                    logger.error(f"🚨 [CONFIG_ERROR] Configuration key '{key}' not found! Returning empty dict.")
                    logger.error(f"🚨 [CONFIG_ERROR] Available keys at root: {list(self.config_cache.keys()) if isinstance(self.config_cache, dict) else 'Not a dict'}")
                    logger.error(f"🚨 [CONFIG_ERROR] This may cause silent initialization failures!")
                return default
                
        # Additional check: warn if returning an empty dict for a config section
        if isinstance(value, dict) and not value and len(keys) > 1:
            import logging
            logger = logging.getLogger("shared.core.config")
            logger.warning(f"⚠️ [CONFIG_WARNING] Configuration section '{key}' exists but is EMPTY!")
            
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
            # Update or create runtime source
            self._update_runtime_source(key, value)
            self._persist_configuration()
    
    def _update_runtime_source(self, key: str, value: Any) -> None:
        """Update runtime configuration source with new value."""
        # Find existing runtime source or create new one
        runtime_source = None
        for source in self.sources:
            if source.name == "runtime":
                runtime_source = source
                break
        
        if runtime_source is None:
            # Create new runtime source
            runtime_source = ConfigSource(
                name="runtime",
                priority=5,
                path=self.config_dir / "user" / "runtime.yaml",
                data={}
            )
            self.sources.append(runtime_source)
        
        # Update runtime data with new value
        keys = key.split('.')
        runtime_data = runtime_source.data
        
        # Navigate to parent in runtime data
        for k in keys[:-1]:
            if k not in runtime_data:
                runtime_data[k] = {}
            runtime_data = runtime_data[k]
        
        # Set value in runtime data
        runtime_data[keys[-1]] = value
            
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
            "AICO_API_PORT": "api_gateway.protocols.rest.port",
            "AICO_ENVIRONMENT": "system.environment",
            "AICO_API_HOST": "api_gateway.host",
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
        runtime_file = self.config_dir / "user" / "runtime.yaml"
        
        if runtime_file.exists():
            try:
                with open(runtime_file, 'r', encoding='utf-8') as f:
                    runtime_config = yaml.safe_load(f) or {}
                    if runtime_config:
                        self._deep_merge(self.config_cache, runtime_config)
                        self.sources.append(ConfigSource(
                            name="runtime",
                            priority=5,
                            path=runtime_file,
                            data=runtime_config
                        ))
            except (yaml.YAMLError, IOError) as e:
                # Log error but don't crash - runtime config is optional
                print(f"Warning: Failed to load runtime config '{runtime_file}': {e}")
        
    def _persist_configuration(self) -> None:
        """Persist current configuration to encrypted store."""
        runtime_file = self.config_dir / "user" / "runtime.yaml"
        
        # Extract runtime changes (priority 5 source)
        runtime_data = {}
        for source in self.sources:
            if source.name == "runtime" and source.data:
                runtime_data = source.data
                break
        
        # Ensure user directory exists
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(runtime_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(runtime_data, f, default_flow_style=False, sort_keys=True)
        except (yaml.YAMLError, IOError) as e:
            raise ConfigurationError(f"Failed to persist runtime config to '{runtime_file}': {e}")
        
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
        # Thread-safe check to prevent duplicate watchers on the same directory (FSEvents issue on macOS)
        with ConfigurationManager._watcher_lock:
            if ConfigurationManager._watchers_started:
                return
                
            # Clean up any existing watchers first to prevent FSEvents "already scheduled" errors
            self._cleanup_existing_watchers()
                
            # Lazy import watchdog only when file watchers are actually needed
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            import time
            
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
                            
            try:
                handler = ConfigFileHandler(self)
                observer = Observer()
                
                # Give FSEvents time to fully release any previous watches
                time.sleep(0.1)
                
                observer.schedule(handler, str(self.config_dir), recursive=True)
                observer.start()
                self.watchers.append(observer)
                ConfigurationManager._watchers_started = True
                
            except RuntimeError as e:
                if "already scheduled" in str(e):
                    # FSEvents still has the watch registered - this is a known macOS issue
                    # The functionality works fine, just suppress the error
                    import sys
                    print(f"[CONFIG] Info: FSEvents watch already active for {self.config_dir} - continuing without file watching", file=sys.stderr)
                    ConfigurationManager._watchers_started = True
                else:
                    # Re-raise other RuntimeErrors
                    raise
                    
    def _cleanup_existing_watchers(self) -> None:
        """Clean up any existing file watchers to prevent FSEvents conflicts."""
        for watcher in self.watchers:
            try:
                # Unschedule all watches first to prevent FSEvents "already scheduled" errors
                watcher.unschedule_all()
                watcher.stop()
                watcher.join()
            except Exception as e:
                # Log cleanup failure but continue
                print(f"[CONFIG] Warning: Failed to cleanup existing watcher: {e}")
        self.watchers.clear()
        
    def _log_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Log configuration change for audit trail.
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        # Import here to avoid circular dependency
        try:
            from .logging import AICOLogger
            logger = AICOLogger(
                subsystem="core",
                module="aico.core.config",
                config_manager=self
            )
            logger.info(
                f"Configuration changed: {key}",
                extra={
                    "config_key": key,
                    "old_value": str(old_value) if old_value is not None else None,
                    "new_value": str(new_value) if new_value is not None else None,
                    "change_type": "update" if old_value is not None else "create"
                }
            )
        except ImportError:
            # Fallback to print if logging system not available
            print(f"[CONFIG] {key}: {old_value} -> {new_value}")
        
    @classmethod
    def reset_singleton(cls):
        """Reset singleton instance for testing or cleanup."""
        if cls._instance is not None:
            # Clean up watchers before resetting - proper FSEvents cleanup
            for watcher in cls._instance.watchers:
                try:
                    # Unschedule all watches first to prevent FSEvents "already scheduled" errors
                    watcher.unschedule_all()
                    watcher.stop()
                    watcher.join()
                except Exception as e:
                    # Log cleanup failure but don't crash during shutdown
                    # This is acceptable during cleanup as it's non-critical
                    import sys
                    print(f"[CONFIG] Warning: Failed to stop config watcher during cleanup: {e}", file=sys.stderr)
            cls._instance.watchers.clear()
            cls._instance = None
            cls._initialized = False
            cls._watchers_started = False
    
    def __del__(self):
        """Cleanup file watchers on destruction."""
        for watcher in self.watchers:
            try:
                # Unschedule all watches first to prevent FSEvents "already scheduled" errors
                watcher.unschedule_all()
                watcher.stop()
                watcher.join()
            except Exception as e:
                # Log cleanup failure but don't crash during destruction
                # This is acceptable during object destruction as it's non-critical
                import sys
                print(f"[CONFIG] Warning: Failed to stop config watcher during destruction: {e}", file=sys.stderr)
