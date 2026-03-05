"""
NATS message handlers for modelservice - pure Protocol Buffer implementation.

This module implements NATS request/response handlers that work directly with
Protocol Buffer messages, providing type-safe message handling.
"""

import sys
import os
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, List
import httpx
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
# SpaCy removed - now using GLiNER for entity extraction
from .transformers_manager import TransformersManager
from aico.core.version import get_modelservice_version
from modelservice.handlers.tts_factory import TtsFactory
from aico.ai.llm.factory import LLMClientFactory
from aico.proto.aico_modelservice_pb2 import (
    HealthResponse, CompletionsResponse, ModelsResponse, ModelInfoResponse,
    EmbeddingsRequest, EmbeddingsResponse, NerResponse, EntityList, EntityWithConfidence, StatusResponse, ModelInfo, ServiceStatus, OllamaStatus,
    SentimentRequest, SentimentResponse, IntentClassificationRequest, IntentClassificationResponse,
    TtsRequest, TtsStreamChunk
)
from google.protobuf.timestamp_pb2 import Timestamp

# Logger will be initialized in class constructor to avoid import-time issues


class ModelserviceHandlers:
    """NATS message handlers for modelservice functionality."""
    
    def __init__(self, config: dict, ollama_manager, message_bus_client=None, config_manager=None):
        # Initialize logger first
        self.logger = get_logger("modelservice.core.handlers")
        
        self.logger.debug("ModelserviceHandlers constructor called - initializing...")
        self.logger.debug("ModelserviceHandlers constructor called - initializing...")
        self.config = config
        self.message_bus_client = message_bus_client
        self.version = get_modelservice_version()
        
        # Track start time for uptime calculation
        import time
        self.start_time = time.time()
        
        # Store config manager for components that need it
        self.config_manager = config_manager

        # LLM client (vLLM)
        self.llm_client = None
        try:
            if self.config_manager is not None:
                llm_config = self.config_manager.get("llm", {})
                if llm_config:
                    self.llm_client = LLMClientFactory.create(llm_config)
        except Exception:
            self.llm_client = None
        
        # SpaCy manager removed - using GLiNER via TransformersManager
        
        # Initialize Transformers manager lazily (only when needed)
        self.transformers_manager = None
        
        self.logger.debug("About to initialize NER system...")
        # Initialize GLiNER models asynchronously - will be done during startup
        self.ner_initialized = False
        self.transformers_initialized = False
        
        # Initialize TTS handler with config manager (uses factory for engine selection)
        self.tts_handler = TtsFactory.create_handler(config_manager=self.config_manager)
        self.tts_initialized = False
        
        self.logger.debug("ModelserviceHandlers initialization complete")
    
    def get_transformer_model(self, model_name: str) -> Any:
        """Get transformer model from TransformersManager.
        
        Args:
            model_name: Name of the model to retrieve
            
        Returns:
            Model instance or None if not available
        """
        try:
            # Lazy initialization of TransformersManager
            if self.transformers_manager is None:
                from aico.core.config import ConfigurationManager
                self.config_manager = ConfigurationManager()
                self.transformers_manager = TransformersManager(self.config_manager)
                
            # Get the model from the transformers manager
            return self.transformers_manager.get_model(model_name)
        except Exception as e:
            self.logger.error(f"Failed to get transformer model '{model_name}': {e}")
            return None
    
    async def initialize_ner_system(self):
        """Initialize the NER system using GLiNER via TransformersManager."""
        if self.ner_initialized:
            return
        
        try:
            self.logger.debug("Starting GLiNER NER system initialization...")
            
            # Lazy initialization of TransformersManager if not already done
            if self.transformers_manager is None:
                from aico.core.config import ConfigurationManager
                self.config_manager = ConfigurationManager()
                self.transformers_manager = TransformersManager(self.config_manager)
            
            # Ensure GLiNER model is loaded via transformers manager
            await self.transformers_manager.ensure_models_loaded()
            
            # Check if entity extraction model is available
            gliner_model = self.transformers_manager.get_model("entity_extraction")
            if gliner_model is not None:
                self.logger.debug("GLiNER NER system initialization completed successfully")
                self.ner_initialized = True
            else:
                self.logger.warning("GLiNER model not available - NER system not initialized")
                self.ner_initialized = False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize GLiNER NER system: {e}")
            self.ner_initialized = False
            import traceback
            self.logger.error(f"NER initialization traceback: {traceback.format_exc()}")
    
    async def initialize_transformers_system(self):
        """Initialize the Transformers system asynchronously using TransformersManager."""
        self.logger.debug(f"🔍 [INIT_CHECK] initialize_transformers_system() called - transformers_initialized={self.transformers_initialized}")
        
        if self.transformers_initialized:
            self.logger.debug("✅ Transformers system already initialized - skipping")
            return
        
        try:
            self.logger.debug(f"🔍 [INIT_START] Starting NEW Transformers initialization - transformers_initialized={self.transformers_initialized}")
            self.logger.debug("Starting Transformers system initialization...")
            
            # Lazy initialization of TransformersManager
            if self.transformers_manager is None:
                from aico.core.config import ConfigurationManager
                self.config_manager = ConfigurationManager()
                self.transformers_manager = TransformersManager(self.config_manager)
            
            # Initialize transformers models
            success = await self.transformers_manager.initialize_models()
            
            if success:
                # Get all required models from the transformers manager
                required_models = [
                    config for config in self.transformers_manager.model_configs.values() 
                    if config.required
                ]
                
                loaded_models = []
                failed_models = []
                
                # Check each required model
                for model_config in required_models:
                    model = self.transformers_manager.get_model(model_config.name)
                    self.logger.debug(f"Checking model {model_config.name}: {model is not None}")
                    if model is not None:
                        self.logger.debug(f"✅ {model_config.description} verified and ready")
                        loaded_models.append(model_config.name)
                    else:
                        self.logger.warning(f"⚠️ {model_config.description} verification failed")
                        failed_models.append(model_config.name)
                
                # Dynamic summary based on actual required models
                loaded_count = len(loaded_models)
                total_count = len(required_models)
                
                self.transformers_initialized = True
                self.logger.debug("✅ Transformers system initialized successfully")
                self.logger.debug(f"✅ Transformers System Ready: {loaded_count}/{total_count} required models loaded")
                
                if loaded_count == total_count:
                    self.logger.debug(f"🎯 All transformer models operational: {', '.join(loaded_models)}")
                else:
                    self.logger.debug(f"✅ Operational models: {', '.join(loaded_models)}")
                    if failed_models:
                        self.logger.warning(f"⚠️  Failed models: {', '.join(failed_models)} - some features may be limited")
            else:
                self.logger.error("❌ Transformers system initialization failed")
                self.logger.error("❌ Transformers System Failed: Models not available")
                
        except Exception as e:
            import traceback
            self.logger.error(f"Failed to initialize Transformers system: {e}")
            self.logger.error(f"Transformers initialization traceback: {traceback.format_exc()}")
    
    def _get_gliner_model(self):
        """Get GLiNER model for entity extraction."""
        return self.transformers_manager.get_model("entity_extraction")
        
    async def handle_health_request(self, request_payload) -> HealthResponse:
        """Handle health check requests via Protocol Buffers."""
        response = HealthResponse()
        
        try:
            # Perform comprehensive health check
            health_data = await self._check_system_health()
            
            response.success = True
            response.status = health_data["status"]
            
            # Add uptime in seconds
            import time
            response.uptime_seconds = time.time() - self.start_time
            
            self.logger.debug(
                f"Health check completed: {health_data['status']}",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
            
        except Exception as e:
            response.success = False
            response.status = "error"
            response.error = f"Health check failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_chat_request(self, request_payload, correlation_id=None) -> CompletionsResponse:
        from modelservice.core.metrics import track_inference

        """Handle chat requests via Protocol Buffers (conversational with message arrays)."""
        response = CompletionsResponse()
        
        try:
            self.logger.debug(f"[CHAT] Processing chat request: {type(request_payload)}")
            
            # Extract data from Protocol Buffer request
            model = request_payload.model
            messages = request_payload.messages
            
            self.logger.debug(f"[CHAT] Request details - model: '{model}', messages count: {len(messages)}")
            
            if not model or not messages:
                error_msg = "Model and messages are required"
                self.logger.error(f"[CHAT] Validation failed: {error_msg}")
                response.success = False
                response.error = error_msg
                return response
            
            self._require_llm_client()

            llm_messages = []
            for msg in messages:
                if msg.content:
                    llm_messages.append({"role": msg.role, "content": msg.content})

            from aico.proto.aico_modelservice_pb2 import CompletionResult, ConversationMessage
            with track_inference(model, task_type="chat") as tracker:
                llm_response = await self.llm_client.chat_completion(
                    messages=llm_messages,
                    model=model,
                    stream=False,
                )
                assistant_content = (
                    (llm_response.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                result = CompletionResult()
                result.model = model
                result.done = True
                response_msg = ConversationMessage()
                response_msg.role = "assistant"
                response_msg.content = assistant_content
                result.message.CopyFrom(response_msg)
                tracker.set_success(True)
                response.success = True
                response.result.CopyFrom(result)
                
        except Exception as e:
            error_msg = f"Chat request failed: {str(e)}"
            self.logger.error(f"[CHAT] ❌ CRITICAL ERROR: {error_msg}")
            self.logger.error(f"[CHAT] Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"[CHAT] Full traceback: {traceback.format_exc()}")
            response.success = False
            response.error = error_msg
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_completions_request(self, request_payload) -> CompletionsResponse:
        """Handle completions requests via Protocol Buffers (single prompt analysis tasks)."""
        response = CompletionsResponse()
        
        try:
            self.logger.info(f"[COMPLETIONS] Processing completions request: {type(request_payload)}")
            
            # Extract data from Protocol Buffer request
            model = request_payload.model
            
            # CompletionsRequest uses messages field, extract the prompt from it
            if hasattr(request_payload, 'prompt') and request_payload.prompt:
                # Direct prompt field (if available)
                prompt = request_payload.prompt
            elif hasattr(request_payload, 'messages') and request_payload.messages:
                # Extract prompt from messages (convert messages to single prompt)
                prompt_parts = []
                for msg in request_payload.messages:
                    if hasattr(msg, 'content'):
                        prompt_parts.append(f"{msg.role}: {msg.content}")
                    else:
                        prompt_parts.append(str(msg))
                prompt = "\n".join(prompt_parts)
            else:
                prompt = ""
            
            self.logger.info(f"[COMPLETIONS] Request details - model: '{model}', prompt: '{prompt[:100]}...'")
            
            if not model or not prompt:
                error_msg = "Model and prompt are required"
                self.logger.error(f"[COMPLETIONS] Validation failed: {error_msg}")
                response.success = False
                response.error = error_msg
                return response
            
            self._require_llm_client()

            from aico.proto.aico_modelservice_pb2 import CompletionResult, ConversationMessage
            with track_inference(model, task_type="completion") as tracker:
                llm_response = await self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    stream=False,
                )
                response_content = (
                    (llm_response.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                result = CompletionResult()
                result.model = model
                result.created_at.GetCurrentTime()
                result.done = True
                result.message.role = "assistant"
                result.message.content = response_content
                response.success = True
                response.result.CopyFrom(result)
                tracker.set_success(True)
                
        except Exception as e:
            error_msg = f"Completion failed: {str(e)}"
            self.logger.error(f"[COMPLETIONS] ❌ CRITICAL ERROR: {error_msg}")
            self.logger.error(f"[COMPLETIONS] Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"[COMPLETIONS] Full traceback: {traceback.format_exc()}")
            response.success = False
            response.error = error_msg
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_models_request(self, request_payload) -> ModelsResponse:
        """Handle models list requests via Protocol Buffers."""
        response = ModelsResponse()
        
        try:
            self._require_llm_client()
            model_ids = await self.llm_client.list_models()
            for model_id in model_ids:
                model_info = ModelInfo()
                model_info.name = model_id
                model_info.model = model_id
                response.models.append(model_info)

            response.success = True

            self.logger.info(
                f"Retrieved {len(response.models)} models from vLLM",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
                
        except Exception as e:
            response.success = False
            response.error = f"Models request failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_model_info_request(self, request_payload) -> ModelInfoResponse:
        """Handle model info requests via Protocol Buffers."""
        response = ModelInfoResponse()
        
        try:
            model_name = request_payload.model
            if not model_name:
                response.success = False
                response.error = "model is required"
                return response
            
            self._require_llm_client()
            from aico.proto.aico_modelservice_pb2 import ModelDetails
            details = ModelDetails()
            details.family = "vllm"

            response.success = True
            response.details.CopyFrom(details)

            self.logger.info(
                f"Retrieved info for model {model_name}",
                extra={"topic": AICOTopics.LOGS_ENTRY},
            )
                
        except Exception as e:
            response.success = False
            response.error = f"Model info request failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_embeddings_request(self, request: EmbeddingsRequest) -> EmbeddingsResponse:
        """Handle embeddings generation request using transformer models."""
        from modelservice.core.metrics import track_inference
        
        start_time = time.time()
        response = EmbeddingsResponse()
        
        try:
            model = request.model
            prompt = request.prompt
            text_length = len(prompt) if prompt else 0
            
            self.logger.debug(f"Embedding request: model={model}, length={text_length}")
            
            if not model or not prompt:
                response.success = False
                response.error = "model and prompt are required"
                self.logger.error(f"Missing required parameters: model={model}, prompt_length={text_length}")
                return response
                
            # Ensure transformers system is initialized
            if not self.transformers_initialized:
                self.logger.info(f"Initializing transformers system for embeddings request (model={model})...")
                await self.initialize_transformers_system()
            
            # Use TransformersManager for all transformer models
            self.logger.debug(f"Getting transformer model: {model}")
            transformer_model = self.get_transformer_model(model)
            self.logger.debug(f"Transformer model result: {transformer_model is not None}")
            
            if transformer_model is None:
                response.success = False
                response.error = f"Transformer model '{model}' not available"
                self.logger.error(f"Transformer model '{model}' not available")
                return response
            
            # Generate embedding using transformer model from TransformersManager
            # Track inference metrics
            with track_inference(model, task_type="embedding") as tracker:
                try:
                    # Check if this is a SentenceTransformer model (for paraphrase-multilingual)
                    if hasattr(transformer_model, 'encode'):
                        # This is a SentenceTransformer model - use .encode() method
                        encode_start = time.time()
                        
                        # Run in thread pool to avoid blocking event loop and match warmup execution context
                        import asyncio
                        embedding = await asyncio.to_thread(transformer_model.encode, prompt, normalize_embeddings=True)
                        encode_time = time.time() - encode_start
                        
                        # Convert to list if it's a numpy array
                        if hasattr(embedding, 'tolist'):
                            embedding = embedding.tolist()
                        
                        embedding_dim = len(embedding)
                        response.embedding.extend(embedding)
                        response.success = True
                        
                        total_time = time.time() - start_time
                        # Log slow embeddings (>100ms)
                        if total_time > 0.1:
                            self.logger.debug(f"Embedding generated in {total_time*1000:.0f}ms (encode={encode_time*1000:.0f}ms, dim={embedding_dim})")
                        else:
                            self.logger.debug(f"Embedding: {total_time*1000:.0f}ms, dim={embedding_dim}")
                        
                    elif hasattr(transformer_model, 'tokenizer') and hasattr(transformer_model, 'model'):
                        # This is a standard transformer model with tokenizer/model components
                        self.logger.debug(f"Using standard transformer tokenizer/model for {model}")
                        
                        import torch
                        import numpy as np
                        
                        tokenizer = transformer_model.tokenizer
                        transformer = transformer_model.model
                        
                        # Tokenize and get embeddings
                        inputs = tokenizer(
                            prompt,
                            return_tensors="pt",
                            max_length=512,
                            truncation=True,
                            padding=True
                        )
                        
                        with torch.no_grad():
                            outputs = transformer(**inputs)
                            # Use [CLS] token embedding (first token)
                            embedding = outputs.last_hidden_state[:, 0, :].numpy().flatten()
                        
                        # Add embeddings to response
                        response.embedding.extend(embedding.tolist())
                        response.success = True
                        
                    else:
                        response.success = False
                        response.error = f"Model '{model}' type not supported for embeddings"
                        self.logger.error(f"Model '{model}' does not have expected interface (encode() or tokenizer/model)")
                        return response
                    
                    tracker.set_success(True)
                    self.logger.info(
                        f"Generated transformer embeddings for model {model}",
                        extra={"topic": AICOTopics.LOGS_ENTRY}
                    )
                    
                except Exception as transformer_error:
                    tracker.set_success(False)
                    tracker.set_error(str(transformer_error))
                    response.success = False
                    response.error = f"Transformer embedding failed: {str(transformer_error)}"
                    self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
                
        except Exception as e:
            response.success = False
            response.error = f"Embeddings request failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_ner_request(self, request_payload) -> Any:
        """Handle NER (Named Entity Recognition) requests via GLiNER."""
        from modelservice.core.metrics import track_inference
        
        try:
            import time
            handler_start = time.time()
            print(f"🔍 [NER_DEEP_ANALYSIS] ModelService.handle_ner_request() STARTED [{handler_start:.6f}]")
            
            from aico.proto.aico_modelservice_pb2 import NerResponse, EntityList
            
            response = NerResponse()
            text = request_payload.text
            print(f"🔍 [NER_DEEP_ANALYSIS] Extracted text from request: '{text}'")
            
            if not text:
                print(f"🔍 [NER_DEEP_ANALYSIS] ERROR: No text provided")
                response.success = False
                response.error = "text is required"
                return response
            
            self.logger.info(f"Processing NER for text: {text[:50]}...")
            
            # Get GLiNER model from transformers manager
            model_start = time.time()
            print(f"🔍 [NER_DEEP_ANALYSIS] Getting GLiNER model [{model_start:.6f}]")
            gliner_model = self.transformers_manager.get_model("entity_extraction")
            model_end = time.time()
            model_duration = model_end - model_start
            print(f"🔍 [NER_DEEP_ANALYSIS] GLiNER model retrieved in {model_duration*1000:.2f}ms [{model_end:.6f}]")
            print(f"🔍 [NER_DEEP_ANALYSIS] GLiNER model object: {gliner_model}")
            if gliner_model is None:
                print(f"🔍 [NER_DEEP_ANALYSIS] ERROR: GLiNER model is None")
                response.success = False
                response.error = "GLiNER model not available"
                return response
            
            # Use entity types from request if provided, otherwise use defaults
            if request_payload.entity_types:
                entity_types = list(request_payload.entity_types)
                print(f"🔍 [NER_DEEP_ANALYSIS] Using {len(entity_types)} entity types from request")
            else:
                # V5: Balanced entity types (12 types) - optimized from testing
                entity_types = [
                    # Core standard (5) - industry baseline
                    "Person", "Organization", "Location", "Date", "Time",
                    
                    # Conversational context (4) - proven effective in testing
                    "Event", "Activity", "Emotion", "Relationship",
                    
                    # User preferences/goals (3) - important for memory personalization
                    "Preference", "Skill", "Goal"
                ]
                print(f"🔍 [NER_DEEP_ANALYSIS] Using default {len(entity_types)} entity types")
            
            # Use threshold from request if provided, otherwise default to 0.5
            threshold = request_payload.threshold if request_payload.HasField('threshold') else 0.5
            
            # Track NER inference metrics
            self.logger.info(f"🔍 [NER_METRICS] Starting NER inference tracking for text: {text[:50]}...")
            with track_inference("gliner", task_type="ner") as tracker:
                inference_start = time.time()
                print(f"🔍 [NER_DEEP_ANALYSIS] Starting GLiNER inference [{inference_start:.6f}]")
                raw_entities = gliner_model.predict_entities(
                    text,
                    labels=entity_types,
                    threshold=threshold,
                    flat_ner=False,  # Allow nested entities to capture complex phrases like "website redesign project"
                    multi_label=False  # Avoid overlapping entity classifications
                )
                inference_end = time.time()
                inference_duration = inference_end - inference_start
                print(f"🔍 [NER_DEEP_ANALYSIS] GLiNER inference COMPLETED in {inference_duration*1000:.2f}ms [{inference_end:.6f}]")
                
                # Log entity count for monitoring
                self.logger.debug(f"GLiNER extracted {len(raw_entities)} raw entities")
                
                # Track metrics
                tracker.set_success(True)
                tracker.set_entities(len(raw_entities), entity_types)
                self.logger.info(f"🔍 [NER_METRICS] ✅ NER metrics recorded: {len(raw_entities)} entities, duration: {inference_duration*1000:.2f}ms")
            
            # Group entities by type with intelligent filtering - PRESERVE CONFIDENCE SCORES
            entities = {}
            
            for entity in raw_entities:
                entity_type = entity["label"].upper()
                entity_text = entity["text"].strip()
                
                # Skip empty entities
                if not entity_text:
                    self.logger.info(f"🔍 [GLINER_FILTER] REJECTED: Empty entity text")
                    continue
                
                # INTELLIGENT FILTERING: Use GLiNER confidence and linguistic rules
                confidence = entity.get("score", 0.0)
                
                # Respect the threshold parameter - don't add additional filtering
                # The threshold was already applied by GLiNER during extraction
                # Additional filtering here defeats the purpose of the configurable threshold
                
                # Clean possessive forms intelligently
                if entity_text.lower().endswith(("'s", "'s")):
                    entity_text = entity_text[:-2].strip()
                
                
                # V5: Normalize GLiNER Title Case outputs to standard NER types
                # Balanced set (12 types) optimized from testing
                type_normalization = {
                    "PERSON": "PERSON",
                    "ORGANIZATION": "ORG",
                    "LOCATION": "GPE",  # Geopolitical entity
                    "DATE": "DATE",
                    "TIME": "TIME",
                    "EVENT": "EVENT",
                    "ACTIVITY": "ACTIVITY",
                    "EMOTION": "EMOTION",
                    "RELATIONSHIP": "RELATIONSHIP",
                    "PREFERENCE": "PREFERENCE",
                    "SKILL": "SKILL",
                    "GOAL": "GOAL"
                }
                
                entity_type = type_normalization.get(entity_type, entity_type)
                
                if entity_type not in entities:
                    entities[entity_type] = []
                
                # Store entity with confidence - check for duplicates by text only
                entity_with_confidence = {"text": entity_text, "confidence": confidence}
                existing_texts = [e["text"] if isinstance(e, dict) else e for e in entities[entity_type]]
                
                if entity_text not in existing_texts:
                    entities[entity_type].append(entity_with_confidence)
                    self.logger.info(f"🔍 [GLINER_FILTER] ✅ ACCEPTED: '{entity_text}' (type: {entity_type}, confidence: {confidence:.3f})")
                else:
                    self.logger.info(f"🔍 [GLINER_FILTER] REJECTED: Duplicate - '{entity_text}' (type: {entity_type})")
            
            # Create protobuf response
            response.success = True
            
            for entity_type, entity_list in entities.items():
                # Create EntityWithConfidence objects for the new protobuf structure
                for entity_data in entity_list:
                    entity_with_conf = EntityWithConfidence()
                    entity_with_conf.text = entity_data["text"]
                    entity_with_conf.confidence = entity_data["confidence"]
                    response.entities[entity_type].entities.append(entity_with_conf)
            
            # Log results with detailed breakdown
            total_entities = sum(len(v) for v in entities.values())
            self.logger.info(f"🔍 [GLINER_FINAL] ✅ FINAL RESULT: {total_entities} entities extracted from '{text}'")
            for entity_type, entity_list in entities.items():
                self.logger.info(f"🔍 [GLINER_FINAL] {entity_type}: {entity_list}")
            
            self.logger.info(
                f"Extracted {total_entities} entities using GLiNER",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
            
            # Debug logging of detailed NER results
            if entities:
                self.logger.debug(f"[NER] Detailed extraction results for text: '{text[:100]}...'")
                for entity_type, entity_list in entities.items():
                    self.logger.debug(f"[NER] {entity_type}: {entity_list}")
            else:
                self.logger.debug(f"[NER] No entities extracted from text: '{text[:100]}...'")
            
            handler_end = time.time()
            handler_duration = handler_end - handler_start
            print(f"🔍 [NER_DEEP_ANALYSIS] ModelService.handle_ner_request() COMPLETED in {handler_duration*1000:.2f}ms [{handler_end:.6f}]")
            return response
            
        except Exception as e:
            import traceback
            print(f"🔍 [NER_DEEP_ANALYSIS] EXCEPTION in handle_ner_request(): {str(e)}")
            print(f"🔍 [NER_DEEP_ANALYSIS] TRACEBACK: {traceback.format_exc()}")
            from aico.proto.aico_modelservice_pb2 import NerResponse
            response = NerResponse()
            response.success = False
            response.error = f"NER request failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
            return response
    
    async def handle_sentiment_request(self, request_payload) -> Any:
        """Handle sentiment analysis requests via Protocol Buffers."""
        from modelservice.core.metrics import track_inference
        
        try:
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] ✅ Sentiment request received!")
            response = SentimentResponse()
            text = request_payload.text
            
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Request text: '{text[:100]}...'")
            
            if not text:
                self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ No text provided in request")
                response.success = False
                response.error = "text is required"
                return response
            
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Processing sentiment for text: {text[:50]}...")
            
            # Ensure transformers system is initialized
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Checking transformers initialization: {self.transformers_initialized}")
            if not self.transformers_initialized:
                self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Initializing transformers system...")
                await self.initialize_transformers_system()
            
            if not self.transformers_initialized:
                self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ Transformers system not available after initialization")
                response.success = False
                response.error = "Transformers system not available"
                return response
            
            # Get sentiment pipeline from TransformersManager
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Getting sentiment pipeline...")
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Available model configs: {list(self.transformers_manager.model_configs.keys())}")
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Loaded models: {list(self.transformers_manager.loaded_models.keys())}")
            
            sentiment_pipeline = await self.transformers_manager.get_pipeline("sentiment_multilingual")
            if sentiment_pipeline is None:
                self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ Sentiment pipeline not available")
                self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ Model configs: {list(self.transformers_manager.model_configs.keys())}")
                self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ Loaded models: {list(self.transformers_manager.loaded_models.keys())}")
                response.success = False
                response.error = "Sentiment analysis model not available"
                return response
            
            self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] ✅ Sentiment pipeline obtained successfully")
            
            # Analyze sentiment with metrics tracking
            with track_inference("sentiment_multilingual", task_type="sentiment") as tracker:
                try:
                    self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Running sentiment pipeline on text...")
                    result = sentiment_pipeline(text)
                    
                    self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Raw pipeline result: {result}")
                    
                    # Extract sentiment and confidence
                    if result and len(result) > 0:
                        # Handle different result formats
                        if isinstance(result, list) and isinstance(result[0], list):
                            # Format: [[{'label': '3 stars', 'score': 0.268}]]
                            sentiment_result = result[0][0]
                        elif isinstance(result, list) and isinstance(result[0], dict):
                            # Format: [{'label': '3 stars', 'score': 0.268}]
                            sentiment_result = result[0]
                        else:
                            self.logger.error(f"🔍 [SENTIMENT_HANDLER_DEBUG] ❌ Unexpected result format: {type(result)}")
                            tracker.set_success(False)
                            tracker.set_error(f"Unexpected result format: {type(result)}")
                            response.success = False
                            response.error = f"Unexpected result format: {type(result)}"
                            return response
                            
                        label = sentiment_result['label'].lower()
                        confidence = sentiment_result['score']
                        
                        self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] Extracted - Label: '{label}', Confidence: {confidence}")
                        
                        # Map model labels to standard format
                        # nlptown/bert-base-multilingual-uncased-sentiment uses star ratings
                        if label in ['5 stars', '4 stars']:
                            sentiment = 'positive'
                        elif label in ['1 star', '2 stars']:
                            sentiment = 'negative'
                        elif label in ['3 stars']:
                            sentiment = 'neutral'
                        else:
                            # Fallback for other models that might use different labels
                            if label in ['positive', 'pos']:
                                sentiment = 'positive'
                            elif label in ['negative', 'neg']:
                                sentiment = 'negative'
                            else:
                                sentiment = 'neutral'
                        
                        self.logger.info(f"🔍 [SENTIMENT_HANDLER_DEBUG] ✅ Mapped sentiment: '{sentiment}' (confidence: {confidence})")
                        
                        # Record metrics
                        tracker.set_confidence(confidence)
                        tracker.set_sentiment(sentiment)
                        tracker.set_success(True)
                        
                        response.success = True
                        response.sentiment = sentiment
                        response.confidence = confidence
                        
                        self.logger.info(
                            f"Sentiment analysis complete: {sentiment} (confidence: {confidence:.3f})",
                            extra={"topic": AICOTopics.LOGS_ENTRY}
                        )
                    else:
                        tracker.set_success(False)
                        tracker.set_error("No sentiment result returned")
                        response.success = False
                        response.error = "No sentiment result returned"
                    
                except Exception as sentiment_error:
                    tracker.set_success(False)
                    tracker.set_error(str(sentiment_error))
                    response.success = False
                    response.error = f"Sentiment analysis failed: {str(sentiment_error)}"
                    self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
            
            return response
            
        except Exception as e:
            response = SentimentResponse()
            response.success = False
            response.error = f"Sentiment analysis failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
            return response
    
    async def handle_intent_request(self, request_payload) -> IntentClassificationResponse:
        """Handle intent classification requests using zero-shot NLI."""
        import time
        handler_start = time.time()
        print(f"⏱️ [INTENT_TIMING] Handler started at {handler_start}")
        
        try:
            self.logger.info("🔍 [INTENT_HANDLER] Intent classification request received")
            response = IntentClassificationResponse()
            
            # Extract request data
            extract_start = time.time()
            text = request_payload.text
            model = request_payload.model if request_payload.HasField('model') else "intent_classification"
            extract_time = time.time() - extract_start
            print(f"⏱️ [INTENT_TIMING] Text extraction took {extract_time*1000:.2f}ms")
            
            self.logger.info(f"🔍 [INTENT_HANDLER] Text: '{text[:50]}...', Model: {model}")
            
            if not text:
                response.success = False
                response.error = "text is required"
                response.predicted_intent = "general"
                response.confidence = 0.0
                return response
            
            # Ensure transformers system is initialized
            if not self.transformers_initialized:
                self.logger.info("🔍 [INTENT_HANDLER] Initializing transformers system...")
                await self.initialize_transformers_system()
            
            # Get zero-shot classification pipeline
            get_model_start = time.time()
            classifier = self.transformers_manager.get_model("intent_classification")
            get_model_time = time.time() - get_model_start
            print(f"⏱️ [INTENT_TIMING] Getting classifier took {get_model_time*1000:.2f}ms")
            
            if classifier is None:
                self.logger.error("❌ [INTENT_HANDLER] Zero-shot classifier not available")
                response.success = False
                response.error = "Intent classification model not available"
                response.predicted_intent = "general"
                response.confidence = 0.0
                return response
            
            # Define intent labels for classification
            intent_labels = [
                "greeting", "question", "request", "information_sharing",
                "confirmation", "negation", "complaint", "farewell", "general"
            ]
            
            self.logger.info("🔍 [INTENT_HANDLER] Running zero-shot classification...")
            print(f"⏱️ [INTENT_TIMING] About to run classification...")
            
            # Run classification in thread pool to avoid blocking
            import asyncio
            classify_start = time.time()
            result = await asyncio.to_thread(
                classifier,
                text,
                intent_labels,
                multi_label=False
            )
            classify_time = time.time() - classify_start
            print(f"⏱️ [INTENT_TIMING] Classification took {classify_time*1000:.2f}ms")
            
            print(f"⏱️ [INTENT_TIMING] About to log result...")
            self.logger.info(f"🔍 [INTENT_HANDLER] Result: {result}")
            print(f"⏱️ [INTENT_TIMING] Result logged, extracting...")
            
            # Extract results
            extract_result_start = time.time()
            print(f"⏱️ [INTENT_TIMING] Checking result validity...")
            if result and result.get('labels') and result.get('scores'):
                print(f"⏱️ [INTENT_TIMING] Result is valid, extracting fields...")
                response.success = True
                response.predicted_intent = result['labels'][0]
                response.confidence = result['scores'][0]
                print(f"⏱️ [INTENT_TIMING] 📊 CLASSIFIED: intent='{result['labels'][0]}', confidence={result['scores'][0]:.4f}")
                response.detected_language = "unknown"  # Could add language detection
                print(f"⏱️ [INTENT_TIMING] Main fields extracted, adding alternatives...")
                
                # Add alternative predictions
                try:
                    alternatives_data = list(zip(result['labels'][1:4], result['scores'][1:4]))
                    for label, score in alternatives_data:
                        alt = response.alternative_predictions.add()
                        alt.intent = label
                        alt.confidence = float(score)  # Ensure it's a Python float, not numpy
                except Exception as e:
                    print(f"⏱️ [INTENT_TIMING] Error adding alternatives: {e}")
                    # Continue without alternatives if there's an error
                
                print(f"⏱️ [INTENT_TIMING] Alternatives added")
                extract_result_time = time.time() - extract_result_start
                print(f"⏱️ [INTENT_TIMING] Extracting results took {extract_result_time*1000:.2f}ms")
                
                self.logger.info(f"✅ [INTENT_HANDLER] Classified as: {response.predicted_intent} "
                               f"(confidence={response.confidence:.3f})")
            else:
                response.success = False
                response.error = "No classification result returned"
                response.predicted_intent = "general"
                response.confidence = 0.0
            
            handler_total = time.time() - handler_start
            print(f"⏱️ [INTENT_TIMING] ✅ TOTAL HANDLER TIME: {handler_total*1000:.2f}ms")
            print(f"⏱️ [INTENT_TIMING] Handler returning response at {time.time()}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ [INTENT_HANDLER] Intent classification failed: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            response = IntentClassificationResponse()
            response.success = False
            response.predicted_intent = "general"
            response.confidence = 0.0
            response.detected_language = "unknown"

            return response

    async def handle_status_request(self, request_payload) -> StatusResponse:
        """Handle service status requests."""
        response = StatusResponse()

        try:
            status = ServiceStatus()
            status.version = self.version
            status.ollama_running = False
            status.ollama_version = "retired"

            vllm_models_count = 0
            try:
                self._require_llm_client()
                status.ollama_running = True
                model_ids = await self.llm_client.list_models()
                for model_id in model_ids:
                    status.loaded_models.append(model_id)
                vllm_models_count = len(model_ids)
            except Exception as e:
                self.logger.debug(f"Could not query vLLM models: {e}")

            transformers_models_count = 0
            if self.transformers_manager is not None:
                try:
                    loaded_transformers = list(self.transformers_manager.loaded_models.keys())
                    transformers_models_count = len(loaded_transformers)
                    for model_name in loaded_transformers:
                        status.loaded_models.append(model_name)
                except Exception as e:
                    self.logger.debug(f"Could not query TransformersManager models: {e}")

            status.loaded_models_count = vllm_models_count + transformers_models_count

            response.success = True
            response.status.CopyFrom(status)

            self.logger.info("Status request completed", extra={"topic": AICOTopics.LOGS_ENTRY})
            return response

        except Exception as e:
            response.success = False
            response.error = f"Status request failed: {str(e)}"
            self.logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
            return response

    async def _check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        health_data = {
            "status": "healthy",
            "checks": {},
            "issues": []
        }

        try:
            try:
                self._require_llm_client()
                vllm_ok = await self.llm_client.health_check()
                health_data["checks"]["vllm"] = {"available": bool(vllm_ok)}
                if not vllm_ok:
                    health_data["status"] = "degraded"
                    health_data["issues"].append("vLLM service unavailable")
            except Exception as e:
                health_data["checks"]["vllm"] = {"available": False, "error": str(e)}
                health_data["status"] = "degraded"
                health_data["issues"].append(f"vLLM check failed: {str(e)}")

            # Check API Gateway connectivity (optional)
            try:
                gateway_status = await self._check_gateway_status()
                health_data["checks"]["api_gateway"] = gateway_status
            except Exception as e:
                health_data["checks"]["api_gateway"] = {
                    "available": False,
                    "error": str(e)
                }

        except Exception as e:
            self.logger.error(f"Critical health check error: {str(e)}")
            health_data["status"] = "unhealthy"
            health_data["issues"].append(f"Critical health check error: {str(e)}")

        return health_data

    async def _check_ollama_status(self) -> Dict[str, Any]:
        return {"available": False, "error": "Ollama retired"}

    async def _check_gateway_status(self) -> dict:
        """Check API Gateway status (optional)."""
        try:
            gateway_url = f"http://{self.config.get('api_gateway', {}).get('host', 'localhost')}:{self.config.get('api_gateway', {}).get('port', 8771)}"

            async with httpx.AsyncClient(timeout=3.0) as client:
                start_time = time.time()
                response = await client.get(f"{gateway_url}/api/v1/health")
                response_time = (time.time() - start_time) * 1000

                return {
                    "available": response.status_code == 200,
                    "response_time_ms": round(response_time),
                    "url": gateway_url
                }

        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

    async def initialize_tts_system(self):
        """
        Initialize the TTS system using Coqui XTTS.

        This will block until the model is downloaded and loaded.
        On first run, this downloads ~1.8GB from HuggingFace.

        Raises:
            Exception: If TTS initialization fails
        """
        if self.tts_initialized:
            return

        self.logger.info("Starting TTS system initialization...")
        self.logger.info("⏳ This may take several minutes on first run (downloading ~1.8GB model)...")

        await self.tts_handler.initialize()
        self.tts_initialized = True
        self.logger.info("✅ TTS system initialized successfully")

    async def handle_tts_request(self, request: TtsRequest):
        """
        Handle TTS request and stream audio chunks.

        Args:
            request: TtsRequest protobuf message

        Yields:
            TtsStreamChunk messages with audio data
        """
        print("=" * 100)
        print(f"🎤 [MODELSERVICE] TTS REQUEST RECEIVED!")
        print(f"Text: {request.text[:100]}...")
        print(f"Language: {request.language}")
        print(f"TTS initialized: {self.tts_initialized}")
        print("=" * 100)

        if not self.tts_initialized:
            # Try to initialize on first request
            await self.initialize_tts_system()

            if not self.tts_initialized:
                # Still not initialized - return error
                yield TtsStreamChunk(
                    audio_data=b"",
                    sample_rate=0,
                    is_final=True,
                    error="TTS system not initialized"
                )
                return

        try:
            self.logger.info(f"🎤 TTS request: {len(request.text)} chars, language: {request.language}")

            # Stream audio chunks
            actual_sample_rate = 22050  # Default fallback
            async for audio_bytes, sample_rate in self.tts_handler.synthesize_stream(
                text=request.text,
                language=request.language,
                speed=request.speed if request.speed else 1.0
            ):
                actual_sample_rate = sample_rate  # Track the actual sample rate
                yield TtsStreamChunk(
                    audio_data=audio_bytes,
                    sample_rate=sample_rate,
                    is_final=False
                )

            # Send final chunk with correct sample rate
            yield TtsStreamChunk(
                audio_data=b"",
                sample_rate=actual_sample_rate,
                is_final=True
            )

            self.logger.info("✅ TTS request completed")

        except Exception as e:
            self.logger.error(f"TTS request failed: {e}", exc_info=True)
            yield TtsStreamChunk(
                audio_data=b"",
                sample_rate=0,
                is_final=True,
                error=str(e)
            )

