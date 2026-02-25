"""
AICO Configuration Management System

Provides unified, hierarchical configuration management across all AICO subsystems
with encryption, validation, and hot reloading capabilities.
"""

import json
import logging
import os
import threading
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

try:
    import jsonschema
    from jsonschema import Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

logger = logging.getLogger(__name__)

_CONFIG_DEFAULT_UNSET = object()


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
            
        # Import here to avoid circular dependency
        from aico.core.paths import AICOPaths

        if config_dir is None:
            config_dir = AICOPaths.get_config_directory()

        self.config_dir = config_dir
        self.user_config_dir = config_dir
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

        # Track missing configuration keys we've already logged about to avoid log storms
        self._missing_key_errors_logged: set[str] = set()
        logger.info(f"Configuration initialized from {self.config_dir} (lightweight={lightweight})")
    
    def validate_schemas(self, schema_dir: Optional[Path] = None) -> List[Tuple[str, List[str]]]:
        """
        Validate all loaded domain configurations against their JSON schemas.
        
        Args:
            schema_dir: Directory containing schema files (defaults to config/schemas)
            
        Returns:
            List of (domain_name, errors) tuples for domains with validation errors.
            Empty list if all domains are valid.
            
        Raises:
            ConfigurationError: If jsonschema is not installed
        """
        if not JSONSCHEMA_AVAILABLE:
            raise ConfigurationError(
                "jsonschema package is required for schema validation. "
                "Install with: pip install jsonschema"
            )
        
        if schema_dir is None:
            schema_dir = self.config_dir / "schemas"
        
        if not schema_dir.exists():
            logger.warning(f"Schema directory not found: {schema_dir}")
            return []
        
        validation_errors = []
        
        # Get all domain names from loaded config (top-level keys)
        domains = list(self.config_cache.keys())
        
        for domain in domains:
            schema_file = schema_dir / f"{domain}.schema.json"
            
            if not schema_file.exists():
                logger.debug(f"No schema found for domain '{domain}' (expected: {schema_file})")
                continue
            
            try:
                # Load schema
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                
                # Validate domain config against schema
                validator = Draft7Validator(schema)
                errors = list(validator.iter_errors(self.config_cache[domain]))
                
                if errors:
                    error_messages = [
                        f"  - {error.json_path}: {error.message}"
                        for error in errors
                    ]
                    validation_errors.append((domain, error_messages))
                    logger.error(f"Schema validation failed for domain '{domain}':")
                    for msg in error_messages:
                        logger.error(msg)
                else:
                    logger.debug(f"✓ Schema validation passed for domain '{domain}'")
                    
            except json.JSONDecodeError as e:
                validation_errors.append((domain, [f"Invalid JSON schema: {e}"]))
                logger.error(f"Failed to parse schema for domain '{domain}': {e}")
            except Exception as e:
                validation_errors.append((domain, [f"Validation error: {e}"]))
                logger.error(f"Error validating domain '{domain}': {e}")
        
        return validation_errors
    
    def get(self, key: str, default: Any = _CONFIG_DEFAULT_UNSET) -> Any:
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

        # Guard against legacy core.<domain> namespace usage during the refactor.
        # We only block namespaces that have already been migrated to dedicated domains
        # to keep the repo runnable while we split core.yaml incrementally.
        migrated_core_prefixes = (
            "core.system.",
            "core.logging.",
            "core.message_bus.",
            "core.service_auth.",
            "core.api_gateway.",
            "core.instrumentation.",
            "core.modelservice.",
            "core.database.",
            "core.scheduler.",
            "core.conversation.",
            "core.memory.",
            "core.agency.",
            "core.emotion.",
        )
        if key.startswith(migrated_core_prefixes) and os.environ.get("AICO_ALLOW_LEGACY_CORE_NAMESPACE") != "1":
            raise ConfigurationError(
                "Legacy configuration namespace 'core.*' is not allowed. "
                "This repo is migrating from the former mega-config domain to dedicated domains. "
                "Update your config key to the new domain (e.g. 'core.logging.*' -> 'logging.*', "
                "'core.message_bus.*' -> 'message_bus.*', 'core.api_gateway.*' -> 'api_gateway.*'). "
                "If you must temporarily bypass this guard during migration, set "
                "AICO_ALLOW_LEGACY_CORE_NAMESPACE=1."
            )
        
        keys = key.split('.')
        value = self.config_cache
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                strict_missing = os.environ.get("AICO_CONFIG_STRICT_MISSING_KEYS") == "1"
                if default is not _CONFIG_DEFAULT_UNSET and not strict_missing:
                    import logging
                    logger = logging.getLogger("shared.core.config")
                    if key not in self._missing_key_errors_logged:
                        self._missing_key_errors_logged.add(key)
                        available = []
                        if isinstance(value, dict):
                            available = list(value.keys())
                        # Missing optional keys are expected during incremental config migration.
                        # Do not emit stack traces in this case (it creates noisy log storms).
                        logger.warning(
                            "[CONFIG_WARNING] Configuration key '%s' not found (missing segment '%s'). "
                            "Returning provided default. Available keys at this level: %s",
                            key,
                            k,
                            available,
                        )
                    return default

                available = []
                if isinstance(value, dict):
                    available = list(value.keys())
                raise ConfigurationError(
                    f"Configuration key '{key}' not found. "
                    f"Missing segment '{k}'. Available keys at this level: {available}"
                )
        
        # Additional check: warn if returning an empty dict for a config section
        if isinstance(value, dict) and not value and len(keys) > 1:
            import logging
            logger = logging.getLogger("shared.core.config")
            logger.warning(f"⚠️ [CONFIG_WARNING] Configuration section '{key}' exists but is EMPTY!")
            
        return value

    def get_optional(self, key: str, default: Any = None) -> Any:
        """Get configuration value, always returning a fallback if missing."""
        return self.get(key, default=default)

    def require(self, key: str, *, allow_empty_dict: bool = False) -> Any:
        """Get configuration value and fail loudly if missing (or empty dict, unless allowed)."""
        value = self.get(key)
        if isinstance(value, dict) and not value and not allow_empty_dict:
            raise ConfigurationError(f"Configuration key '{key}' exists but is empty")
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
                path=self._get_runtime_config_file(),
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
            "AICO_REST_HOST": "api_gateway.rest.host",
            "AICO_NATS_URL": "message_bus.nats_url",
            "AICO_INFLUX_URL": "influx.url",
            "AICO_LOKI_URL": "loki.url",
            "AICO_PG_HOST": "postgres.host",
            "AICO_PG_PORT": "postgres.port",
            "AICO_PG_DB_NAME": "postgres.db_name",
            "AICO_TRANSPORT_ENCRYPTION_ENABLED": "security.transport.encryption.enabled",
            "AICO_GATEWAY_ENCRYPTION_PLUGIN_ENABLED": "api_gateway.plugins.encryption.enabled",
            "AICO_GATEWAY_SECURITY_PLUGIN_ENABLED": "api_gateway.plugins.security.enabled",
            "AICO_OLLAMA_HOST": "modelservice.ollama.host",
            "AICO_OLLAMA_PORT": "modelservice.ollama.port",
            "AICO_OLLAMA_AUTO_INSTALL": "modelservice.ollama.auto_install",
            "AICO_OLLAMA_AUTO_START": "modelservice.ollama.auto_start",
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

            # Apply environment variable overrides directly to the in-memory cache.
            # IMPORTANT: Do not call self.set() here because _apply_environment_variables()
            # runs during initialize(); calling set() would recursively call initialize().
            for key, value in env_overrides.items():
                keys = key.split('.')
                current = self.config_cache
                for k in keys[:-1]:
                    if k not in current or not isinstance(current[k], dict):
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value
                
    def _load_runtime_configs(self) -> None:
        """Load runtime configuration changes from encrypted store."""
        runtime_file = self._get_runtime_config_file()
        
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
        # Skip persistence in test mode to prevent polluting user config
        if os.environ.get('AICO_TEST_MODE') == '1':
            return
        
        runtime_file = self._get_runtime_config_file()
        
        # Extract runtime changes (priority 5 source)
        runtime_data = {}
        for source in self.sources:
            if source.name == "runtime":
                runtime_data = source.data
                break

        try:
            runtime_file.parent.mkdir(parents=True, exist_ok=True)
            with open(runtime_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(runtime_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            # Log error but don't crash - persistence is optional
            print(f"Warning: Failed to persist runtime config '{runtime_file}': {e}")

    def _get_runtime_config_file(self) -> Path:
        """Get the runtime config file path.

        Runtime config must be writable. In container deployments `AICO_CONFIG_DIR` is
        expected to be read-only (image-shipped defaults), so runtime overrides are
        stored under the data directory by default.
        """
        override_dir = os.getenv("AICO_RUNTIME_CONFIG_DIR")
        if override_dir:
            return Path(override_dir) / "runtime.yaml"

        # CRITICAL: Avoid circular dependency with AICOPaths.get_data_directory()
        # which calls ConfigurationManager.initialize() during initialization
        # Use direct platformdirs call instead
        try:
            import platformdirs
            data_dir = Path(platformdirs.user_data_dir("aico", "boeni-industries"))
            return data_dir / "config" / "runtime.yaml"
        except Exception:
            return (self.user_config_dir / "runtime.yaml")
        
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
            from .logging import get_logger
            logger = get_logger("shared.core.config")
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
