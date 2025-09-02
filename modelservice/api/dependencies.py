"""
Dependencies for modelservice API endpoints.
"""

from typing import Dict, Any
from fastapi import Depends

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager
from aico.security.service_auth import ServiceAuthManager


def get_modelservice_config() -> Dict[str, Any]:
    """Get modelservice configuration."""
    config_manager = ConfigurationManager()
    config_manager.initialize()
    return config_manager.get("modelservice", {})


def get_identity_manager() -> TransportIdentityManager:
    """Get transport identity manager instance."""
    config_manager = ConfigurationManager()
    config_manager.initialize()
    key_manager = AICOKeyManager(config_manager)
    return TransportIdentityManager(key_manager)


def get_service_auth_manager() -> ServiceAuthManager:
    """Get service authentication manager"""
    config_manager = ConfigurationManager()
    config_manager.initialize()
    key_manager = AICOKeyManager(config_manager)
    identity_manager = TransportIdentityManager(key_manager)
    return ServiceAuthManager(key_manager, identity_manager)