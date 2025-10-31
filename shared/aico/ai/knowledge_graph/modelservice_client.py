"""
Modelservice Client for Knowledge Graph

ZeroMQ client for calling modelservice APIs (GLiNER, embeddings, LLM).
Follows AICO's message bus patterns.
"""

import asyncio
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.core.logging import get_logger
from aico.proto.aico_modelservice_pb2 import (
    NerRequest, NerResponse,
    EmbeddingsRequest, EmbeddingsResponse,
    CompletionsRequest, CompletionsResponse
)

logger = get_logger("shared", "ai.knowledge_graph.modelservice_client")

def _ts():
    """Get timestamp for debug prints."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class ModelserviceClient:
    """
    ZeroMQ client for modelservice API calls.
    
    Provides async methods for:
    - Entity extraction (GLiNER)
    - Embedding generation
    - LLM completions (Eve)
    """
    
    def __init__(self):
        """Initialize modelservice client."""
        self.bus_client: Optional[MessageBusClient] = None
        self._connected = False
        self._pending_requests: Dict[str, asyncio.Future] = {}
    
    async def connect(self, timeout: float = 5.0) -> None:
        """Connect to message bus."""
        if self._connected:
            logger.info("🔍 [KG CLIENT] Already connected, skipping")
            return
        
        try:
            logger.info("🔍 [KG CLIENT] Creating MessageBusClient with ID: kg_modelservice_client")
            self.bus_client = MessageBusClient("kg_modelservice_client")
            
            # Connect with timeout
            logger.info("🔍 [KG CLIENT] Connecting to message bus...")
            await asyncio.wait_for(self.bus_client.connect(), timeout=timeout)
            logger.info("🔍 [KG CLIENT] Message bus connection successful")
            
            # Subscribe to response topics
            logger.info(f"🔍 [KG CLIENT] Subscribing to {AICOTopics.MODELSERVICE_NER_RESPONSE}")
            await self.bus_client.subscribe(
                AICOTopics.MODELSERVICE_NER_RESPONSE,
                self._handle_ner_response
            )
            logger.info(f"🔍 [KG CLIENT] Subscribing to {AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE}")
            await self.bus_client.subscribe(
                AICOTopics.MODELSERVICE_EMBEDDINGS_RESPONSE,
                self._handle_embeddings_response
            )
            logger.info(f"🔍 [KG CLIENT] Subscribing to {AICOTopics.MODELSERVICE_CHAT_RESPONSE}")
            await self.bus_client.subscribe(
                AICOTopics.MODELSERVICE_CHAT_RESPONSE,
                self._handle_completions_response
            )
            
            self._connected = True
            logger.info("🔍 [KG CLIENT] Modelservice client fully connected and subscribed")
            
        except asyncio.TimeoutError:
            logger.error(f"Failed to connect to message bus: timeout after {timeout}s")
            raise RuntimeError("Message bus connection timeout - is the backend running?")
        except Exception as e:
            logger.error(f"Failed to connect modelservice client: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from message bus."""
        if self.bus_client:
            await self.bus_client.disconnect()
            self._connected = False
            logger.info("Modelservice client disconnected")
    
    async def extract_entities(
        self,
        text: str,
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        Extract entities using GLiNER.
        
        Args:
            text: Text to extract entities from
            labels: Entity types to extract (e.g., ["person", "organization"])
            
        Returns:
            Dict with "entities" list containing extracted entities
        """
        if not self._connected:
            await self.connect()
        
        request_id = str(uuid.uuid4())
        logger.info(f"🔍 [KG CLIENT] Generated request_id: {request_id}")
        
        # Create NER request
        ner_request = NerRequest()
        ner_request.text = text
        # Note: GLiNER handler uses hardcoded labels, but we send them anyway
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # Publish request
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_NER_REQUEST,
                ner_request,
                correlation_id=request_id
            )
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            
            if not response.get("success", False):
                logger.error(f"NER request failed: {response.get('error', 'Unknown error')}")
                return {"entities": {}}
            
            # Entities are already converted to dicts in _handle_ner_response
            # Response format: {"entities": {"PERSON": [...], "ORGANIZATION": [...]}}
            entities_by_type = response.get("entities", {})
            total_entities = sum(len(entity_list) for entity_list in entities_by_type.values())
            logger.debug(f"Extracted {total_entities} entities across {len(entities_by_type)} types")
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"NER request timed out after 30s for request_id: {request_id}")
            # Don't remove from pending - response might still arrive
            return {"entities": []}
    
    async def generate_embeddings(
        self,
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Dict with "embeddings" list (one per text)
        """
        if not self._connected:
            await self.connect()
        
        # Generate embeddings one at a time (modelservice expects single text)
        embeddings = []
        
        for text in texts:
            request_id = str(uuid.uuid4())
            
            # Create embeddings request
            embeddings_request = EmbeddingsRequest()
            embeddings_request.model = "paraphrase-multilingual"
            embeddings_request.prompt = text
            
            # Create future for response
            future = asyncio.Future()
            self._pending_requests[request_id] = future
            
            try:
                # Publish request
                await self.bus_client.publish(
                    AICOTopics.MODELSERVICE_EMBEDDINGS_REQUEST,
                    embeddings_request,
                    correlation_id=request_id
                )
                
                # Wait for response with timeout
                response = await asyncio.wait_for(future, timeout=30.0)
                
                if not response.get("success", False):
                    logger.error(f"Embeddings request failed: {response.get('error', 'Unknown error')}")
                    embeddings.append([0.0] * 768)  # Dummy embedding
                else:
                    embeddings.append(list(response.get("embedding", [])))
                
            except asyncio.TimeoutError:
                logger.error(f"Embeddings request timed out after 30s for request_id: {request_id}")
                # Don't remove from pending - response might still arrive
                embeddings.append([0.0] * 768)  # Dummy embedding
        
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return {"embeddings": embeddings}
    
    async def generate_completion(
        self,
        prompt: str,
        model: str = "eve",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generate LLM completion.
        
        Args:
            prompt: Prompt text
            model: Model name (default: "eve" = qwen3-abliterated)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with "text" containing generated completion
        """
        if not self._connected:
            await self.connect()
        
        request_id = str(uuid.uuid4())
        
        # Create completions request
        from aico.proto.aico_modelservice_pb2 import ConversationMessage
        
        completions_request = CompletionsRequest()
        # Map "eve" to actual model name from config
        if model == "eve":
            completions_request.model = "huihui_ai/qwen3-abliterated:8b-v2"
        else:
            completions_request.model = model
        
        
        # Add prompt as user message
        msg = completions_request.messages.add()
        msg.role = "user"
        msg.content = prompt
        
        # Set parameters
        completions_request.temperature = temperature
        completions_request.max_tokens = max_tokens
        completions_request.stream = False  # Non-streaming for KG
        
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # Publish request
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_CHAT_REQUEST,
                completions_request,
                correlation_id=request_id
            )
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=60.0)
            
            if not response.get("success", False):
                logger.error(f"Completions request failed: {response.get('error', 'Unknown error')}")
                return {"text": ""}
            
            text = response.get("content", "")
            logger.debug(f"Generated completion: {len(text)} chars")
            return {"text": text}
            
        except asyncio.TimeoutError:
            logger.error(f"Completions request timed out after 60s for request_id: {request_id}")
            # Don't remove from pending - response might still arrive
            return {"text": ""}
    
    async def _handle_ner_response(self, envelope) -> None:
        """Handle NER response from modelservice."""
        try:
            logger.info(f"🔍 [KG CLIENT] Received NER response")
            
            # Extract correlation ID from attributes map
            try:
                correlation_id = envelope.metadata.attributes.get("correlation_id", "")
                if not correlation_id:
                    logger.error(f"KG Client: No correlation_id in attributes: {dict(envelope.metadata.attributes)}")
                    return
            except Exception as e:
                raise
            
            
            if correlation_id not in self._pending_requests:
                logger.warning(f"🔍 [KG CLIENT] No pending request for correlation_id: {correlation_id}")
                return
            
            # Unpack NER response
            ner_response = NerResponse()
            envelope.any_payload.Unpack(ner_response)
            
            # Convert to dict
            result = {
                "success": ner_response.success,
                "error": ner_response.error if ner_response.error else None,
                "entities": {}
            }
            
            # Convert protobuf entities to dict
            for entity_type, entity_list in ner_response.entities.items():
                result["entities"][entity_type] = [
                    {
                        "text": entity.text,
                        "label": entity_type,  # Use the map key as the label
                        "confidence": entity.confidence,
                        "start_pos": 0,  # Not in protobuf
                        "end_pos": 0     # Not in protobuf
                    }
                    for entity in entity_list.entities
                ]
            
            # Resolve future
            future = self._pending_requests.get(correlation_id)
            if future and not future.done():
                future.set_result(result)
                # Clean up after successful resolution
                self._pending_requests.pop(correlation_id, None)
            else:
                logger.warning(f"KG Client: Future not found or already done: {future}")
                
        except Exception as e:
            logger.error(f"KG Client exception in handler: {e}")
            logger.error(f"Error handling NER response: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_embeddings_response(self, envelope) -> None:
        """Handle embeddings response from modelservice."""
        try:
            # Extract correlation ID from attributes map
            correlation_id = envelope.metadata.attributes.get("correlation_id", "")
            
            if not correlation_id or correlation_id not in self._pending_requests:
                return
            
            # Unpack embeddings response
            embeddings_response = EmbeddingsResponse()
            envelope.any_payload.Unpack(embeddings_response)
            
            # Convert to dict
            result = {
                "success": embeddings_response.success,
                "error": embeddings_response.error if embeddings_response.error else None,
                "embedding": list(embeddings_response.embedding)
            }
            
            # Resolve future
            future = self._pending_requests.get(correlation_id)
            if future and not future.done():
                future.set_result(result)
                # Clean up after successful resolution
                self._pending_requests.pop(correlation_id, None)
                
        except Exception as e:
            logger.error(f"Error handling embeddings response: {e}")
    
    async def _handle_completions_response(self, envelope) -> None:
        """Handle completions response from modelservice."""
        try:
            # Extract correlation ID from attributes map
            correlation_id = envelope.metadata.attributes.get("correlation_id", "")
            
            if not correlation_id or correlation_id not in self._pending_requests:
                return
            
            # Unpack completions response
            completions_response = CompletionsResponse()
            envelope.any_payload.Unpack(completions_response)
            
            # Convert to dict
            content = ""
            if completions_response.success and completions_response.HasField("result"):
                content = completions_response.result.message.content
            
            result = {
                "success": completions_response.success,
                "error": completions_response.error if completions_response.error else None,
                "content": content
            }
            
            # Resolve future
            future = self._pending_requests.get(correlation_id)
            if future and not future.done():
                future.set_result(result)
                # Clean up after successful resolution
                self._pending_requests.pop(correlation_id, None)
            else:
                logger.warning(f"KG Client LLM: Future not found or already done: {future}")
                
        except Exception as e:
            logger.error(f"KG Client LLM exception in handler: {e}")
            logger.error(f"Error handling completions response: {e}")
            import traceback
            traceback.print_exc()
