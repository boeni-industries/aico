"""
Integration tests for configuration schema validation.

Tests the schema validation system to ensure all domains validate correctly
and that validation errors are properly detected and reported.
"""

import pytest
import json
from pathlib import Path
from aico.core.config import ConfigurationManager, ConfigurationError


class TestSchemaValidation:
    """Tests for schema validation functionality."""
    
    def setup_method(self):
        """Reset singleton state before each test."""
        ConfigurationManager._instance = None
        ConfigurationManager._initialized = False
    
    def test_validate_schemas_all_pass(self):
        """Test that all default domain configurations pass validation."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        errors = config.validate_schemas()
        
        # Should have no validation errors
        assert len(errors) == 0, f"Found validation errors: {errors}"
    
    def test_validate_schemas_returns_list(self):
        """Test validate_schemas returns list of tuples."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        errors = config.validate_schemas()
        
        assert isinstance(errors, list)
        # Each error should be (domain_name, error_messages) tuple
        for error in errors:
            assert isinstance(error, tuple)
            assert len(error) == 2
            assert isinstance(error[0], str)  # domain name
            assert isinstance(error[1], list)  # error messages
    
    def test_schema_files_exist_for_all_domains(self):
        """Test that schema files exist for all domain config files."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        config_dir = config.config_dir / "defaults"
        schema_dir = config.config_dir / "schemas"
        
        # Get all YAML config files
        config_files = list(config_dir.glob("*.yaml"))
        
        for config_file in config_files:
            domain = config_file.stem
            schema_file = schema_dir / f"{domain}.schema.json"
            
            # Core domains should have schemas
            if domain in ["system", "logging", "postgres", "modelservice", 
                         "scheduler", "conversation", "memory", "agency"]:
                assert schema_file.exists(), f"Missing schema for {domain}"
    
    def test_schema_files_are_valid_json(self):
        """Test that all schema files are valid JSON."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        schema_dir = config.config_dir / "schemas"
        schema_files = list(schema_dir.glob("*.schema.json"))
        
        assert len(schema_files) > 0, "No schema files found"
        
        for schema_file in schema_files:
            with open(schema_file, 'r') as f:
                try:
                    schema = json.load(f)
                    assert isinstance(schema, dict)
                    assert "$schema" in schema
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {schema_file}: {e}")
    
    def test_required_properties_enforced(self):
        """Test that required properties in schemas are enforced."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # Temporarily modify a domain to remove a required property
        original_value = config.config_cache.get("system", {}).get("environment")
        
        try:
            # Remove required property
            if "system" in config.config_cache:
                config.config_cache["system"].pop("environment", None)
            
            errors = config.validate_schemas()
            
            # Should have validation error for system domain
            system_errors = [e for e in errors if e[0] == "system"]
            assert len(system_errors) > 0, "Should detect missing required property"
            
        finally:
            # Restore original value
            if "system" in config.config_cache and original_value is not None:
                config.config_cache["system"]["environment"] = original_value
    
    def test_enum_validation_enforced(self):
        """Test that enum constraints in schemas are enforced."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # Temporarily set invalid enum value
        original_value = config.config_cache.get("system", {}).get("environment")
        
        try:
            # Set invalid enum value
            if "system" in config.config_cache:
                config.config_cache["system"]["environment"] = "invalid_env"
            
            errors = config.validate_schemas()
            
            # Should have validation error for system domain
            system_errors = [e for e in errors if e[0] == "system"]
            assert len(system_errors) > 0, "Should detect invalid enum value"
            
        finally:
            # Restore original value
            if "system" in config.config_cache and original_value is not None:
                config.config_cache["system"]["environment"] = original_value
    
    def test_type_validation_enforced(self):
        """Test that type constraints in schemas are enforced."""
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # Temporarily set wrong type
        original_value = config.config_cache.get("scheduler", {}).get("enabled")
        
        try:
            # Set wrong type (string instead of boolean)
            if "scheduler" in config.config_cache:
                config.config_cache["scheduler"]["enabled"] = "true"
            
            errors = config.validate_schemas()
            
            # Should have validation error for scheduler domain
            scheduler_errors = [e for e in errors if e[0] == "scheduler"]
            assert len(scheduler_errors) > 0, "Should detect wrong type"
            
        finally:
            # Restore original value
            if "scheduler" in config.config_cache and original_value is not None:
                config.config_cache["scheduler"]["enabled"] = original_value


class TestSchemaValidationCLI:
    """Tests for CLI schema validation command."""
    
    def test_validation_command_exists(self):
        """Test that aico config validate command exists."""
        # This would be tested via subprocess in actual integration test
        # For now, just verify the method exists
        config = ConfigurationManager()
        assert hasattr(config, "validate_schemas")
