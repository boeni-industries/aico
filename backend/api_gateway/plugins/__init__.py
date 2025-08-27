"""
Plugin package for AICO API Gateway

Provides built-in plugins for the modular API Gateway architecture.
"""

from .encryption_plugin import EncryptionPlugin
from .log_consumer_plugin import LogConsumerPlugin
from .message_bus_plugin import MessageBusPlugin
from .security_plugin import SecurityPlugin
from .rate_limiting_plugin import RateLimitingPlugin
from .validation_plugin import ValidationPlugin
from .routing_plugin import RoutingPlugin

__all__ = [
    'EncryptionPlugin',
    'LogConsumerPlugin',
    'MessageBusPlugin',
    'SecurityPlugin',
    'RateLimitingPlugin', 
    'ValidationPlugin',
    'RoutingPlugin'
]
