"""
NATS service for modelservice.

This module implements the message bus client that subscribes to modelservice
request topics and routes messages to appropriate handlers.

All communication is via NATS with Protocol Buffers (AicoMessage envelope).
"""

import asyncio
from typing import Dict, Any, Optional

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.core.bus import MessageBusClient
from aico.core.config import ConfigurationManager

from .protobuf_messages import ModelserviceMessageParser
from .handlers import ModelserviceHandlers


class ModelserviceNATSService:
    """NATS service for modelservice message handling."""

    def __init__(self, config: ConfigurationManager, ollama_manager=None):
        self.logger = get_logger("modelservice.nats_service")

        self.config_manager = config
        self.config = config.get("modelservice", {})
        self.ollama_manager = ollama_manager
        self.running = False
        self.bus_client: Optional[MessageBusClient] = None
        self.processed_correlation_ids = set()

        self.handlers = ModelserviceHandlers(
            self.config,
            ollama_manager,
            None,
            config_manager=self.config_manager,
        )

        self.topic_handlers = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: self.handlers.handle_health_request,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: self.handlers.handle_chat_request,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: self.handlers.handle_completions_request,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: self.handlers.handle_models_request,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: self.handlers.handle_model_info_request,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: self.handlers.handle_embeddings_request,
            AICOTopics.MODELSERVICE_NER_REQUEST: self.handlers.handle_ner_request,
            AICOTopics.MODELSERVICE_INTENT_REQUEST: self.handlers.handle_intent_request,
            AICOTopics.MODELSERVICE_SENTIMENT_REQUEST: self.handlers.handle_sentiment_request,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: self.handlers.handle_status_request,
            AICOTopics.MODELSERVICE_TTS_REQUEST: self.handlers.handle_tts_request,
        }

    def set_ollama_manager(self, ollama_manager):
        self.ollama_manager = ollama_manager
        self.handlers.ollama_manager = ollama_manager
        self.logger.info("Ollama manager injected into NATS service")

    def set_transformers_manager(self, transformers_manager):
        self.handlers.transformers_manager = transformers_manager
        self.handlers.transformers_initialized = True
        self.logger.info("✅ TransformersManager injected into NATS service with preloaded models")

    async def start_early(self):
        try:
            self.logger.info("Starting modelservice NATS service (early mode)...")

            self.bus_client = MessageBusClient("message_bus_client_modelservice")
            await self.bus_client.connect()

            self.handlers.message_bus_client = self.bus_client

            basic_topics = [
                AICOTopics.MODELSERVICE_HEALTH_REQUEST,
                AICOTopics.MODELSERVICE_STATUS_REQUEST,
            ]

            for topic in basic_topics:
                await self.bus_client.subscribe(topic, self._handle_message)

            self.running = True
            self.logger.info("Modelservice NATS service started (early mode)")

        except Exception as e:
            self.logger.error(f"Failed to start NATS service (early): {str(e)}")
            raise

    async def start(self):
        try:
            self.logger.info("Completing modelservice NATS service initialization...")

            if not self.bus_client:
                raise RuntimeError("start_early() must be called before start()")

            modelservice_topics = [
                AICOTopics.MODELSERVICE_CHAT_REQUEST,
                AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
                AICOTopics.MODELSERVICE_MODELS_REQUEST,
                AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST,
                AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
                AICOTopics.MODELSERVICE_NER_REQUEST,
                AICOTopics.MODELSERVICE_INTENT_REQUEST,
                AICOTopics.MODELSERVICE_SENTIMENT_REQUEST,
                AICOTopics.MODELSERVICE_TTS_REQUEST,
            ]

            for topic in modelservice_topics:
                if topic in self.topic_handlers:
                    await self.bus_client.subscribe(topic, self._handle_message)

            await self.handlers.initialize_ner_system()
            await self.handlers.initialize_transformers_system()

            asyncio.create_task(self._message_loop())
            self.logger.info("Modelservice NATS service fully initialized")

        except Exception as e:
            self.logger.error(f"Failed to start NATS service: {str(e)}")
            raise

    async def stop(self):
        self.logger.info("Stopping modelservice NATS service...")
        self.running = False
        if self.bus_client:
            await self.bus_client.disconnect()
        self.logger.info("Modelservice NATS service stopped")

    async def run(self):
        if not self.running:
            self.logger.error("Cannot run NATS service - not started")
            return
        await self._message_loop()

    async def _message_loop(self):
        while self.running:
            await asyncio.sleep(1.0)

    async def _handle_message(self, envelope):
        try:
            correlation_id = ModelserviceMessageParser.get_correlation_id(envelope)
            message_type = ModelserviceMessageParser.get_message_type(envelope)

            if correlation_id in self.processed_correlation_ids:
                return
            self.processed_correlation_ids.add(correlation_id)
            if len(self.processed_correlation_ids) > 1000:
                old_ids = list(self.processed_correlation_ids)[:500]
                for old_id in old_ids:
                    self.processed_correlation_ids.discard(old_id)

            topic = message_type
            request_payload = ModelserviceMessageParser.extract_request_payload(envelope, topic)

            if topic not in self.topic_handlers:
                self.logger.error(f"No handler found for topic: {topic}")
                return

            if topic == AICOTopics.MODELSERVICE_CHAT_REQUEST:
                response = await self.topic_handlers[topic](request_payload, correlation_id)
            elif topic == AICOTopics.MODELSERVICE_TTS_REQUEST:
                async for chunk in self.topic_handlers[topic](request_payload):
                    await self.bus_client.publish(AICOTopics.MODELSERVICE_TTS_STREAM, chunk)
                return
            else:
                response = await self.topic_handlers[topic](request_payload)

            if correlation_id and self.bus_client:
                reply_to = envelope.metadata.attributes.get("reply_to")
                response_topic = reply_to or self._get_response_topic(topic)
                if response_topic:
                    await self.bus_client.publish(response_topic, response, correlation_id=correlation_id)

        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def _get_response_topic(self, request_topic: str) -> Optional[str]:
        response_mapping = {
            AICOTopics.MODELSERVICE_HEALTH_REQUEST: AICOTopics.MODELSERVICE_HEALTH_RESPONSE,
            AICOTopics.MODELSERVICE_CHAT_REQUEST: AICOTopics.MODELSERVICE_CHAT_RESPONSE,
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST: AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
            AICOTopics.MODELSERVICE_MODELS_REQUEST: AICOTopics.MODELSERVICE_MODELS_RESPONSE,
            AICOTopics.MODELSERVICE_MODEL_INFO_REQUEST: AICOTopics.MODELSERVICE_MODEL_INFO_RESPONSE,
            AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST: AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
            AICOTopics.MODELSERVICE_NER_REQUEST: AICOTopics.MODELSERVICE_NER_RESPONSE,
            AICOTopics.MODELSERVICE_SENTIMENT_REQUEST: AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE,
            AICOTopics.MODELSERVICE_STATUS_REQUEST: AICOTopics.MODELSERVICE_STATUS_RESPONSE,
        }
        return response_mapping.get(request_topic)
