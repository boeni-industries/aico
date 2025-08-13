# AICO Core Module
"""
AICO Core Module

Provides core functionality for the AICO system including configuration management,
logging, path resolution, and message bus communication.
"""

from .config import ConfigurationManager
from .logging import get_logger, AICOLogger
from .paths import AICOPaths
from .bus import (
    MessageBusClient, 
    MessageBusBroker, 
    create_client,
    create_broker
)

# Import protobuf message types
from ..proto.core import AicoMessage, MessageMetadata

__all__ = ['ConfigurationManager', 'get_logger', 'AICOLogger', 'AICOPaths', 'MessageBusClient', 'MessageBusBroker', 'AicoMessage', 'MessageMetadata', 'create_client', 'create_broker']
