"""
ZeroMQ service for modelservice - replaces FastAPI/uvicorn HTTP server.

This module implements the ZMQ message bus client that subscribes to modelservice
topics and routes messages to appropriate handlers. It replaces the HTTP server
with pure ZMQ communication using CurveZMQ encryption and Protocol Buffers.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.core.bus import MessageBusClient
from aico.core.config import ConfigurationManager
from .zmq_handlers import ModelserviceZMQHandlers
from .protobuf_messages import ModelserviceMessageFactory, ModelserviceMessageParser

logger = get_logger("modelservice", "zmq_service")


class ModelserviceZMQService:
    """ZeroMQ service for modelservice message handling."""
    
    def __init__(self, config: ConfigurationManager, ollama_manager=None):
        """Initialize the ZMQ service with configuration and optional Ollama manager."""
        self.config = config.get("modelservice", {})
        self.ollama_manager = ollama_manager
        self.bus_client = None
        self.running = False
        
        # Initialize handlers with dependencies (ollama_manager can be None initially)
        self.handlers = ModelserviceZMQHandlers(self.config, ollama_manager)
        
        # Topic to handler mapping
        self.topic_handlers = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: self.handlers.handle_health_request,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: self.handlers.handle_completions_request,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: self.handlers.handle_models_request,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: self.handlers.handle_model_info_request,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: self.handlers.handle_embeddings_request,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: self.handlers.handle_status_request,
            # Ollama management topics
            AICOTopics.OLLAMA_STATUS_REQUEST: self._handle_ollama_status,
            AICOTopics.OLLAMA_MODELS_REQUEST: self._handle_ollama_models,
            AICOTopics.OLLAMA_MODELS_PULL_REQUEST: self._handle_ollama_pull,
            AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST: self._handle_ollama_remove,
            AICOTopics.OLLAMA_SERVE_REQUEST: self._handle_ollama_serve,
            AICOTopics.OLLAMA_SHUTDOWN_REQUEST: self._handle_ollama_shutdown,
        }
    
    def set_ollama_manager(self, ollama_manager):
        """Set the Ollama manager after early initialization."""
        self.ollama_manager = ollama_manager
        self.handlers.ollama_manager = ollama_manager
        logger.info("Ollama manager injected into ZMQ service")
    
    async def start_early(self):
        """Start ZMQ service early for log capture, without full initialization."""
        try:
            logger.info("Starting modelservice ZMQ service (early mode)...")
            
            # Initialize message bus client with correct constructor
            from aico.core.config import ConfigurationManager
            config_manager = ConfigurationManager()
            self.bus_client = MessageBusClient(
                client_id="modelservice",
                config_manager=config_manager
            )
            
            await self.bus_client.connect()
            
            # Subscribe to topics that don't require Ollama
            basic_topics = [
                AICOTopics.MODELSERVICE_HEALTH_REQUEST,
                AICOTopics.MODELSERVICE_STATUS_REQUEST,
            ]
            
            for topic in basic_topics:
                if topic in self.topic_handlers:
                    await self.bus_client.subscribe(topic, self._handle_message)
                    logger.info(f"Subscribed to topic (early): {topic}")
            
            self.running = True
            logger.info("Modelservice ZMQ service started (early mode)")
            
        except Exception as e:
            logger.error(f"Failed to start ZMQ service (early): {str(e)}")
            raise
    
    async def start(self):
        """Start the ZMQ service and subscribe to topics."""
        try:
            logger.info("Starting modelservice ZMQ service...")
            
            # Initialize message bus client with CurveZMQ encryption
            from aico.core.config import ConfigurationManager
            config_manager = ConfigurationManager()
            self.bus_client = MessageBusClient(
                client_id="modelservice",
                config_manager=config_manager
            )
            
            await self.bus_client.connect()
            
            # Subscribe to remaining topics that require Ollama
            ollama_topics = [
                AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
                AICOTopics.MODELSERVICE_MODELS_REQUEST,
                AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST,
                AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
                AICOTopics.OLLAMA_STATUS_REQUEST,
                AICOTopics.OLLAMA_MODELS_REQUEST,
                AICOTopics.OLLAMA_MODELS_PULL_REQUEST,
                AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST,
                AICOTopics.OLLAMA_SERVE_REQUEST,
                AICOTopics.OLLAMA_SHUTDOWN_REQUEST,
            ]
            
            for topic in ollama_topics:
                if topic in self.topic_handlers:
                    await self.bus_client.subscribe(topic, self._handle_message)
                    logger.info(f"Subscribed to topic: {topic}")
            
            logger.info("Modelservice ZMQ service fully initialized")
            
            # Start message processing loop
            await self._message_loop()
            
        except Exception as e:
            logger.error(f"Failed to start ZMQ service: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the ZMQ service."""
        logger.info("Stopping modelservice ZMQ service...")
        self.running = False
        
        if self.bus_client:
            await self.bus_client.disconnect()
        
        logger.info("Modelservice ZMQ service stopped")
    
    async def run(self):
        """Continue running the ZMQ service (for services started early)."""
        if not self.running:
            logger.error("Cannot run ZMQ service - not started")
            return
            
        logger.info("ZMQ service continuing to run...")
        await self._message_loop()
    
    async def _message_loop(self):
        """Main message processing loop - keep service alive while MessageBusClient handles messages."""
        while self.running:
            try:
                # Keep the service alive while MessageBusClient handles message reception
                # The actual message processing is handled by the MessageBusClient's _message_loop
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                if self.running:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def _handle_message(self, topic: str, message: bytes):
        """Handle incoming Protocol Buffer ZMQ messages and route to appropriate handlers."""
        try:
            # Parse Protocol Buffer message
            envelope = ModelserviceMessageParser.parse_envelope(message)
            correlation_id = ModelserviceMessageParser.get_correlation_id(envelope)
            request_payload = ModelserviceMessageParser.extract_request_payload(envelope, topic)
            
            logger.debug(f"Handling Protocol Buffer message on topic {topic} with correlation_id {correlation_id}")
            
            # Route to appropriate handler
            handler = self.topic_handlers.get(topic)
            if not handler:
                logger.warning(f"No handler found for topic: {topic}")
                return
            
            # Execute handler with Protocol Buffer payload
            response_payload = await handler(request_payload)
            
            # Send Protocol Buffer response if correlation_id is provided
            if correlation_id and self.bus_client:
                response_topic = self._get_response_topic(topic)
                if response_topic:
                    response_envelope = self._create_response_envelope(
                        topic, response_payload, correlation_id
                    )
                    
                    await self.bus_client.publish(response_topic, response_envelope.SerializeToString())
                    logger.debug(f"Sent Protocol Buffer response on topic {response_topic}")
            
        except Exception as e:
            logger.error(f"Error handling Protocol Buffer message on topic {topic}: {str(e)}")
            
            # Send error response if possible
            correlation_id = None
            try:
                envelope = ModelserviceMessageParser.parse_envelope(message)
                correlation_id = ModelserviceMessageParser.get_correlation_id(envelope)
            except:
                pass
                
            if correlation_id and self.bus_client:
                response_topic = self._get_response_topic(topic)
                if response_topic:
                    error_envelope = self._create_error_response_envelope(
                        topic, str(e), correlation_id
                    )
                    await self.bus_client.publish(response_topic, error_envelope.SerializeToString())
    
    def _get_response_topic(self, request_topic: str) -> Optional[str]:
        """Get the response topic for a given request topic."""
        response_mapping = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: AICOTopics.MODELSERVICE_MODELS_RESPONSE,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: AICOTopics.MODELSERVICE_STATUS_RESPONSE,
            AICOTopics.OLLAMA_STATUS_REQUEST: AICOTopics.OLLAMA_STATUS_RESPONSE,
            AICOTopics.OLLAMA_MODELS_REQUEST: AICOTopics.OLLAMA_MODELS_RESPONSE,
            AICOTopics.OLLAMA_MODELS_PULL_REQUEST: AICOTopics.OLLAMA_MODELS_PULL_RESPONSE,
            AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST: AICOTopics.OLLAMA_MODELS_REMOVE_RESPONSE,
            AICOTopics.OLLAMA_SERVE_REQUEST: AICOTopics.OLLAMA_SERVE_RESPONSE,
            AICOTopics.OLLAMA_SHUTDOWN_REQUEST: AICOTopics.OLLAMA_SHUTDOWN_RESPONSE,
        }
        return response_mapping.get(request_topic)
    
    def _create_response_envelope(self, request_topic: str, response_payload, correlation_id: str):
        """Create Protocol Buffer response envelope based on request topic."""
        return ModelserviceMessageFactory.create_envelope(
            response_payload, 
            self._get_response_message_type(request_topic), 
            correlation_id
        )
    
    def _create_error_response_envelope(self, request_topic: str, error_message: str, correlation_id: str):
        """Create Protocol Buffer error response envelope."""
        # Create appropriate error response based on request topic
        if request_topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
            from aico.proto.aico_modelservice_pb2 import HealthResponse
            response = HealthResponse()
            response.success = False
            response.status = "error"
            response.error = error_message
        elif request_topic == AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST:
            from aico.proto.aico_modelservice_pb2 import CompletionsResponse
            response = CompletionsResponse()
            response.success = False
            response.error = error_message
        elif request_topic == AICOTopics.MODELSERVICE_MODELS_REQUEST:
            from aico.proto.aico_modelservice_pb2 import ModelsResponse
            response = ModelsResponse()
            response.success = False
            response.error = error_message
        else:
            # Generic error response
            from aico.proto.aico_modelservice_pb2 import HealthResponse
            response = HealthResponse()
            response.success = False
            response.status = "error"
            response.error = error_message
        
        return ModelserviceMessageFactory.create_envelope(
            response,
            self._get_response_message_type(request_topic),
            correlation_id
        )
    
    def _get_response_message_type(self, request_topic: str) -> str:
        """Get response message type for request topic."""
        mapping = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: "modelservice/health/response",
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: "modelservice/completions/response",
            AICOTopics.MODELSERVICE_MODELS_REQUEST: "modelservice/models/response",
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: "modelservice/model_info/response",
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: "modelservice/embeddings/response",
            AICOTopics.MODELSERVICE_STATUS_REQUEST: "modelservice/status/response",
            AICOTopics.OLLAMA_STATUS_REQUEST: "ollama/status/response",
            AICOTopics.OLLAMA_MODELS_REQUEST: "ollama/models/response",
            AICOTopics.OLLAMA_MODELS_PULL_REQUEST: "ollama/models/pull/response",
            AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST: "ollama/models/remove/response",
            AICOTopics.OLLAMA_SERVE_REQUEST: "ollama/serve/response",
            AICOTopics.OLLAMA_SHUTDOWN_REQUEST: "ollama/shutdown/response",
        }
        return mapping.get(request_topic, "unknown/response")
    
    # Ollama management handlers (delegate to ollama_manager)
    async def _handle_ollama_status(self, request_data: dict) -> dict:
        """Handle Ollama status requests."""
        try:
            if hasattr(self.ollama_manager, 'get_status'):
                status = await self.ollama_manager.get_status()
                return {"success": True, "data": status}
            else:
                # Fallback to basic status check
                status = await self.handlers._check_ollama_status()
                return {"success": True, "data": status}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_ollama_models(self, request_data: dict) -> dict:
        """Handle Ollama models list requests."""
        try:
            # Delegate to models handler
            return await self.handlers.handle_models_request(request_data)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_ollama_pull(self, request_data: dict) -> dict:
        """Handle Ollama model pull requests."""
        try:
            model_name = request_data.get('model')
            if not model_name:
                return {"success": False, "error": "model name is required"}
            
            if hasattr(self.ollama_manager, 'pull_model'):
                result = await self.ollama_manager.pull_model(model_name)
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "pull_model not implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_ollama_remove(self, request_data: dict) -> dict:
        """Handle Ollama model remove requests."""
        try:
            model_name = request_data.get('model')
            if not model_name:
                return {"success": False, "error": "model name is required"}
            
            if hasattr(self.ollama_manager, 'remove_model'):
                result = await self.ollama_manager.remove_model(model_name)
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "remove_model not implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_ollama_serve(self, request_data: dict) -> dict:
        """Handle Ollama serve requests."""
        try:
            if hasattr(self.ollama_manager, 'start_server'):
                result = await self.ollama_manager.start_server()
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "start_server not implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_ollama_shutdown(self, request_data: dict) -> dict:
        """Handle Ollama shutdown requests."""
        try:
            if hasattr(self.ollama_manager, 'stop_server'):
                result = await self.ollama_manager.stop_server()
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "stop_server not implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}
