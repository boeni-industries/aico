"""
Dependencies for modelservice API endpoints.
"""

from typing import Generator
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager


def get_config_manager() -> ConfigurationManager:
    """Get configuration manager instance."""
    config_manager = ConfigurationManager()
    config_manager.initialize()
    return config_manager


def get_modelservice_config() -> dict:
    """Get modelservice configuration."""
    config_manager = get_config_manager()
    return config_manager.get("modelservice", {})


# TODO: Add additional dependencies as needed