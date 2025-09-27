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
    
    async def check_modelservice_health(self) -> bool:
        """Check if the modelservice is running and responding.
        
        Returns:
            bool: True if modelservice is healthy, False otherwise
        """
        try:
            # Use a very short timeout for health check
            original_timeout = self.config.timeout
            self.config.timeout = 2.0
            
            # Send a simple ping request
            result = await self._send_request(
                "modelservice/health/request/v1", 
                "modelservice/health/response/v1", 
                {"check": "ping"}
            )
            
            # Restore original timeout
            self.config.timeout = original_timeout
            return result.get('success', False)
        except TimeoutError:
            self.logger.error("⚠️ MODELSERVICE HEALTH CHECK FAILED - Service appears to be offline")
            print("⚠️ MODELSERVICE HEALTH CHECK FAILED - Service appears to be offline")
            return False
        except Exception as e:
            self.logger.error(f"⚠️ MODELSERVICE HEALTH CHECK FAILED: {e}")
            print(f"⚠️ MODELSERVICE HEALTH CHECK FAILED: {e}")
            return False
    
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
        import time
        start_time = time.time()
        
        # Add detailed debugging for embedding and chat requests
        is_embedding_request = "embeddings" in request_topic
        is_chat_request = "chat" in request_topic
        
        if is_embedding_request:
            self.logger.debug(f"🔍 [ZMQ_DEBUG] Starting {request_topic} request")
            text = data.get("prompt", "")
            text_length = len(text) if text else 0
            text_preview = text[:50] + "..." if text and len(text) > 50 else text
            self.logger.debug(f"🔍 [ZMQ_DEBUG] Text length: {text_length}, preview: '{text_preview}'")
        elif is_chat_request:
            self.logger.debug(f"💬 [CHAT_DEBUG] Starting {request_topic} request")
            messages = data.get("messages", [])
            message_count = len(messages)
            model = data.get("model", "unknown")
            self.logger.debug(f"💬 [CHAT_DEBUG] Model: {model}, Messages: {message_count}")
            if messages:
                last_msg = messages[-1]
                last_msg_content = last_msg.get("content", "")[:50] + "..." if len(last_msg.get("content", "")) > 50 else last_msg.get("content", "")
                self.logger.debug(f"💬 [CHAT_DEBUG] Last message: role='{last_msg.get('role', 'unknown')}', content='{last_msg_content}'")
        
        
        # Connection setup timing
        connection_start = time.time()
        # Reduced connection debug noise
        await self._ensure_connection()
        connection_time = time.time() - connection_start
        # Only log slow connections
        if is_embedding_request and connection_time > 0.1:
            print(f"⏱️ [MODELSERVICE_TIMING] SLOW connection: {connection_time:.4f}s")
            self.logger.debug(f"🔍 [ZMQ_DEBUG] Connection setup took {connection_time:.4f}s")
            self.logger.debug(f"💬 [CHAT_DEBUG] Connection setup took {connection_time:.4f}s")
        
        # Generate correlation ID for request/response matching
        correlation_id = str(uuid.uuid4())
        if is_embedding_request:
            self.logger.debug(f"🔍 [ZMQ_DEBUG] Using correlation_id: {correlation_id}")
        elif is_chat_request:
            self.logger.debug(f"💬 [CHAT_DEBUG] Using correlation_id: {correlation_id}")
        
        # Create proper protobuf message based on request type
        from aico.proto.aico_modelservice_pb2 import CompletionsRequest, HealthRequest, ModelsRequest, StatusRequest, EmbeddingsRequest, NerRequest, IntentClassificationRequest, SentimentRequest
        
        if "completions" in request_topic or "chat" in request_topic:
            # Create CompletionsRequest protobuf
            request_proto = CompletionsRequest()
            request_proto.model = data.get("model", "")
            if "messages" in data:
                # For chat requests with message arrays
                from aico.proto.aico_modelservice_pb2 import ConversationMessage
                for message in data["messages"]:
                    msg = request_proto.messages.add()
                    msg.role = message.get("role", "user")
                    msg.content = message.get("content", "")
            elif "prompt" in data:
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
        elif "embeddings" in request_topic:
            # Create EmbeddingsRequest protobuf
            protobuf_start = time.time()
            # Reduced protobuf debug noise
            request_proto = EmbeddingsRequest()
            request_proto.model = data.get("model", "")
            request_proto.prompt = data.get("prompt", "")
            protobuf_time = time.time() - protobuf_start
            # Only log slow protobuf creation
            if is_embedding_request and protobuf_time > 0.01:
                print(f"⏱️ [MODELSERVICE_TIMING] SLOW protobuf: {protobuf_time:.4f}s")
        elif "ner" in request_topic:
            # Create NerRequest protobuf
            request_proto = NerRequest()
            request_proto.text = data.get("text", "")
        elif "intent" in request_topic:
            # Create IntentClassificationRequest protobuf
            request_proto = IntentClassificationRequest()
            request_proto.text = data.get("text", "")
            if data.get("user_id"):
                request_proto.user_id = data["user_id"]
            if data.get("conversation_context"):
                request_proto.conversation_context.extend(data["conversation_context"])
        elif "sentiment" in request_topic:
            # Create SentimentRequest protobuf
            request_proto = SentimentRequest()
            request_proto.text = data.get("text", "")
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
                
                if hasattr(message, 'any_payload'):
                    # Handle embeddings responses
                    if "embeddings" in response_topic:
                        from aico.proto.aico_modelservice_pb2 import EmbeddingsResponse
                        embeddings_response = EmbeddingsResponse()
                        if message.any_payload.Unpack(embeddings_response):
                            self.logger.debug(f"Successfully unpacked EmbeddingsResponse: success={embeddings_response.success}")
                            response_data = {
                                'success': embeddings_response.success,
                                'error': embeddings_response.error if embeddings_response.HasField('error') else None
                            }
                            if embeddings_response.success and embeddings_response.embedding:
                                response_data['data'] = {'embedding': list(embeddings_response.embedding)}
                                self.logger.debug(f"Extracted embedding with {len(embeddings_response.embedding)} dimensions")
                            response_received.set()
                        else:
                            self.logger.error("Failed to unpack EmbeddingsResponse")
                            response_data = {'success': False, 'error': 'Failed to unpack response'}
                            response_received.set()
                    # Handle NER responses
                    elif "ner" in response_topic:
                        from aico.proto.aico_modelservice_pb2 import NerResponse
                        ner_response = NerResponse()
                        if message.any_payload.Unpack(ner_response):
                            self.logger.debug(f"Successfully unpacked NerResponse: success={ner_response.success}")
                            response_data = {
                                'success': ner_response.success,
                                'error': ner_response.error if ner_response.HasField('error') else None
                            }
                            if ner_response.success:
                                # Convert protobuf map to Python dict
                                entities = {}
                                for entity_type, entity_list in ner_response.entities.items():
                                    entities[entity_type] = list(entity_list.entities)
                                response_data['data'] = {'entities': entities}
                                self.logger.debug(f"Extracted {len(entities)} entity types")
                            response_received.set()
                        else:
                            self.logger.error("Failed to unpack NerResponse")
                            response_data = {'success': False, 'error': 'Failed to unpack response'}
                            response_received.set()
                    # Handle Intent Classification responses
                    elif "intent" in response_topic:
                        from aico.proto.aico_modelservice_pb2 import IntentClassificationResponse
                        intent_response = IntentClassificationResponse()
                        if message.any_payload.Unpack(intent_response):
                            self.logger.debug(f"Successfully unpacked IntentClassificationResponse: success={intent_response.success}")
                            response_data = {
                                'success': intent_response.success,
                                'error': intent_response.error if intent_response.HasField('error') else None
                            }
                            if intent_response.success:
                                # Extract intent classification data
                                alternatives = []
                                for alt in intent_response.alternative_predictions:
                                    alternatives.append((alt.intent, alt.confidence))
                                
                                response_data['data'] = {
                                    'predicted_intent': intent_response.predicted_intent,
                                    'confidence': intent_response.confidence,
                                    'detected_language': intent_response.detected_language,
                                    'inference_time_ms': intent_response.inference_time_ms,
                                    'alternatives': alternatives,
                                    'metadata': dict(intent_response.metadata)
                                }
                                self.logger.debug(f"Intent classified as: {intent_response.predicted_intent} (confidence={intent_response.confidence:.2f})")
                            response_received.set()
                        else:
                            self.logger.error("Failed to unpack IntentClassificationResponse")
                            response_data = {'success': False, 'error': 'Failed to unpack response'}
                            response_received.set()
                    # Handle Sentiment responses
                    elif "sentiment" in response_topic:
                        self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] ✅ Received sentiment response!")
                        from aico.proto.aico_modelservice_pb2 import SentimentResponse
                        sentiment_response = SentimentResponse()
                        if message.any_payload.Unpack(sentiment_response):
                            self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] ✅ Successfully unpacked SentimentResponse: success={sentiment_response.success}")
                            response_data = {
                                'success': sentiment_response.success,
                                'error': sentiment_response.error if sentiment_response.HasField('error') else None
                            }
                            if sentiment_response.success:
                                response_data['data'] = {
                                    'sentiment': sentiment_response.sentiment,
                                    'confidence': sentiment_response.confidence
                                }
                                self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] ✅ Extracted sentiment: {sentiment_response.sentiment} (confidence: {sentiment_response.confidence:.3f})")
                            else:
                                self.logger.error(f"🔍 [SENTIMENT_CLIENT_DEBUG] ❌ Sentiment response failed: {sentiment_response.error}")
                            response_received.set()
                        else:
                            self.logger.error("🔍 [SENTIMENT_CLIENT_DEBUG] ❌ Failed to unpack SentimentResponse")
                            response_data = {'success': False, 'error': 'Failed to unpack response'}
                            response_received.set()
                    else:
                        # Handle completions/chat responses
                        from aico.proto.aico_modelservice_pb2 import CompletionsResponse
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
                                    response_data['data'] = {'content': completions_response.result.message.content}
                                    self.logger.debug(f"Extracted message content: {completions_response.result.message.content[:100]}...")
                                elif hasattr(completions_response.result, 'content'):
                                    response_data['data'] = {'content': completions_response.result.content}
                                    self.logger.debug(f"Extracted content: {completions_response.result.content[:100]}...")
                                else:
                                    # Log available fields for debugging
                                    fields = [field.name for field in completions_response.result.DESCRIPTOR.fields]
                                    self.logger.debug(f"Available result fields: {fields}")
                                    response_data['data'] = {'content': str(completions_response.result)}
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
        subscription_start = time.time()
        # Reduced subscription debug noise
        await self.bus_client.subscribe(response_topic, handle_response)
        subscription_time = time.time() - subscription_start
        
        # Only log slow subscriptions
        if is_embedding_request and subscription_time > 0.01:
            print(f"⏱️ [MODELSERVICE_TIMING] SLOW subscription: {subscription_time:.4f}s")
            self.logger.debug(f"🔍 [ZMQ_DEBUG] Subscribed to {response_topic} in {subscription_time:.4f}s")
        elif is_chat_request:
            self.logger.debug(f"💬 [CHAT_DEBUG] Subscribed to {response_topic} in {subscription_time:.4f}s")
        
        try:
            # Send request with correlation ID
            publish_start = time.time()
            # Reduced publishing debug noise
            await self.bus_client.publish(request_topic, request_proto, correlation_id=correlation_id)
            publish_time = time.time() - publish_start
            
            # Only log slow publishing
            if is_embedding_request and publish_time > 0.01:
                print(f"⏱️ [MODELSERVICE_TIMING] SLOW publish: {publish_time:.4f}s")
                self.logger.debug(f"🔍 [ZMQ_DEBUG] Published to {request_topic} in {publish_time:.4f}s")
                self.logger.debug(f"🔍 [ZMQ_DEBUG] Waiting for response with timeout={self.config.timeout}s")
            elif is_chat_request:
                self.logger.debug(f"💬 [CHAT_DEBUG] Published to {request_topic} in {publish_time:.4f}s")
                self.logger.debug(f"💬 [CHAT_DEBUG] Waiting for response with timeout={self.config.timeout}s")
            
            # Wait for response with timeout
            wait_start = time.time()
            # Reduced wait debug noise
            await asyncio.wait_for(response_received.wait(), timeout=self.config.timeout)
            wait_time = time.time() - wait_start
            total_time = time.time() - start_time
            # Only log slow responses
            if is_embedding_request and wait_time > 0.2:
                print(f"⏱️ [MODELSERVICE_TIMING] SLOW response: {wait_time:.4f}s wait")
            
            if is_embedding_request:
                self.logger.debug(f"🔍 [ZMQ_DEBUG] ✅ Response received in {wait_time:.4f}s (total: {total_time:.4f}s)")
                self.logger.debug(f"🔍 [ZMQ_DEBUG] Performance breakdown: connection={connection_time:.4f}s, subscription={subscription_time:.4f}s, publish={publish_time:.4f}s, wait={wait_time:.4f}s")
            elif is_chat_request:
                self.logger.debug(f"💬 [CHAT_DEBUG] ✅ Response received in {wait_time:.4f}s (total: {total_time:.4f}s)")
                self.logger.debug(f"💬 [CHAT_DEBUG] Performance breakdown: connection={connection_time:.4f}s, subscription={subscription_time:.4f}s, publish={publish_time:.4f}s, wait={wait_time:.4f}s")
            
            return response_data
            
        except asyncio.TimeoutError:
            total_time = time.time() - start_time
            error_msg = f"Request timed out after {self.config.timeout}s - MODELSERVICE MAY BE OFFLINE"
            
            if is_embedding_request:
                print(f"⏱️ [MODELSERVICE_TIMING] ❌ TIMEOUT after {total_time:.4f}s!")
                print(f"⏱️ [MODELSERVICE_TIMING] Breakdown: connection={connection_time:.4f}s, subscription={subscription_time:.4f}s, publish={publish_time:.4f}s, wait={self.config.timeout:.4f}s")
                self.logger.error(f"🔍 [ZMQ_DEBUG] ❌ TIMEOUT after {total_time:.4f}s waiting for response")
                self.logger.error(f"🔍 [ZMQ_DEBUG] Performance breakdown: connection={connection_time:.4f}s, subscription={subscription_time:.4f}s, publish={publish_time:.4f}s, wait={self.config.timeout:.4f}s")
            elif is_chat_request:
                self.logger.error(f"💬 [CHAT_DEBUG] ❌ TIMEOUT after {total_time:.4f}s waiting for response")
                self.logger.error(f"💬 [CHAT_DEBUG] Performance breakdown: connection={connection_time:.4f}s, subscription={subscription_time:.4f}s, publish={publish_time:.4f}s, wait={self.config.timeout:.4f}s")
                self.logger.error(f"💬 [CHAT_DEBUG] Model requested: {data.get('model', 'unknown')}. Check if this model is available in Ollama.")
            
            self.logger.error(f"⚠️ {error_msg}", extra={"topic": AICOTopics.LOGS_ENTRY})
            print(f"⚠️ {error_msg}")
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"ZMQ request failed: {str(e)}"
            
            if is_embedding_request:
                import traceback
                self.logger.error(f"🔍 [ZMQ_DEBUG] ❌ Exception after {total_time:.4f}s: {e}")
                self.logger.error(f"🔍 [ZMQ_DEBUG] Traceback: {traceback.format_exc()}")
            elif is_chat_request:
                import traceback
                self.logger.error(f"💬 [CHAT_DEBUG] ❌ Exception after {total_time:.4f}s: {e}")
                self.logger.error(f"💬 [CHAT_DEBUG] Traceback: {traceback.format_exc()}")
            
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
        import time
        start_time = time.time()
        text_length = len(prompt)
        text_preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
        
        # Reduced debug noise - only log if text is long or if there are issues
        if text_length > 500:
            print(f"⏱️ [MODELSERVICE_TIMING] Large embedding request: {text_length} chars")
        self.logger.debug(f"🔍 [EMBEDDING_CLIENT_DEBUG] Starting embedding request for model={model}, text_length={text_length}")
        self.logger.debug(f"🔍 [EMBEDDING_CLIENT_DEBUG] Text preview: '{text_preview}'")
        
        request_data = {
            "model": model,
            "prompt": prompt
        }
        
        try:
            send_request_start = time.time()
            # Removed debug noise
            
            result = await self._send_request(
                AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
                AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
                request_data
            )
            
            send_request_time = time.time() - send_request_start
            elapsed_time = time.time() - start_time
            # Only log slow embeddings
            if elapsed_time > 0.5:
                print(f"⏱️ [MODELSERVICE_TIMING] SLOW embedding: {elapsed_time:.2f}s for {text_length} chars")
            
            if result.get("success"):
                embedding_dim = len(result.get("data", {}).get("embedding", []))
                # Reduced success noise
                self.logger.debug(f"🔍 [EMBEDDING_CLIENT_DEBUG] ✅ Success! Got {embedding_dim}-dimensional embedding in {elapsed_time:.2f}s")
            else:
                print(f"⏱️ [MODELSERVICE_TIMING] ❌ FAILED! Error: {result.get('error')}")
                self.logger.error(f"🔍 [EMBEDDING_CLIENT_DEBUG] ❌ Failed to get embedding: {result.get('error')}")
            
            return result
        except Exception as e:
            import traceback
            elapsed_time = time.time() - start_time
            self.logger.error(f"🔍 [EMBEDDING_CLIENT_DEBUG] ❌ Exception after {elapsed_time:.2f}s: {e}")
            self.logger.error(f"🔍 [EMBEDDING_CLIENT_DEBUG] Traceback: {traceback.format_exc()}")
            raise
    
    async def get_embeddings_batch(self, model: str, prompts: List[str]) -> Dict[str, Any]:
        """EMERGENCY FIX: Skip batch processing - just do individual requests quickly."""
        import time
        start_time = time.time()
        
        try:
            self.logger.warning(f"🚨 [BATCH_EMBEDDING_CLIENT] EMERGENCY MODE: Processing {len(prompts)} embeddings individually (batch disabled due to 30s delays)")
            
            # EMERGENCY: Just do individual requests sequentially to avoid timeout issues
            embeddings = []
            failed_count = 0
            
            for i, prompt in enumerate(prompts):
                try:
                    single_start = time.time()
                    result = await self.get_embeddings(model=model, prompt=prompt)
                    single_time = time.time() - single_start
                    
                    if result.get("success") and "embedding" in result.get("data", {}):
                        embeddings.append(result["data"]["embedding"])
                        if single_time > 3.0:
                            self.logger.warning(f"🚨 [BATCH_EMBEDDING_CLIENT] SLOW individual embedding {i+1}/{len(prompts)}: {single_time:.2f}s")
                    else:
                        embeddings.append(None)
                        failed_count += 1
                        self.logger.error(f"🚨 [BATCH_EMBEDDING_CLIENT] Failed embedding {i+1}/{len(prompts)}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    embeddings.append(None)
                    failed_count += 1
                    self.logger.error(f"🚨 [BATCH_EMBEDDING_CLIENT] Exception on embedding {i+1}/{len(prompts)}: {e}")
            
            elapsed_time = time.time() - start_time
            successful_count = len([e for e in embeddings if e is not None])
            
            self.logger.info(f"🚨 [BATCH_EMBEDDING_CLIENT] EMERGENCY COMPLETE: {successful_count}/{len(prompts)} embeddings in {elapsed_time:.2f}s")
            
            if elapsed_time > 10.0:
                self.logger.error(f"🚨 [BATCH_EMBEDDING_CLIENT] ❌ STILL TOO SLOW: {elapsed_time:.2f}s for {len(prompts)} embeddings")
            
            return {
                "success": True,
                "data": {
                    "embeddings": embeddings,
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "processing_time": elapsed_time
                }
            }
        except Exception as e:
            import traceback
            elapsed_time = time.time() - start_time
            self.logger.error(f"🚀 [BATCH_EMBEDDING_CLIENT] ❌ Exception after {elapsed_time:.2f}s: {e}")
            self.logger.error(f"🚀 [BATCH_EMBEDDING_CLIENT] Traceback: {traceback.format_exc()}")
            raise
    
    def _log_batch_performance(self, metrics: Dict[str, Any], total_time: float, 
                              successful_count: int, failed_count: int, method: str) -> None:
        """PERFORMANCE MONITORING: Log detailed batch processing metrics."""
        batch_size = metrics["batch_size"]
        individual_times = metrics.get("individual_times", [])
        
        # Calculate performance statistics
        avg_time_per_embedding = total_time / batch_size if batch_size > 0 else 0
        success_rate = (successful_count / batch_size * 100) if batch_size > 0 else 0
        
        # Individual timing statistics (for concurrent mode)
        if individual_times:
            avg_individual_time = sum(individual_times) / len(individual_times)
            min_time = min(individual_times)
            max_time = max(individual_times)
            
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Method: {method}")
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Batch: {batch_size} items, {successful_count} success, {failed_count} failed ({success_rate:.1f}% success)")
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Total: {total_time:.2f}s, Avg per item: {avg_time_per_embedding:.3f}s")
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Individual times: avg={avg_individual_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")
            
            # Performance thresholds and warnings
            if avg_time_per_embedding > 2.0:
                self.logger.warning(f"📊 [BATCH_PERFORMANCE] ⚠️ SLOW BATCH: {avg_time_per_embedding:.3f}s per embedding (threshold: 2.0s)")
            
            if success_rate < 90:
                self.logger.warning(f"📊 [BATCH_PERFORMANCE] ⚠️ LOW SUCCESS RATE: {success_rate:.1f}% (threshold: 90%)")
                
        else:
            # True batch mode statistics
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Method: {method}")
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Batch: {batch_size} items, {successful_count} success, {failed_count} failed ({success_rate:.1f}% success)")
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Total: {total_time:.2f}s, Avg per item: {avg_time_per_embedding:.3f}s")
            
            # Performance comparison
            estimated_individual_time = batch_size * 2.0  # Assume 2s per individual request
            speedup = estimated_individual_time / total_time if total_time > 0 else 1
            self.logger.info(f"📊 [BATCH_PERFORMANCE] Estimated speedup: {speedup:.1f}x vs individual requests")
    
    async def get_ner_entities(self, text: str, entity_types: List[str] = None) -> Dict[str, Any]:
        """Get named entity recognition from modelservice with optional entity type filtering."""
        request_data = {
            "text": text
        }
        
        # ROOT FIX: Pass specific entity types to GLiNER for focused extraction
        if entity_types:
            request_data["entity_types"] = entity_types
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_NER_REQUEST,
            AICOTopics.MODELSERVICE_NER_RESPONSE,
            request_data
        )
    
    async def get_ner_entities_optimized(self, ner_request: Dict[str, Any]) -> Dict[str, Any]:
        """REPURPOSED: Use existing NER endpoint with optimized parameters."""
        self.logger.info(f"🔍 [GLINER_OPTIMIZED] Using existing NER endpoint with model: {ner_request.get('model_name', 'default')}")
        
        # REPURPOSE: Enhance existing NER request with optimization parameters
        request_data = {
            "text": ner_request.get("text", ""),
            "entity_types": ner_request.get("entity_types", []),
            # Add optimization parameters to existing endpoint
            "threshold": ner_request.get("threshold", 0.35),
            "model_name": ner_request.get("model_name", "urchade/gliner_multi-v2.1"),
            "max_length": ner_request.get("max_length", 512),
            "optimization_mode": True  # Signal to modelservice for optimized processing
        }
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_NER_REQUEST,
            AICOTopics.MODELSERVICE_NER_RESPONSE,
            request_data
        )
    
    async def classify_intent(self, text: str, user_id: Optional[str] = None, conversation_context: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get intent classification from modelservice using advanced AI processor."""
        request_data = {
            "text": text
        }
        
        if user_id:
            request_data["user_id"] = user_id
        
        if conversation_context:
            request_data["conversation_context"] = conversation_context
        
        return await self._send_request(
            AICOTopics.MODELSERVICE_INTENT_REQUEST,
            AICOTopics.MODELSERVICE_INTENT_RESPONSE,
            request_data
        )
    
    async def get_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Get sentiment analysis from modelservice."""
        request_data = {
            "text": text
        }
        
        self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] Sending sentiment request for text: '{text[:50]}...'")
        self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] Request data: {request_data}")
        
        result = await self._send_request(
            AICOTopics.MODELSERVICE_SENTIMENT_REQUEST,
            AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE,
            request_data
        )
        
        self.logger.info(f"🔍 [SENTIMENT_CLIENT_DEBUG] Response received: {result}")
        return result
    
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
    """Get singleton modelservice client instance.
    
    This function returns a client that can communicate with the modelservice,
    but does not guarantee that the modelservice is actually running.
    Use client.check_modelservice_health() to verify the service is available.
    """
    global _modelservice_client
    
    if _modelservice_client is None:
        _modelservice_client = ModelServiceClient(config_manager)
        logger = get_logger("backend", "services.modelservice_client")
        logger.info("Created modelservice client - Note: this does not guarantee the modelservice is running")
        print("[i] Created modelservice client - use check_modelservice_health() to verify service availability")
    
    return _modelservice_client
