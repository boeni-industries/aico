"""
API client utilities for CLI commands.

Provides consistent HTTP client configuration and error handling for AICO CLI commands.
"""

import httpx
from contextlib import contextmanager
from typing import Generator

from aico.core.config import ConfigurationManager


@contextmanager
def get_modelservice_client() -> Generator[httpx.Client, None, None]:
    """Get configured HTTP client for modelservice API."""
    # Load configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Get modelservice configuration
    modelservice_config = config_manager.get("modelservice", {})
    rest_config = modelservice_config.get("rest", {})
    host = rest_config.get("host", "127.0.0.1")
    port = rest_config.get("port", 8773)
    
    base_url = f"http://{host}:{port}"
    
    # Create client with reasonable timeouts
    with httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "AICO-CLI/1.0"}
    ) as client:
        yield client


@contextmanager  
def get_gateway_client() -> Generator[httpx.Client, None, None]:
    """Get configured HTTP client for API Gateway."""
    # Load configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Get gateway configuration
    gateway_config = config_manager.get("api_gateway", {})
    rest_config = gateway_config.get("rest", {})
    host = rest_config.get("host", "127.0.0.1")
    port = rest_config.get("port", 8771)
    
    base_url = f"http://{host}:{port}"
    
    # Create client with reasonable timeouts
    with httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "AICO-CLI/1.0"}
    ) as client:
        yield client
