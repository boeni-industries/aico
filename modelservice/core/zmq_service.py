"""
ZeroMQ service for modelservice - replaces FastAPI/uvicorn HTTP server.

This module implements the ZMQ message bus client that subscribes to modelservice
topics and routes messages to appropriate handlers. It replaces the HTTP server
with pure ZMQ communication using Protocol Buffers.
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

# Logger will be initialized in class constructor to avoid import-time issues


class ModelserviceZMQService:
    """ZeroMQ service for modelservice message handling."""
    
    def __init__(self, config: ConfigurationManager, ollama_manager=None):
        """Initialize the ZMQ service with configuration and optional Ollama manager."""
        # Initialize logger first
        self.logger = get_logger("modelservice", "zmq_service")
        
        # Configuration is stored under 'core' domain in the config manager
        core_config = config.get("core", {})
        self.config = core_config.get("modelservice", {})
        self.ollama_manager = ollama_manager
        self.running = False
        self.bus_client = None
        self.processed_correlation_ids = set()  # Track processed correlation IDs to prevent duplicates
        
        self.logger.info("About to instantiate ModelserviceZMQHandlers...")
        try:
            self.handlers = ModelserviceZMQHandlers(self.config, ollama_manager)
            self.logger.info("ModelserviceZMQHandlers instantiated successfully")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to instantiate ModelserviceZMQHandlers: {e}")
            import traceback
            self.logger.error(f"Handlers instantiation traceback: {traceback.format_exc()}")
            raise
        
        # Topic to handler mapping
        self.topic_handlers = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: self.handlers.handle_health_request,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: self.handlers.handle_chat_request,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: self.handlers.handle_completions_request,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: self.handlers.handle_models_request,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: self.handlers.handle_model_info_request,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: self.handlers.handle_embeddings_request,
            AICOTopics.MODELSERVICE_NER_REQUEST: self.handlers.handle_ner_request,
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
        self.logger.info("Ollama manager injected into ZMQ service")
    
    async def start_early(self):
        """Start ZMQ service early for log capture, without full initialization."""
        try:
            self.logger.info("Starting modelservice ZMQ service (early mode)...")
            
            # Initialize message bus client following AICO patterns
            self.bus_client = MessageBusClient("message_bus_client_modelservice")
            
            await self.bus_client.connect()
            
            basic_topics = [
                AICOTopics.MODELSERVICE_HEALTH_REQUEST,
                AICOTopics.MODELSERVICE_STATUS_REQUEST,
            ]
            
            self.logger.info(f"Subscribing to basic topics: {basic_topics}")
            for topic in basic_topics:
                self.logger.info(f"About to subscribe to topic: '{topic}' (type: {type(topic)})")
                await self.bus_client.subscribe(topic, self._handle_message)
                self.logger.info(f"Successfully subscribed to topic: '{topic}'")
                
            self.logger.info(f"ZMQ service early start complete, subscribed to {len(basic_topics)} topics")
            self.logger.info(f"Topic handler mapping: {list(self.topic_handlers.keys())}")
            
            self.running = True
            self.logger.info("Modelservice ZMQ service started (early mode)")
            
        except Exception as e:
            self.logger.error(f"Failed to start ZMQ service (early): {str(e)}")
            raise
    
    async def start(self):
        """Complete the ZMQ service initialization and subscribe to remaining topics."""
        try:
            self.logger.info("Completing modelservice ZMQ service initialization...")
            
            # Reuse existing bus_client from start_early() - don't create a new one
            if not self.bus_client:
                self.logger.error("No existing bus client found - start_early() must be called first")
                raise RuntimeError("start_early() must be called before start()")
            
            # Subscribe to remaining topics that require Ollama
            ollama_topics = [
                AICOTopics.MODELSERVICE_CHAT_REQUEST,
                AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
                AICOTopics.MODELSERVICE_MODELS_REQUEST,
                AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST,
                AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
                AICOTopics.MODELSERVICE_NER_REQUEST,
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
                    self.logger.info(f"Subscribed to topic: {topic}")
                else:
                    self.logger.warning(f"No handler found for topic {topic} during subscription")
            
            self.logger.info("Modelservice ZMQ service fully initialized")
            
            # Start message processing loop as background task (non-blocking)
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to start ZMQ service: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the ZMQ service."""
        self.logger.info("Stopping modelservice ZMQ service...")
        self.running = False
        
        if self.bus_client:
            await self.bus_client.disconnect()
        
        self.logger.info("Modelservice ZMQ service stopped")
    
    async def run(self):
        """Continue running the ZMQ service (for services started early)."""
        if not self.running:
            self.logger.error("Cannot run ZMQ service - not started")
            return
            
        self.logger.info("ZMQ service continuing to run...")
        await self._message_loop()
    
    async def _message_loop(self):
        """Main message processing loop - keep service alive while MessageBusClient handles messages."""
        while self.running:
            try:
                # Keep the service alive while MessageBusClient handles message reception
                # The actual message processing is handled by the MessageBusClient's _message_loop
                await asyncio.sleep(1.0)
            except Exception as e:
                self.logger.error(f"Error in message loop: {str(e)}")
                if self.running:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def _handle_message(self, envelope):
        """Handle incoming Protocol Buffer ZMQ messages and route to appropriate handlers."""
        self.logger.info(f"[ZMQ_SERVICE] 📨 Message handler called with envelope: {type(envelope)}")
        try:
            # Extract information from AicoMessage envelope
            self.logger.info(f"[ZMQ_SERVICE] Extracting correlation_id and message_type from envelope...")
            correlation_id = ModelserviceMessageParser.get_correlation_id(envelope)
            message_type = ModelserviceMessageParser.get_message_type(envelope)
            self.logger.info(f"[ZMQ_SERVICE] Extracted - correlation_id: '{correlation_id}', message_type: '{message_type}'")
            
            # Check for duplicate correlation ID to prevent processing the same message multiple times
            if correlation_id in self.processed_correlation_ids:
                self.logger.warning(f"Duplicate correlation ID detected: {correlation_id}, skipping message processing")
                return
            
            # Add correlation ID to processed set
            self.processed_correlation_ids.add(correlation_id)
            
            # Clean up old correlation IDs to prevent memory growth (keep last 1000)
            if len(self.processed_correlation_ids) > 1000:
                # Remove oldest half of the set
                old_ids = list(self.processed_correlation_ids)[:500]
                for old_id in old_ids:
                    self.processed_correlation_ids.discard(old_id)
            
            # Use message type as topic (already includes /v1 suffix)
            topic = message_type
            self.logger.info(f"[ZMQ_SERVICE] Processing message: type={message_type}, topic={topic}, correlation_id={correlation_id}")
            
            self.logger.info(f"[ZMQ_SERVICE] Extracting request payload for topic: {topic}")
            request_payload = ModelserviceMessageParser.extract_request_payload(envelope, topic)
            self.logger.info(f"[ZMQ_SERVICE] Request payload extracted: {type(request_payload)}")
            
            self.logger.debug(f"[ZMQ_SERVICE] Handling Protocol Buffer message on topic {topic} with correlation_id {correlation_id}")
            
            # Route to appropriate handler
            self.logger.info(f"[ZMQ_SERVICE] Looking up handler for topic: {topic}")
            handler = self.topic_handlers.get(topic)
            if not handler:
                self.logger.error(f"[ZMQ_SERVICE] ❌ CRITICAL: No handler found for topic: {topic}")
                self.logger.info(f"[ZMQ_SERVICE] Looking up handler for topic: {topic}")
            
            if topic in self.topic_handlers:
                handler_name = self.topic_handlers[topic].__name__
                self.logger.info(f"[ZMQ_SERVICE] ✅ Handler found: {handler_name}")
                
                
                # Execute handler
                self.logger.info(f"[ZMQ_SERVICE] Executing handler {handler_name} with payload type: {type(request_payload)}")
                response = await self.topic_handlers[topic](request_payload)
            self.logger.info(f"[ZMQ_SERVICE] Handler completed, response type: {type(response)}")
            
            # Send Protocol Buffer response if correlation_id is provided
            if correlation_id and self.bus_client:
                response_topic = self._get_response_topic(topic)
                self.logger.info(f"[ZMQ_SERVICE] Response topic for '{topic}': {response_topic}")
                if response_topic:
                    self.logger.info(f"[ZMQ_SERVICE] Publishing response to topic '{response_topic}' with correlation_id '{correlation_id}'")
                    # Pass raw response_payload to MessageBusClient, let it handle envelope wrapping
                    await self.bus_client.publish(response_topic, response_payload, correlation_id=correlation_id)
                    self.logger.info(f"[ZMQ_SERVICE] ✅ Response published successfully to topic {response_topic}")
                else:
                    self.logger.error(f"[ZMQ_SERVICE] ❌ No response topic found for request topic: {topic}")
            else:
                self.logger.warning(f"[ZMQ_SERVICE] ⚠️ No response sent - correlation_id: {correlation_id}, bus_client: {self.bus_client is not None}")
            
        except Exception as e:
            self.logger.error(f"[ZMQ_SERVICE] ❌ CRITICAL ERROR handling Protocol Buffer message: {str(e)}")
            self.logger.error(f"[ZMQ_SERVICE] Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"[ZMQ_SERVICE] Full traceback: {traceback.format_exc()}")
            
            # Send error response if possible
            correlation_id = None
            try:
                correlation_id = ModelserviceMessageParser.get_correlation_id(envelope)
                self.logger.info(f"[ZMQ_SERVICE] Extracted correlation_id for error response: {correlation_id}")
            except Exception as extract_error:
                self.logger.error(f"[ZMQ_SERVICE] Failed to extract correlation_id for error response: {extract_error}")
                
            if correlation_id and self.bus_client:
                response_topic = self._get_response_topic(topic)
                if response_topic:
                    self.logger.info(f"[ZMQ_SERVICE] Sending error response to topic: {response_topic}")
                    if topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
                        from aico.proto.aico_modelservice_pb2 import HealthResponse
                        error_response = HealthResponse()
                        error_response.success = False
                        error_response.status = "error"
                        error_response.error = f"Handler error: {str(e)}"
                        await self.bus_client.publish(response_topic, error_response, correlation_id=correlation_id)
                        self.logger.info(f"[ZMQ_SERVICE] Error response sent successfully")
                else:
                    self.logger.error(f"[ZMQ_SERVICE] No response topic available for error response")
            else:
                self.logger.error(f"[ZMQ_SERVICE] Cannot send error response - missing correlation_id or bus_client")
    
    def _get_response_topic(self, request_topic: str) -> Optional[str]:
        """Get the response topic for a given request topic."""
        response_mapping = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: AICOTopics.MODELSERVICE_CHAT_RESPONSE,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: AICOTopics.MODELSERVICE_MODELS_RESPONSE,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
            AICOTopics.MODELSERVICE_NER_REQUEST: AICOTopics.MODELSERVICE_NER_RESPONSE,
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
        response_message_type = self._get_response_message_type(request_topic)
        self.logger.debug(f"Creating response envelope: topic={request_topic}, response_type={response_message_type}, payload_type={type(response_payload)}")
        envelope = ModelserviceMessageFactory.create_envelope(
            response_payload, 
            response_message_type, 
            correlation_id
        )
        self.logger.debug(f"Created response envelope with payload type URL: {envelope.any_payload.type_url}")
        return envelope
    
    def _create_error_response_envelope(self, request_topic: str, error_message: str, correlation_id: str):
        """Create Protocol Buffer error response envelope."""
        # Create appropriate error response based on request topic
        if request_topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
            from aico.proto.aico_modelservice_pb2 import HealthResponse
            response = HealthResponse()
            response.success = False
            response.status = "error"
            response.error = error_message
        elif request_topic in [AICOTopics.MODELSERVICE_CHAT_REQUEST, AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST]:
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
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: AICOTopics.MODELSERVICE_CHAT_RESPONSE,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: AICOTopics.MODELSERVICE_MODELS_RESPONSE,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
            AICOTopics.MODELSERVICE_NER_REQUEST: AICOTopics.MODELSERVICE_NER_RESPONSE,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: AICOTopics.MODELSERVICE_STATUS_RESPONSE,
            AICOTopics.OLLAMA_STATUS_REQUEST: AICOTopics.OLLAMA_STATUS_RESPONSE,
            AICOTopics.OLLAMA_MODELS_REQUEST: AICOTopics.OLLAMA_MODELS_RESPONSE,
            AICOTopics.OLLAMA_MODELS_PULL_REQUEST: AICOTopics.OLLAMA_MODELS_PULL_RESPONSE,
            AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST: AICOTopics.OLLAMA_MODELS_REMOVE_RESPONSE,
            AICOTopics.OLLAMA_SERVE_REQUEST: AICOTopics.OLLAMA_SERVE_RESPONSE,
            AICOTopics.OLLAMA_SHUTDOWN_REQUEST: AICOTopics.OLLAMA_SHUTDOWN_RESPONSE,
        }
        return mapping.get(request_topic, "unknown/response/v1")
    
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
