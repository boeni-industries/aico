"""
Configuration Test Fixtures

Provides test configuration instances.
"""

import pytest
from pathlib import Path


@pytest.fixture
def test_config():
    """Provide a test configuration manager.
    
    Uses default configuration from config/defaults/core.yaml
    """
    from aico.core.config import ConfigurationManager
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    config_path = project_root / "config" / "defaults" / "core.yaml"
    
    # Create config manager
    config = ConfigurationManager()
    
    # Override any test-specific settings here if needed
    # config.set("test.mode", True)
    
    return config
