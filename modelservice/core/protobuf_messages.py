"""
Protocol Buffer message utilities for modelservice.

This module provides clean utilities for creating and parsing Protocol Buffer
messages using the existing AicoMessage envelope system.
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from google.protobuf.any_pb2 import Any as ProtoAny

from aico.proto.aico_core_envelope_pb2 import AicoMessage, MessageMetadata
from aico.proto.aico_modelservice_pb2 import (
    # Request messages
    HealthRequest, CompletionsRequest, ModelsRequest, ModelInfoRequest,
    EmbeddingsRequest, StatusRequest, OllamaStatusRequest, OllamaModelsRequest,
    OllamaPullRequest, OllamaRemoveRequest, OllamaServeRequest, OllamaShutdownRequest,
    # Response messages
    HealthResponse, CompletionsResponse, ModelsResponse, ModelInfoResponse,
    EmbeddingsResponse, StatusResponse, OllamaStatusResponse, OllamaModelsResponse,
    OllamaPullResponse, OllamaRemoveResponse, OllamaServeResponse, OllamaShutdownResponse,
    # Data structures
    ChatMessage
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
        
        payload = expected_type()
        if not envelope.any_payload.Unpack(payload):
            raise ValueError(f"Failed to unpack payload as {expected_type.__name__}")
        
        return payload
    
    # Request message factories
    @staticmethod
    def create_health_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a health check request."""
        request = HealthRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "modelservice/health/request", correlation_id
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
        """Create a chat completions request."""
        request = CompletionsRequest()
        request.model = model
        request.stream = stream
        
        # Convert messages to ChatMessage protos
        for msg in messages:
            chat_msg = ChatMessage()
            chat_msg.role = msg.get('role', 'user')
            chat_msg.content = msg.get('content', '')
            request.messages.append(chat_msg)
        
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
            request, "modelservice/completions/request", correlation_id
        )
    
    @staticmethod
    def create_models_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a models list request."""
        request = ModelsRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "modelservice/models/request", correlation_id
        )
    
    @staticmethod
    def create_model_info_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a model info request."""
        request = ModelInfoRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, "modelservice/model_info/request", correlation_id
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
            request, "modelservice/embeddings/request", correlation_id
        )
    
    @staticmethod
    def create_status_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create a status request."""
        request = StatusRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "modelservice/status/request", correlation_id
        )
    
    # Ollama management request factories
    @staticmethod
    def create_ollama_status_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama status request."""
        request = OllamaStatusRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/status/request", correlation_id
        )
    
    @staticmethod
    def create_ollama_models_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama models request."""
        request = OllamaModelsRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/models/request", correlation_id
        )
    
    @staticmethod
    def create_ollama_pull_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama pull request."""
        request = OllamaPullRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/models/pull/request", correlation_id
        )
    
    @staticmethod
    def create_ollama_remove_request(model: str, correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama remove request."""
        request = OllamaRemoveRequest()
        request.model = model
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/models/remove/request", correlation_id
        )
    
    @staticmethod
    def create_ollama_serve_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama serve request."""
        request = OllamaServeRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/serve/request", correlation_id
        )
    
    @staticmethod
    def create_ollama_shutdown_request(correlation_id: Optional[str] = None) -> AicoMessage:
        """Create an Ollama shutdown request."""
        request = OllamaShutdownRequest()
        return ModelserviceMessageFactory.create_envelope(
            request, "ollama/shutdown/request", correlation_id
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
        """Extract correlation ID from envelope metadata."""
        return envelope.metadata.message_id
    
    @staticmethod
    def get_message_type(envelope: AicoMessage) -> str:
        """Extract message type from envelope metadata."""
        return envelope.metadata.message_type
    
    @staticmethod
    def extract_request_payload(envelope: AicoMessage, topic: str):
        """Extract request payload from envelope based on topic."""
        message_type = envelope.metadata.message_type
        
        # Map message types to their corresponding protobuf classes
        request_types = {
            "modelservice/health/request": HealthRequest,
            "modelservice/completions/request": CompletionsRequest,
            "modelservice/models/request": ModelsRequest,
            "modelservice/model_info/request": ModelInfoRequest,
            "modelservice/embeddings/request": EmbeddingsRequest,
            "modelservice/status/request": StatusRequest,
            "ollama/status/request": OllamaStatusRequest,
            "ollama/models/request": OllamaModelsRequest,
            "ollama/models/pull/request": OllamaPullRequest,
            "ollama/models/remove/request": OllamaRemoveRequest,
            "ollama/serve/request": OllamaServeRequest,
            "ollama/shutdown/request": OllamaShutdownRequest,
        }
        
        request_class = request_types.get(message_type)
        if not request_class:
            raise ValueError(f"Unknown request type: {message_type}")
        
        return ModelserviceMessageFactory.extract_payload(envelope, request_class)
    
    @staticmethod
    def extract_response_payload(envelope: AicoMessage, topic: str):
        """Extract response payload from envelope based on topic."""
        message_type = envelope.metadata.message_type
        
        # Map message types to their corresponding protobuf classes
        response_types = {
            "modelservice/health/response": HealthResponse,
            "modelservice/completions/response": CompletionsResponse,
            "modelservice/models/response": ModelsResponse,
            "modelservice/model_info/response": ModelInfoResponse,
            "modelservice/embeddings/response": EmbeddingsResponse,
            "modelservice/status/response": StatusResponse,
            "ollama/status/response": OllamaStatusResponse,
            "ollama/models/response": OllamaModelsResponse,
            "ollama/models/pull/response": OllamaPullResponse,
            "ollama/models/remove/response": OllamaRemoveResponse,
            "ollama/serve/response": OllamaServeResponse,
            "ollama/shutdown/response": OllamaShutdownResponse,
        }
        
        response_class = response_types.get(message_type)
        if not response_class:
            raise ValueError(f"Unknown response type: {message_type}")
        
        return ModelserviceMessageFactory.extract_payload(envelope, response_class)
