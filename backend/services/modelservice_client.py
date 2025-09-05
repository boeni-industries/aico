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
            timeout = bus_config.get("timeout", 30.0)
            self.config = ModelServiceConfig(broker_address=broker_address, timeout=timeout)
        else:
            self.config = config
            
        self.logger = get_logger("backend", "modelservice_client")
        self.bus_client: Optional[MessageBusClient] = None
    
    async def _ensure_connection(self):
        """Ensure ZMQ connection is established."""
        if self.bus_client is None:
            self.bus_client = MessageBusClient(
                broker_address=self.config.broker_address,
                identity="backend_modelservice_client",
                enable_curve=True
            )
            await self.bus_client.connect()
            self.logger.info(
                "Connected to message bus for modelservice communication",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
    
    async def _send_request(self, request_topic: str, response_topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request via ZMQ and wait for response."""
        await self._ensure_connection()
        
        # Generate correlation ID for request/response pattern
        correlation_id = str(uuid.uuid4())
        request_message = {
            'correlation_id': correlation_id,
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_response(topic: str, message: dict):
            nonlocal response_data
            if message.get('correlation_id') == correlation_id:
                response_data = message
                response_received.set()
        
        # Subscribe to response topic
        await self.bus_client.subscribe(response_topic, handle_response)
        
        try:
            # Send request
            await self.bus_client.publish(request_topic, request_message)
            
            # Wait for response with timeout
            await asyncio.wait_for(response_received.wait(), timeout=self.config.timeout)
            
            return response_data.get('data', {})
            
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
    
    async def get_completions(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Get text completions from modelservice."""
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
