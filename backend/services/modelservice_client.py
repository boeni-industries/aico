"""
ZMQ client for backend-modelservice communication.

Uses ZeroMQ message bus with CurveZMQ encryption for secure communication
with the modelservice subsystem.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient


@dataclass
class ModelServiceConfig:
    """Configuration for modelservice client."""
    broker_address: str
    timeout: float
    encryption_enabled: bool = True


class ModelServiceClient:
    """
    ZMQ client for modelservice communication.
    
    Provides secure communication with modelservice via ZeroMQ message bus
    with CurveZMQ encryption.
    """
    
    def __init__(self, config_manager: ConfigurationManager, config: Optional[ModelServiceConfig] = None):
        self.config_manager = config_manager
        
        # Load configuration from AICO config system
        if config is None:
            bus_config = config_manager.get("message_bus", {})
            broker_address = bus_config.get("broker_address", "tcp://localhost:5555")
            timeout = bus_config.get("timeout", 60.0)
            self.config = ModelServiceConfig(broker_address=broker_address, timeout=timeout)
        else:
            self.config = config
            
        self.logger = get_logger("backend", "services.modelservice_client")
        self.bus_client: Optional[MessageBusClient] = None
    
    async def _ensure_connection(self):
        """Ensure ZMQ connection is established."""
        if self.bus_client is None:
            self.bus_client = MessageBusClient(
                client_id="backend_modelservice_client",
                config_manager=self.config_manager
            )
            await self.bus_client.connect()
            self.logger.info(
                "Connected to message bus for modelservice communication",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
    
    async def _send_request(self, request_topic: str, response_topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request via ZMQ and wait for response."""
        await self._ensure_connection()
        
        # Generate correlation ID for request/response matching
        correlation_id = str(uuid.uuid4())
        
        # Create proper protobuf message based on request type
        from aico.proto.aico_modelservice_pb2 import CompletionsRequest, HealthRequest, ModelsRequest, StatusRequest
        
        if "completions" in request_topic:
            # Create CompletionsRequest protobuf
            request_proto = CompletionsRequest()
            request_proto.model = data.get("model", "")
            if "prompt" in data:
                # For simple prompt, convert to messages format
                from aico.proto.aico_modelservice_pb2 import ConversationMessage
                msg = request_proto.messages.add()
                msg.role = "user"
                msg.content = data["prompt"]
            request_proto.stream = data.get("stream", False)
            if "temperature" in data.get("options", {}):
                request_proto.temperature = data["options"]["temperature"]
            if "max_tokens" in data.get("options", {}):
                request_proto.max_tokens = data["options"]["max_tokens"]
        elif "health" in request_topic:
            request_proto = HealthRequest()
        elif "models" in request_topic:
            request_proto = ModelsRequest()
        elif "status" in request_topic:
            request_proto = StatusRequest()
        else:
            # Fallback to HealthRequest for unknown types
            request_proto = HealthRequest()
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_response(message):
            nonlocal response_data
            try:
                # Check correlation ID match
                message_correlation_id = None
                if hasattr(message, 'metadata') and hasattr(message.metadata, 'attributes'):
                    message_correlation_id = message.metadata.attributes.get('correlation_id')
                
                self.logger.debug(f"Received response with correlation_id: {message_correlation_id}, expected: {correlation_id}")
                
                # Only process if correlation IDs match
                if message_correlation_id != correlation_id:
                    self.logger.debug(f"Correlation ID mismatch, ignoring response")
                    return
                
                self.logger.debug(f"Processing response for correlation_id: {correlation_id}")
                
                from aico.proto.aico_modelservice_pb2 import CompletionsResponse
                if hasattr(message, 'any_payload'):
                    # Unpack the Any payload
                    completions_response = CompletionsResponse()
                    if message.any_payload.Unpack(completions_response):
                        self.logger.debug(f"Successfully unpacked CompletionsResponse: success={completions_response.success}")
                        response_data = {
                            'success': completions_response.success,
                            'error': completions_response.error if completions_response.HasField('error') else None
                        }
                        if completions_response.HasField('result'):
                            # Check if result has message field (actual field name from logs)
                            if hasattr(completions_response.result, 'message'):
                                response_data['response'] = completions_response.result.message.content
                                self.logger.debug(f"Extracted message content: {completions_response.result.message.content[:100]}...")
                            elif hasattr(completions_response.result, 'content'):
                                response_data['response'] = completions_response.result.content
                                self.logger.debug(f"Extracted content: {completions_response.result.content[:100]}...")
                            elif hasattr(completions_response.result, 'text'):
                                response_data['response'] = completions_response.result.text
                                self.logger.debug(f"Extracted text: {completions_response.result.text[:100]}...")
                            else:
                                # Log available fields for debugging
                                fields = [field.name for field in completions_response.result.DESCRIPTOR.fields]
                                self.logger.debug(f"Available result fields: {fields}")
                                response_data['response'] = str(completions_response.result)
                        else:
                            self.logger.debug("No result field in response")
                        response_received.set()
                    else:
                        self.logger.error("Failed to unpack CompletionsResponse")
                        response_data = {'success': False, 'error': 'Failed to unpack response'}
                        response_received.set()
                else:
                    # Handle case where message doesn't have any_payload
                    self.logger.debug(f"Message structure: {type(message)}, fields: {dir(message)}")
                    response_data = {'success': False, 'error': 'Invalid message format'}
                    response_received.set()
            except Exception as e:
                self.logger.error(f"Error parsing response: {e}")
                response_data = {'success': False, 'error': str(e)}
                response_received.set()
        
        # Subscribe to response topic
        await self.bus_client.subscribe(response_topic, handle_response)
        
        try:
            # Send request with correlation ID
            await self.bus_client.publish(request_topic, request_proto, correlation_id=correlation_id)
            
            # Wait for response with timeout
            await asyncio.wait_for(response_received.wait(), timeout=self.config.timeout)
            
            return response_data
            
        except asyncio.TimeoutError:
            error_msg = f"Request timed out after {self.config.timeout}s"
            self.logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"ZMQ request failed: {str(e)}"
            self.logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
    
    async def get_health(self) -> Dict[str, Any]:
        """Get modelservice health status."""
        return await self._send_request(
            AICOTopics.MODELSERVICE_HEALTH_REQUEST,
            AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
            {}
        )
    
    async def get_chat_completions(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Get chat completions from modelservice (conversational with message arrays)."""
        request_data = {
            "model": model,
            "messages": messages,
            "stream": kwargs.get("stream", False),
            "options": kwargs.get("options", {})
        }
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_CHAT_REQUEST,
            AICOTopics.MODELSERVICE_CHAT_RESPONSE,
            request_data
        )
    
    async def get_completions(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Get text completions from modelservice (single prompt analysis)."""
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": kwargs.get("stream", False),
            "options": kwargs.get("options", {})
        }
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
            AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
            request_data
        )
    
    async def get_models(self) -> Dict[str, Any]:
        """Get list of available models."""
        return await self._send_request(
            AICOTopics.MODELSERVICE_MODELS_REQUEST,
            AICOTopics.MODELSERVICE_MODELS_RESPONSE,
            {}
        )
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        return await self._send_request(
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST,
            AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE,
            {"model_name": model_name}
        )
    
    async def get_embeddings(self, model: str, prompt: str) -> Dict[str, Any]:
        """Get embeddings from modelservice."""
        request_data = {
            "model": model,
            "prompt": prompt
        }
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
            AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
            request_data
        )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get modelservice status."""
        return await self._send_request(
            AICOTopics.MODELSERVICE_STATUS_REQUEST,
            AICOTopics.MODELSERVICE_STATUS_RESPONSE,
            {}
        )
    
    async def disconnect(self):
        """Disconnect from the message bus."""
        if self.bus_client:
            await self.bus_client.disconnect()
            self.bus_client = None
            self.logger.info(
                "Disconnected from message bus",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )


# Singleton instance for backend use
_modelservice_client: Optional[ModelServiceClient] = None


def get_modelservice_client(config_manager: ConfigurationManager) -> ModelServiceClient:
    """Get singleton modelservice client instance."""
    global _modelservice_client
    
    if _modelservice_client is None:
        _modelservice_client = ModelServiceClient(config_manager)
    
    return _modelservice_client
