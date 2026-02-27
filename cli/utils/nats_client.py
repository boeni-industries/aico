"""NATS client utility for CLI commands.

Provides a simple interface for CLI commands to communicate with services
via NATS message bus with Protocol Buffers.
"""

import asyncio
import uuid
import warnings
from typing import Dict, Any

from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_core_envelope_pb2 import AicoMessage

# Suppress specific async warnings for CLI usage
warnings.filterwarnings("ignore", message="coroutine.*was never awaited", category=RuntimeWarning)

from aico.core.logging import initialize_logging, get_logger


def _get_correlation_id(envelope: AicoMessage) -> str:
    if "correlation_id" in envelope.metadata.attributes:
        return envelope.metadata.attributes["correlation_id"]
    return envelope.metadata.message_id


def _extract_payload(envelope: AicoMessage, expected_type: type):
    if not envelope.HasField("any_payload"):
        raise ValueError("Envelope has no payload")
    payload = expected_type()
    if not envelope.any_payload.Unpack(payload):
        raise ValueError(f"Failed to unpack payload as {expected_type.__name__}")
    return payload


def _extract_response_payload(envelope: AicoMessage, topic: str):
    from aico.proto import aico_modelservice_pb2

    response_types = {
        AICOTopics.MODELSERVICE_HEALTH_RESPONSE: aico_modelservice_pb2.HealthResponse,
        AICOTopics.MODELSERVICE_STATUS_RESPONSE: aico_modelservice_pb2.StatusResponse,
        AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE: aico_modelservice_pb2.EmbeddingsResponse,
        AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE: aico_modelservice_pb2.CompletionsResponse,
        AICOTopics.MODELSERVICE_MODELS_RESPONSE: aico_modelservice_pb2.ModelsResponse,
        AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE: aico_modelservice_pb2.ModelInfoResponse,
        AICOTopics.MODELSERVICE_NER_RESPONSE: aico_modelservice_pb2.NerResponse,
        AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE: aico_modelservice_pb2.SentimentResponse,
        AICOTopics.MODELSERVICE_INTENT_CLASSIFICATION_RESPONSE: aico_modelservice_pb2.IntentClassificationResponse,
        AICOTopics.OLLAMA_STATUS_RESPONSE: aico_modelservice_pb2.OllamaStatusResponse,
        AICOTopics.OLLAMA_MODELS_RESPONSE: aico_modelservice_pb2.OllamaModelsResponse,
        AICOTopics.OLLAMA_MODELS_PULL_RESPONSE: aico_modelservice_pb2.OllamaPullResponse,
        AICOTopics.OLLAMA_MODELS_REMOVE_RESPONSE: aico_modelservice_pb2.OllamaRemoveResponse,
        AICOTopics.OLLAMA_SERVE_RESPONSE: aico_modelservice_pb2.OllamaServeResponse,
        AICOTopics.OLLAMA_SHUTDOWN_RESPONSE: aico_modelservice_pb2.OllamaShutdownResponse,
    }

    response_type = response_types.get(topic)
    if response_type is None:
        raise ValueError(f"Unsupported response topic: {topic}")
    return _extract_payload(envelope, response_type)


class CLINATSClient:
    """NATS client for CLI commands."""

    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.config_manager.initialize(lightweight=True)
        initialize_logging(service_name="cli", enable_loki=True, enable_console=True)
        self.logger = get_logger("cli.nats_client")

    async def send_request(
        self,
        request_topic: str,
        response_topic: str,
        data: Dict[str, Any],
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Send a Protocol Buffer request via the message bus and wait for response."""

        client = None
        try:
            client = MessageBusClient(
                client_id="cli_client",
                config_manager=self.config_manager,
            )

            await client.connect()

            correlation_id = str(uuid.uuid4())
            request_proto = self._create_request_proto(request_topic, data)

            response_received = asyncio.Event()
            response_payload: Dict[str, Any] | None = None

            async def handle_response(envelope):
                nonlocal response_payload
                try:
                    if _get_correlation_id(envelope) != correlation_id:
                        return

                    if response_topic == AICOTopics.MODELSERVICE_HEALTH_RESPONSE:
                        from aico.proto.aico_modelservice_pb2 import HealthResponse

                        health_response = _extract_payload(envelope, HealthResponse)
                        response_payload = {
                            "success": health_response.success,
                            "data": {
                                "status": health_response.status,
                                "version": "0.0.2",
                                "checks": {},
                                "issues": [],
                            },
                        }
                        if (not health_response.success) and health_response.HasField("error"):
                            response_payload["error"] = health_response.error

                    elif response_topic == AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE:
                        from aico.proto.aico_modelservice_pb2 import EmbeddingsResponse

                        embeddings_response = _extract_payload(envelope, EmbeddingsResponse)
                        response_payload = {
                            "success": embeddings_response.success,
                            "data": {"embedding": list(embeddings_response.embedding)},
                        }
                        if (not embeddings_response.success) and embeddings_response.HasField("error"):
                            response_payload["error"] = embeddings_response.error

                    elif response_topic == AICOTopics.OLLAMA_MODELS_RESPONSE:
                        from aico.proto.aico_modelservice_pb2 import ModelsResponse

                        models_response = _extract_payload(envelope, ModelsResponse)
                        response_payload = {"success": models_response.success, "data": {"models": []}}
                        for model in models_response.models:
                            model_dict = {
                                "name": model.name,
                                "size": model.size,
                                "digest": model.digest,
                            }
                            if model.HasField("modified_at"):
                                model_dict["modified_at"] = model.modified_at.ToDatetime().isoformat()
                            response_payload["data"]["models"].append(model_dict)

                        if (not models_response.success) and models_response.HasField("error"):
                            response_payload["error"] = models_response.error

                    else:
                        protobuf_response = _extract_response_payload(envelope, response_topic)
                        response_payload = {"success": getattr(protobuf_response, "success", False), "data": {}}
                        if hasattr(protobuf_response, "error") and protobuf_response.HasField("error"):
                            response_payload["error"] = protobuf_response.error

                    response_received.set()

                except Exception as e:
                    self.logger.error(f"Error parsing response: {e}")
                    response_payload = {"success": False, "error": f"Response parsing error: {str(e)}"}
                    response_received.set()

            await client.subscribe(response_topic, handle_response)

            await client.publish(
                request_topic,
                request_proto,
                correlation_id=correlation_id,
                reply_to=response_topic,
            )

            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            return response_payload or {"success": False, "error": "empty response"}

        except asyncio.TimeoutError:
            self.logger.error(f"Request timed out after {timeout}s")
            return {"success": False, "error": f"Request timed out after {timeout}s"}
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    def send_request_sync(
        self,
        request_topic: str,
        response_topic: str,
        data: Dict[str, Any],
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for send_request."""

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.send_request(request_topic, response_topic, data, timeout))
        finally:
            loop.close()

    def _create_request_proto(self, request_topic: str, data: Dict[str, Any]):
        """Create request protobuf object based on topic."""

        from aico.proto.aico_modelservice_pb2 import (
            HealthRequest,
            StatusRequest,
            ModelsRequest,
            CompletionsRequest,
            ConversationMessage,
            EmbeddingsRequest,
            OllamaModelsRequest,
            OllamaPullRequest,
        )

        if request_topic == AICOTopics.MODELSERVICE_HEALTH_REQUEST:
            return HealthRequest()
        if request_topic == AICOTopics.MODELSERVICE_STATUS_REQUEST:
            return StatusRequest()
        if request_topic == AICOTopics.MODELSERVICE_MODELS_REQUEST:
            return ModelsRequest()
        if request_topic == AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST:
            request = CompletionsRequest()
            request.model = data.get("model", "")
            for msg_data in data.get("messages", []):
                message = ConversationMessage()
                message.role = msg_data.get("role", "user")
                message.content = msg_data.get("content", "")
                request.messages.append(message)
            if data.get("stream") is not None:
                request.stream = data.get("stream")
            if data.get("temperature") is not None:
                request.temperature = data.get("temperature")
            if data.get("max_tokens") is not None:
                request.max_tokens = data.get("max_tokens")
            if data.get("top_p") is not None:
                request.top_p = data.get("top_p")
            if data.get("system"):
                request.system = data.get("system")
            return request
        if request_topic == AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST:
            request = EmbeddingsRequest()
            request.model = data.get("model", "")
            request.prompt = data.get("prompt", "")
            return request
        if request_topic == AICOTopics.OLLAMA_STATUS_REQUEST:
            return StatusRequest()
        if request_topic == AICOTopics.OLLAMA_MODELS_REQUEST:
            return OllamaModelsRequest()
        if request_topic == AICOTopics.OLLAMA_MODELS_PULL_REQUEST:
            request = OllamaPullRequest()
            request.model = data.get("model", "")
            return request

        raise ValueError(f"Unsupported request topic: {request_topic}")


def get_modelservice_health() -> Dict[str, Any]:
    """Get modelservice health."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_HEALTH_REQUEST,
        AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
        {},
        timeout=3.0,
    )


def get_modelservice_status() -> Dict[str, Any]:
    """Get modelservice status."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_STATUS_REQUEST,
        AICOTopics.MODELSERVICE_STATUS_RESPONSE,
        {},
        timeout=5.0,
    )


def get_ollama_status() -> Dict[str, Any]:
    """Get Ollama status."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.OLLAMA_STATUS_REQUEST,
        AICOTopics.OLLAMA_STATUS_RESPONSE,
        {},
        timeout=5.0,
    )


def get_ollama_models() -> Dict[str, Any]:
    """Get Ollama models list."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.OLLAMA_MODELS_REQUEST,
        AICOTopics.OLLAMA_MODELS_RESPONSE,
        {},
        timeout=10.0,
    )


def pull_ollama_model(model_name: str) -> Dict[str, Any]:
    """Pull/download a model via Ollama."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.OLLAMA_MODELS_PULL_REQUEST,
        AICOTopics.OLLAMA_MODELS_PULL_RESPONSE,
        {"model": model_name},
        timeout=60.0,
    )


def get_embeddings(model: str, text: str) -> Dict[str, Any]:
    """Generate embeddings via modelservice."""

    client = CLINATSClient()
    return client.send_request_sync(
        AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
        AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
        {"model": model, "prompt": text},
        timeout=30.0,
    )
