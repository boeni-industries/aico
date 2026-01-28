"""
Unit tests for strict configuration access methods.

Tests the require() and get_optional() methods to ensure proper fail-loud
behavior on missing required keys and explicit optional key handling.
"""

import pytest
import os
from aico.core.config import ConfigurationManager, ConfigurationError


class TestStrictConfigAccess:
    """Tests for strict configuration access patterns."""
    
    def setup_method(self):
        """Reset singleton state before each test."""
        ConfigurationManager._instance = None
        ConfigurationManager._initialized = False
        
    def test_require_existing_key(self):
        """Test require() returns value for existing key."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # Test with known existing key
        value = config.require("system.environment")
        assert value == "development"
    
    def test_require_missing_key_fails_loud(self):
        """Test require() raises ConfigurationError for missing key."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.require("nonexistent.key.path")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_get_optional_existing_key(self):
        """Test get_optional() returns value for existing key."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        value = config.get_optional("system.environment")
        assert value == "development"
    
    def test_get_optional_missing_key_returns_none(self):
        """Test get_optional() returns None for missing key without error."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        value = config.get_optional("nonexistent.key.path")
        assert value is None
    
    def test_get_optional_with_default(self):
        """Test get_optional() returns default for missing key."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        value = config.get_optional("nonexistent.key", default="custom_default")
        assert value == "custom_default"
    
    def test_legacy_get_with_default_still_works(self):
        """Test legacy get() with default still works for backward compatibility."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        value = config.get("nonexistent.key", "fallback")
        assert value == "fallback"
    
    def test_strict_missing_keys_env_var(self):
        """Test AICO_CONFIG_STRICT_MISSING_KEYS environment variable."""
        os.environ["AICO_CONFIG_STRICT_MISSING_KEYS"] = "1"
        
        try:
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            
            # Even get() with default should fail in strict mode
            with pytest.raises(ConfigurationError):
                config.get("nonexistent.key", "default")
        finally:
            del os.environ["AICO_CONFIG_STRICT_MISSING_KEYS"]


class TestLegacyNamespaceGuard:
    """Tests for legacy core.* namespace blocking."""
    
    def setup_method(self):
        """Reset singleton state before each test."""
        ConfigurationManager._instance = None
        ConfigurationManager._initialized = False
    
    def test_legacy_core_system_blocked(self):
        """Test core.system.* keys are blocked."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.get("core.system.environment")
        
        assert "legacy" in str(exc_info.value).lower()
        assert "core.*" in str(exc_info.value)
    
    def test_legacy_core_database_blocked(self):
        """Test core.database.* keys are blocked."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.get("core.database.postgres.host")
        
        assert "legacy" in str(exc_info.value).lower()
    
    def test_legacy_core_memory_blocked(self):
        """Test core.memory.* keys are blocked."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.get("core.memory.working.ttl_seconds")
        
        assert "legacy" in str(exc_info.value).lower()
    
    def test_new_domain_keys_work(self):
        """Test new domain keys work without core prefix."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # These should all work
        assert config.get("system.environment") is not None
        assert config.get("postgres.host") is not None
        assert config.get("memory.working.ttl_seconds") is not None
    
    def test_legacy_bypass_env_var(self):
        """Test AICO_ALLOW_LEGACY_CORE_NAMESPACE bypass."""
        os.environ["AICO_ALLOW_LEGACY_CORE_NAMESPACE"] = "1"
        
        try:
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            
            # Should not raise error with bypass enabled
            # (will return None since key doesn't exist, but won't block)
            value = config.get("core.system.environment", "default")
            assert value == "default"
        finally:
            del os.environ["AICO_ALLOW_LEGACY_CORE_NAMESPACE"]
