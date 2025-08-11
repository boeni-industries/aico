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
    AICOMessage, 
    MessageMetadata, 
    MessagePriority,
    create_client,
    create_broker
)

__all__ = ['ConfigurationManager', 'get_logger', 'AICOLogger', 'AICOPaths', 'MessageBusClient', 'MessageBusBroker', 'AICOMessage', 'MessageMetadata', 'MessagePriority', 'create_client', 'create_broker']
