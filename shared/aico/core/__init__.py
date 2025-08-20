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

# Optional protobuf imports to avoid chicken/egg problem with CLI
try:
    from ..proto.aico_core_envelope_pb2 import AicoMessage, MessageMetadata
except ImportError:
    # Protobuf files not generated yet - use fallbacks
    AicoMessage = None
    MessageMetadata = None

__all__ = ['ConfigurationManager', 'get_logger', 'AICOLogger', 'AICOPaths', 'MessageBusClient', 'MessageBusBroker', 'AicoMessage', 'MessageMetadata', 'create_client', 'create_broker']
