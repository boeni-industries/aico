"""
Protocol Buffer message utilities for modelservice.

This module provides clean utilities for creating and parsing Protocol Buffer
messages using the existing AicoMessage envelope system.
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from google.protobuf.any_pb2 import Any as ProtoAny

from aico.core.topics import AICOTopics
from aico.proto.aico_core_envelope_pb2 import AicoMessage, MessageMetadata
from aico.proto.aico_modelservice_pb2 import (
    # Request messages
    HealthRequest, CompletionsRequest, ModelsRequest, ModelInfoRequest,
    EmbeddingsRequest, NerRequest, StatusRequest, OllamaStatusRequest, OllamaModelsRequest,
    OllamaPullRequest, OllamaRemoveRequest, OllamaServeRequest, OllamaShutdownRequest,
    # Response messages
    HealthResponse, CompletionsResponse, ModelsResponse, ModelInfoResponse,
    EmbeddingsResponse, NerResponse, StatusResponse, OllamaStatusResponse, OllamaModelsResponse,
    OllamaPullResponse, OllamaRemoveResponse, OllamaServeResponse, OllamaShutdownResponse,
    # Data structures
    ConversationMessage
)


class ModelserviceMessageFactory:
    """Factory for creating modelservice Protocol Buffer messages."""
    
    @staticmethod
    def create_envelope(payload: Any, message_type: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an AicoMessage envelope with the given payload."""
        # Create metadata
        metadata = MessageMetadata()
        metadata.message_id = correlation_id or str(uuid.uuid4())
        metadata.timestamp.GetCurrentTime()
        metadata.source = "modelservice"
        metadata.message_type = message_type
        metadata.version = "1.0"
        
        # Create envelope
        envelope = AicoMessage()
        envelope.metadata.CopyFrom(metadata)
        
        # Pack payload into Any
        any_payload = ProtoAny()
        any_payload.Pack(payload)
        envelope.any_payload.CopyFrom(any_payload)
        
        return envelope
    
    @staticmethod
    def extract_payload(envelope: AicoMessage, expected_type: type) -> Any:
        """Extract and unpack payload from AicoMessage envelope."""
        if not envelope.HasField('any_payload'):
            raise ValueError("Envelope has no payload")
        
        # Debug logging for payload unpacking
        from aico.core.logging import get_logger
        logger = get_logger("modelservice", "protobuf_debug")
        
        logger.info(f"[DEBUG] Attempting to unpack payload as {expected_type.__name__}")
        logger.info(f"[DEBUG] Payload type URL: {envelope.any_payload.type_url}")
        logger.info(f"[DEBUG] Payload value length: {len(envelope.any_payload.value)} bytes")
        
        payload = expected_type()
        if not envelope.any_payload.Unpack(payload):
            logger.error(f"[DEBUG] FAILED to unpack payload as {expected_type.__name__}")
            logger.error(f"[DEBUG] Expected type URL should contain: {expected_type.DESCRIPTOR.full_name}")
            raise ValueError(f"Failed to unpack payload as {expected_type.__name__}")
        
        logger.info(f"[DEBUG] Successfully unpacked payload as {expected_type.__name__}")
        return payload
    
    # Request message factories
    @staticmethod
    def create_health_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a health check request."""
        request = HealthRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_HEALTH_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_completions_request(
        model: str,
        messages: list,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        system: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AicoMessage:
        """Create a conversation completions request."""
        request = CompletionsRequest()
        request.model = model
        request.stream = stream
        
        # Convert messages to ConversationMessage protos
        for msg in messages:
            conv_msg = ConversationMessage()
            conv_msg.role = msg.get('role', 'user')
            conv_msg.content = msg.get('content', '')
            request.messages.append(conv_msg)
        
        # Optional parameters
        if temperature is not None:
            request.temperature = temperature
        if max_tokens is not None:
            request.max_tokens = max_tokens
        if top_p is not None:
            request.top_p = top_p
        if system is not None:
            request.system = system
        
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_models_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a models list request."""
        request = ModelsRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_MODELS_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_model_info_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a model info request."""
        request = ModelInfoRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_embeddings_request(
        model: str, 
        prompt: str, 
        correlation_id: Optional[str] = None
    ) -> AicoMessage:
        """Create an embeddings request."""
        request = EmbeddingsRequest()
        request.model = model
        request.prompt = prompt
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_status_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a status request."""
        request = StatusRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.MODELSERVICE_STATUS_REQUEST, correlation_id
        )
    
    # Ollama management request factories
    @staticmethod
    def create_ollama_status_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama status request."""
        request = OllamaStatusRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_STATUS_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_ollama_models_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama models request."""
        request = OllamaModelsRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_MODELS_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_ollama_pull_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama pull request."""
        request = OllamaPullRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_MODELS_PULL_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_ollama_remove_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama remove request."""
        request = OllamaRemoveRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_ollama_serve_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama serve request."""
        request = OllamaServeRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_SERVE_REQUEST, correlation_id
        )
    
    @staticmethod
    def create_ollama_shutdown_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama shutdown request."""
        request = OllamaShutdownRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, AICOTopics.OLLAMA_SHUTDOWN_REQUEST, correlation_id
        )
    


class ModelserviceMessageParser:
    """Parser for extracting data from modelservice Protocol Buffer messages."""
    
    @staticmethod
    def parse_envelope(data: bytes) -> AicoMessage:
        """Parse binary data into AicoMessage envelope."""
        envelope = AicoMessage()
        envelope.ParseFromString(data)
        return envelope
    
    @staticmethod
    def get_correlation_id(envelope: AicoMessage) -> str:
        """Extract correlation ID from envelope metadata attributes."""
        # Check if correlation_id is in attributes first
        if "correlation_id" in envelope.metadata.attributes:
            return envelope.metadata.attributes["correlation_id"]
        # Fall back to message_id if no correlation_id attribute
        return envelope.metadata.message_id
    
    @staticmethod
    def get_message_type(envelope: AicoMessage) -> str:
        """Extract message type from envelope metadata."""
        return envelope.metadata.message_type
    
    @staticmethod
    def extract_request_payload(envelope: AicoMessage, topic: str):
        """Extract request payload from envelope based on topic."""
        from aico.core.logging import get_logger
        logger = get_logger("modelservice", "protobuf_debug")
        
        message_type = envelope.metadata.message_type
        logger.info(f"[DEBUG] extract_request_payload called with message_type: {message_type}")
        
        # Map message types to their corresponding protobuf classes
        request_types = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: HealthRequest,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: CompletionsRequest,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: CompletionsRequest,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: ModelsRequest,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: ModelInfoRequest,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: EmbeddingsRequest,
            AICOTopics.MODELSERVICE_NER_REQUEST: NerRequest,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: StatusRequest,
            AICOTopics.OLLAMA_STATUS_REQUEST: OllamaStatusRequest,
            AICOTopics.OLLAMA_MODELS_REQUEST: OllamaModelsRequest,
            AICOTopics.OLLAMA_MODELS_PULL_REQUEST: OllamaPullRequest,
            AICOTopics.OLLAMA_MODELS_REMOVE_REQUEST: OllamaRemoveRequest,
            AICOTopics.OLLAMA_SERVE_REQUEST: OllamaServeRequest,
            AICOTopics.OLLAMA_SHUTDOWN_REQUEST: OllamaShutdownRequest,
        }
        
        request_class = request_types.get(message_type)
        if not request_class:
            logger.error(f"[DEBUG] Unknown request type: {message_type}")
            raise ValueError(f"Unknown request type: {message_type}")
        
        logger.info(f"[DEBUG] Found request class: {request_class.__name__} for message_type: {message_type}")
        return ModelserviceMessageFactory.extract_payload(envelope, request_class)
    
    @staticmethod
    def extract_response_payload(envelope: AicoMessage, topic: str):
        """Extract response payload from envelope based on topic."""
        message_type = envelope.metadata.message_type
        
        # Map message types to their corresponding protobuf classes
        response_types = {
            AICOTopics.MODELSERVICE_HEALTH_RESPONSE: HealthResponse,
            AICOTopics.MODELSERVICE_CHAT_RESPONSE: CompletionsResponse,
            AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE: CompletionsResponse,
            AICOTopics.MODELSERVICE_MODELS_RESPONSE: ModelsResponse,
            AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE: ModelInfoResponse,
            AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE: EmbeddingsResponse,
            AICOTopics.MODELSERVICE_NER_RESPONSE: NerResponse,
            AICOTopics.MODELSERVICE_STATUS_RESPONSE: StatusResponse,
            AICOTopics.OLLAMA_STATUS_RESPONSE: OllamaStatusResponse,
            AICOTopics.OLLAMA_MODELS_RESPONSE: OllamaModelsResponse,
            AICOTopics.OLLAMA_MODELS_PULL_RESPONSE: OllamaPullResponse,
            AICOTopics.OLLAMA_MODELS_REMOVE_RESPONSE: OllamaRemoveResponse,
            AICOTopics.OLLAMA_SERVE_RESPONSE: OllamaServeResponse,
            AICOTopics.OLLAMA_SHUTDOWN_RESPONSE: OllamaShutdownResponse,
        }
        
        response_class = response_types.get(message_type)
        if not response_class:
            raise ValueError(f"Unknown response type: {message_type}")
        
        return ModelserviceMessageFactory.extract_payload(envelope, response_class)
