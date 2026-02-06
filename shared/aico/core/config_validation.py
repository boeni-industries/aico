"""
Configuration Validation Module

Provides comprehensive startup validation for all AICO configuration.
This module ensures NO configuration errors are silently ignored.

Usage:
    from aico.core.config_validation import validate_startup_config
    
    config_manager = ConfigurationManager()
    config_manager.initialize()
    validate_startup_config(config_manager)  # Raises on any error
"""

from typing import List, Dict, Any, Tuple
from aico.core.config import ConfigurationManager, ConfigurationError
from aico.core.logging import get_logger

logger = get_logger("shared.core.config_validation")


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


# Critical configuration keys that MUST exist for each service
REQUIRED_CONFIG_KEYS = {
    "backend": [
        "postgres.host",
        "postgres.port",
        "postgres.db_name",
        "api_gateway.rest.host",
        "api_gateway.rest.port",
        "message_bus.broker_address",
        "message_bus.pub_port",
        "message_bus.sub_port",
        "security.transport.message_bus_encryption",
        "conversation.features",
        "emotion.appraisal_sensitivity",
        "agency.arbiter.enabled",
        "agency.planning.enable_llm_refinement",
        "memory.working.ttl_seconds",
        "memory.semantic.enabled",
    ],
    "modelservice": [
        "modelservice.host",
        "modelservice.port",
        "modelservice.ollama.host",
        "modelservice.ollama.port",
        "modelservice.transformers.models",
        "api_gateway.rest.host",
        "api_gateway.rest.port",
    ],
    "cli": [
        "api_gateway.rest.host",
        "api_gateway.rest.port",
        "security.transport.encryption_enabled",
    ],
    "shared": [
        "system.environment",
        "logging.level",
        "security.transport.encryption_enabled",
        "message_bus.broker_address",
    ]
}


def validate_required_keys(
    config: ConfigurationManager,
    service: str = "backend"
) -> List[str]:
    """
    Validate that all required configuration keys exist.
    
    Args:
        config: ConfigurationManager instance
        service: Service name (backend, modelservice, cli, shared)
        
    Returns:
        List of missing keys (empty if all present)
    """
    missing_keys = []
    required_keys = REQUIRED_CONFIG_KEYS.get(service, [])
    
    for key in required_keys:
        try:
            # Try to get the value - if it doesn't exist, it will return None or raise
            value = config.get(key, None)
            if value is None:
                missing_keys.append(key)
        except ConfigurationError:
            missing_keys.append(key)
    
    return missing_keys


def validate_domain_schemas(config: ConfigurationManager) -> List[Tuple[str, List[str]]]:
    """
    Validate all loaded domains against their JSON schemas.
    
    Args:
        config: ConfigurationManager instance
        
    Returns:
        List of (domain, errors) tuples for domains with validation errors
    """
    return config.validate_schemas()


def validate_config_types(config: ConfigurationManager) -> List[str]:
    """
    Validate that critical config values have correct types.
    
    Args:
        config: ConfigurationManager instance
        
    Returns:
        List of type validation errors
    """
    errors = []
    
    # Type checks for critical config values
    type_checks = {
        "postgres.port": int,
        "postgres.pool_size": int,
        "api_gateway.rest.port": int,
        "message_bus.pub_port": int,
        "message_bus.sub_port": int,
        "security.transport.message_bus_encryption": bool,
        "memory.working.ttl_seconds": int,
        "memory.semantic.enabled": bool,
        "agency.arbiter.enabled": bool,
        "agency.arbiter.max_active_intentions": int,
        "emotion.appraisal_sensitivity": (int, float),
    }
    
    for key, expected_type in type_checks.items():
        try:
            value = config.get(key, None)
            if value is not None and not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    expected_type_name = " | ".join(t.__name__ for t in expected_type)
                else:
                    expected_type_name = expected_type.__name__
                errors.append(
                    f"Config key '{key}' has wrong type: "
                    f"expected {expected_type_name}, got {type(value).__name__}"
                )
        except ConfigurationError:
            # Key doesn't exist - will be caught by required_keys check
            pass
    
    return errors


def validate_config_ranges(config: ConfigurationManager) -> List[str]:
    """
    Validate that numeric config values are within acceptable ranges.
    
    Args:
        config: ConfigurationManager instance
        
    Returns:
        List of range validation errors
    """
    errors = []
    
    # Range checks for numeric values
    range_checks = {
        "postgres.port": (1, 65535),
        "postgres.pool_size": (1, 100),
        "api_gateway.rest.port": (1, 65535),
        "message_bus.pub_port": (1, 65535),
        "message_bus.sub_port": (1, 65535),
        "memory.working.ttl_seconds": (60, 2592000),  # 60 seconds to 30 days
        "agency.arbiter.max_active_intentions": (1, 20),
        "emotion.appraisal_sensitivity": (0.0, 1.0),
        "emotion.regulation_strength": (0.0, 1.0),
    }
    
    for key, (min_val, max_val) in range_checks.items():
        try:
            value = config.get(key, None)
            if value is not None:
                if not (min_val <= value <= max_val):
                    errors.append(
                        f"Config key '{key}' out of range: "
                        f"{value} not in [{min_val}, {max_val}]"
                    )
        except ConfigurationError:
            # Key doesn't exist - will be caught by required_keys check
            pass
    
    return errors


def validate_startup_config(
    config: ConfigurationManager,
    service: str = "backend",
    fail_fast: bool = True
) -> None:
    """
    Comprehensive configuration validation for service startup.
    
    This function performs ALL validation checks and either:
    - Raises ConfigValidationError immediately (fail_fast=True)
    - Logs all errors and raises at the end (fail_fast=False)
    
    Args:
        config: ConfigurationManager instance
        service: Service name (backend, modelservice, cli, shared)
        fail_fast: If True, raise on first error. If False, collect all errors.
        
    Raises:
        ConfigValidationError: If any validation fails
    """
    all_errors = []
    
    logger.info(f"🔍 [CONFIG_VALIDATION] Starting configuration validation for service: {service}")
    
    # 1. Check required keys
    logger.debug("[CONFIG_VALIDATION] Checking required configuration keys...")
    missing_keys = validate_required_keys(config, service)
    if missing_keys:
        error_msg = f"Missing required configuration keys: {', '.join(missing_keys)}"
        all_errors.append(error_msg)
        logger.error(f"❌ [CONFIG_VALIDATION] {error_msg}")
        if fail_fast:
            raise ConfigValidationError(error_msg)
    else:
        logger.info(f"✅ [CONFIG_VALIDATION] All required keys present ({len(REQUIRED_CONFIG_KEYS.get(service, []))} checked)")
    
    # 2. Validate domain schemas
    logger.debug("[CONFIG_VALIDATION] Validating domain schemas...")
    schema_errors = validate_domain_schemas(config)
    if schema_errors:
        for domain, errors in schema_errors:
            error_msg = f"Schema validation failed for domain '{domain}': {errors}"
            all_errors.append(error_msg)
            logger.error(f"❌ [CONFIG_VALIDATION] {error_msg}")
            if fail_fast:
                raise ConfigValidationError(error_msg)
    else:
        logger.info(f"✅ [CONFIG_VALIDATION] All domain schemas valid ({len(config.get_domains())} domains)")
    
    # 3. Validate config types
    logger.debug("[CONFIG_VALIDATION] Validating configuration types...")
    type_errors = validate_config_types(config)
    if type_errors:
        for error in type_errors:
            all_errors.append(error)
            logger.error(f"❌ [CONFIG_VALIDATION] {error}")
            if fail_fast:
                raise ConfigValidationError(error)
    else:
        logger.info("✅ [CONFIG_VALIDATION] All configuration types valid")
    
    # 4. Validate config ranges
    logger.debug("[CONFIG_VALIDATION] Validating configuration ranges...")
    range_errors = validate_config_ranges(config)
    if range_errors:
        for error in range_errors:
            all_errors.append(error)
            logger.error(f"❌ [CONFIG_VALIDATION] {error}")
            if fail_fast:
                raise ConfigValidationError(error)
    else:
        logger.info("✅ [CONFIG_VALIDATION] All configuration ranges valid")
    
    # Final check - if we collected errors and didn't fail fast, raise now
    if all_errors and not fail_fast:
        error_summary = "\n".join(f"  - {err}" for err in all_errors)
        raise ConfigValidationError(
            f"Configuration validation failed with {len(all_errors)} error(s):\n{error_summary}"
        )
    
    logger.info(f"✅ [CONFIG_VALIDATION] Configuration validation PASSED for service: {service}")


def print_config_summary(config: ConfigurationManager) -> None:
    """
    Print a summary of loaded configuration for debugging.
    
    Args:
        config: ConfigurationManager instance
    """
    logger.info("📋 [CONFIG_VALIDATION] Configuration Summary:")
    logger.info(f"  Environment: {config.get('system.environment', 'unknown')}")
    logger.info(f"  Loaded domains: {', '.join(config.get_domains())}")
    logger.info(f"  Config sources: {len(config.sources)}")
    
    for source in config.sources:
        logger.info(f"    - {source.name} (priority: {source.priority})")
