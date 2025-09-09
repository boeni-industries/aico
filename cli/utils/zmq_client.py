"""
ZeroMQ client utility for CLI commands.

Provides a simple interface for CLI commands to communicate with services
via ZMQ message bus with CurveZMQ encryption and Protocol Buffers.
"""

import asyncio
import logging
import uuid
import warnings
from typing import Dict, Any

from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from modelservice.core.protobuf_messages import ModelserviceMessageFactory, ModelserviceMessageParser

# Suppress specific async warnings for CLI usage
warnings.filterwarnings("ignore", message="coroutine.*was never awaited", category=RuntimeWarning)

from aico.core.logging import initialize_logging, get_logger


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
            # Initialize message bus client using the same pattern as the working test script
            client = MessageBusClient(
                client_id="cli_client",
                config_manager=self.config_manager
            )
            
            await client.connect()
            
            # Create Protocol Buffer request message
            correlation_id = str(uuid.uuid4())
            request_envelope = self._create_request_envelope(request_topic, data, correlation_id)
            
            # Set up response handler
            response_received = asyncio.Event()
            response_payload = None
            
            async def handle_response(envelope):
                nonlocal response_payload
                # Parse Protocol Buffer response using AicoMessage envelope
                try:
                    if ModelserviceMessageParser.get_correlation_id(envelope) == correlation_id:
                        # Extract response based on topic type
                        if response_topic == AICOTopics.MODELSERVICE_HEALTH_RESPONSE:
                            from aico.proto.aico_modelservice_pb2 import HealthResponse
                            health_response = ModelserviceMessageFactory.extract_payload(envelope, HealthResponse)
                            response_payload = {
                                "success": health_response.success,
                                "data": {
                                    "status": health_response.status,
                                    "version": "0.0.2",  # Default version
                                    "checks": {},  # Will be populated by actual health check
                                    "issues": []
                                }
                            }
                            if not health_response.success and health_response.HasField('error'):
                                response_payload["error"] = health_response.error
                        else:
                            # Generic response handling
                            response_payload = ModelserviceMessageParser.extract_response_payload(envelope, response_topic)
                        response_received.set()
                except Exception as e:
                    self.logger.error(f"Error parsing response: {e}")
                    response_payload = {"success": False, "error": f"Response parsing error: {str(e)}"}
            
            # Subscribe to response topic
            await client.subscribe(response_topic, handle_response)
            
            # Send Protocol Buffer request (pass raw protobuf object, let MessageBusClient wrap it)
            await client.publish(request_topic, request_envelope, correlation_id=correlation_id)
            
            # Wait for response with timeout
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            
            return response_payload
            
        except asyncio.TimeoutError:
            self.logger.error(f"Request timed out after {timeout}s")
            return {"success": False, "error": f"Request timed out after {timeout}s"}
        except Exception as e:
            # Ensure any pending async operations are properly handled
            self.logger.error(f"ZMQ request failed: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass  # Ignore disconnect errors
    
    def send_request_sync(self, request_topic: str, response_topic: str, 
                         data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Synchronous wrapper for send_request."""
        try:
            # Create new event loop for this request to avoid conflicts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.send_request(request_topic, response_topic, data, timeout))
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"Sync ZMQ request failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_request_envelope(self, request_topic: str, data: Dict[str, Any], correlation_id: str):
        """Create Protocol Buffer request object based on topic (not envelope - MessageBusClient handles wrapping)."""
        # Import protobuf messages
        from aico.proto.aico_modelservice_pb2 import (
            HealthRequest, StatusRequest, ModelsRequest, CompletionsRequest, ConversationMessage
        )
        
        # Map request topics to raw protobuf objects (not envelopes)
        if request_topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
            return HealthRequest()
        elif request_topic == AICOTopics.MODELSERVICE_STATUS_REQUEST:
            return StatusRequest()
        elif request_topic == AICOTopics.MODELSERVICE_MODELS_REQUEST:
            return ModelsRequest()
        elif request_topic == AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST:
            request = CompletionsRequest()
            request.model = data.get('model', '')
            for msg_data in data.get('messages', []):
                message = ConversationMessage()
                message.role = msg_data.get('role', 'user')
                message.content = msg_data.get('content', '')
                request.messages.append(message)
            if data.get('stream') is not None:
                request.stream = data.get('stream')
            if data.get('temperature') is not None:
                request.temperature = data.get('temperature')
            if data.get('max_tokens') is not None:
                request.max_tokens = data.get('max_tokens')
            if data.get('top_p') is not None:
                request.top_p = data.get('top_p')
            if data.get('system'):
                request.system = data.get('system')
            return request
        elif request_topic == AICOTopics.OLLAMA_STATUS_REQUEST:
            # Create appropriate Ollama request - using StatusRequest for now
            return StatusRequest()
        elif request_topic == AICOTopics.OLLAMA_MODELS_REQUEST:
            return ModelsRequest()
        else:
            raise ValueError(f"Unsupported request topic: {request_topic}")


def get_modelservice_health() -> Dict[str, Any]:
    """Get Modelservice health via ZMQ."""
    client = CLIZMQClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_HEALTH_REQUEST,
        AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
        {},
        timeout=3.0
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
