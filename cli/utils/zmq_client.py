"""
ZeroMQ client utility for CLI commands.

Provides a simple interface for CLI commands to communicate with services
via ZMQ message bus with CurveZMQ encryption and Protocol Buffers.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import sys

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger
from aico.core.topics import AICOTopics
from aico.core.bus import MessageBusClient

# Import Protocol Buffer utilities
modelservice_path = Path(__file__).parent.parent.parent / "modelservice"
sys.path.insert(0, str(modelservice_path))
from core.protobuf_messages import ModelserviceMessageFactory, ModelserviceMessageParser


class CLIZMQClient:
    """ZeroMQ client for CLI commands."""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize(lightweight=True)
        initialize_logging(self.config_manager)
        self.logger = get_logger("cli", "zmq_client")
        
    async def send_request(self, request_topic: str, response_topic: str, 
                          data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Send a Protocol Buffer request via ZMQ and wait for response."""
        client = None
        try:
            # Initialize message bus client
            bus_config = self.config_manager.get('message_bus', {})
            client = MessageBusClient(
                broker_address=bus_config.get('broker_address', 'tcp://localhost:5555'),
                identity="cli_client",
                enable_curve=True
            )
            
            await client.connect()
            
            # Create Protocol Buffer request message
            correlation_id = str(uuid.uuid4())
            request_envelope = self._create_request_envelope(request_topic, data, correlation_id)
            
            # Set up response handler
            response_received = asyncio.Event()
            response_payload = None
            
            async def handle_response(topic: str, message: bytes):
                nonlocal response_payload
                # Parse Protocol Buffer response
                envelope = ModelserviceMessageParser.parse_envelope(message)
                if ModelserviceMessageParser.get_correlation_id(envelope) == correlation_id:
                    response_payload = ModelserviceMessageParser.extract_response_payload(envelope, topic)
                    response_received.set()
            
            # Subscribe to response topic
            await client.subscribe(response_topic, handle_response)
            
            # Send Protocol Buffer request
            await client.publish(request_topic, request_envelope.SerializeToString())
            
            # Wait for response with timeout
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            
            return response_payload
            
        except asyncio.TimeoutError:
            self.logger.error(f"Request timed out after {timeout}s")
            return {"success": False, "error": f"Request timed out after {timeout}s"}
        except Exception as e:
            self.logger.error(f"ZMQ request failed: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if client:
                await client.disconnect()
    
    def send_request_sync(self, request_topic: str, response_topic: str, 
                         data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Synchronous wrapper for send_request."""
        try:
            return asyncio.run(self.send_request(request_topic, response_topic, data, timeout))
        except Exception as e:
            self.logger.error(f"Sync ZMQ request failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_request_envelope(self, request_topic: str, data: Dict[str, Any], correlation_id: str):
        """Create Protocol Buffer request envelope based on topic."""
        # Map request topics to factory methods
        if request_topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
            return ModelserviceMessageFactory.create_health_request(correlation_id)
        elif request_topic == AICOTopics.MODELSERVICE_STATUS_REQUEST:
            return ModelserviceMessageFactory.create_status_request(correlation_id)
        elif request_topic == AICOTopics.MODELSERVICE_MODELS_REQUEST:
            return ModelserviceMessageFactory.create_models_request(correlation_id)
        elif request_topic == AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST:
            return ModelserviceMessageFactory.create_completions_request(
                model=data.get('model', ''),
                messages=data.get('messages', []),
                stream=data.get('stream', False),
                temperature=data.get('temperature'),
                max_tokens=data.get('max_tokens'),
                top_p=data.get('top_p'),
                system=data.get('system'),
                correlation_id=correlation_id
            )
        elif request_topic == AICOTopics.OLLAMA_STATUS_REQUEST:
            return ModelserviceMessageFactory.create_ollama_status_request(correlation_id)
        elif request_topic == AICOTopics.OLLAMA_MODELS_REQUEST:
            return ModelserviceMessageFactory.create_ollama_models_request(correlation_id)
        elif request_topic == AICOTopics.OLLAMA_MODELS_PULL_REQUEST:
            return ModelserviceMessageFactory.create_ollama_pull_request(
                model=data.get('model', ''), correlation_id=correlation_id
            )
        elif request_topic == AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST:
            return ModelserviceMessageFactory.create_ollama_remove_request(
                model=data.get('model', ''), correlation_id=correlation_id
            )
        else:
            raise ValueError(f"Unsupported request topic: {request_topic}")


def get_modelservice_health() -> Dict[str, Any]:
    """Get modelservice health status via ZMQ."""
    client = CLIZMQClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_HEALTH_REQUEST,
        AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
        {},
        timeout=5.0
    )


def get_modelservice_status() -> Dict[str, Any]:
    """Get modelservice status via ZMQ."""
    client = CLIZMQClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_STATUS_REQUEST,
        AICOTopics.MODELSERVICE_STATUS_RESPONSE,
        {},
        timeout=5.0
    )


def get_ollama_status() -> Dict[str, Any]:
    """Get Ollama status via ZMQ."""
    client = CLIZMQClient()
    return client.send_request_sync(
        AICOTopics.OLLAMA_STATUS_REQUEST,
        AICOTopics.OLLAMA_STATUS_RESPONSE,
        {},
        timeout=5.0
    )


def get_ollama_models() -> Dict[str, Any]:
    """Get Ollama models list via ZMQ."""
    client = CLIZMQClient()
    return client.send_request_sync(
        AICOTopics.OLLAMA_MODELS_REQUEST,
        AICOTopics.OLLAMA_MODELS_RESPONSE,
        {},
        timeout=10.0
    )


def is_modelservice_running_zmq() -> bool:
    """Check if modelservice is running via ZMQ health check."""
    try:
        health_response = get_modelservice_health()
        return health_response.get("success", False)
    except Exception:
        return False
