"""
ZeroMQ message handlers for modelservice - pure Protocol Buffer implementation.

This module implements ZMQ request/response handlers that work directly with
Protocol Buffer messages, providing type-safe message handling.
"""

import asyncio
import time
import httpx
from datetime import datetime
from typing import Optional, Dict, Any

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.core.version import get_modelservice_version
from aico.proto.aico_modelservice_pb2 import (
    HealthResponse, CompletionsResponse, ModelsResponse, ModelInfoResponse,
    EmbeddingsResponse, StatusResponse, ModelInfo, ServiceStatus, OllamaStatus
)
from google.protobuf.timestamp_pb2 import Timestamp

logger = get_logger("modelservice", "zmq_handlers")


class ModelserviceZMQHandlers:
    """ZeroMQ message handlers for modelservice functionality."""
    
    def __init__(self, config: dict, ollama_manager):
        self.config = config
        self.ollama_manager = ollama_manager
        self.version = get_modelservice_version()
        
    async def handle_health_request(self, request_payload) -> HealthResponse:
        """Handle health check requests via Protocol Buffers."""
        response = HealthResponse()
        
        try:
            # Perform comprehensive health check
            health_data = await self._check_system_health()
            
            response.success = True
            response.status = health_data["status"]
            
            logger.info(
                f"Health check completed: {health_data['status']}",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
            
        except Exception as e:
            response.success = False
            response.status = "error"
            response.error = f"Health check failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_completions_request(self, request_payload) -> CompletionsResponse:
        """Handle completion requests via Protocol Buffers."""
        response = CompletionsResponse()
        
        try:
            # Extract data from Protocol Buffer request
            model = request_payload.model
            messages = request_payload.messages
            
            if not model or not messages:
                response.success = False
                response.error = "Model and messages are required"
                return response
            
            # Convert messages to prompt (simple implementation)
            prompt_parts = []
            for msg in messages:
                prompt_parts.append(f"{msg.role}: {msg.content}")
            prompt = "\n".join(prompt_parts)
            
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                if ollama_response.status_code != 200:
                    raise Exception(f"Ollama error: {ollama_response.status_code} - {ollama_response.text}")
                
                data = ollama_response.json()
                
                # Create Protocol Buffer response
                from aico.proto.aico_modelservice_pb2 import CompletionResult, ChatMessage
                result = CompletionResult()
                result.model = model
                result.done = data.get("done", True)
                
                # Create response message
                response_msg = ChatMessage()
                response_msg.role = "assistant"
                response_msg.content = data.get("response", "")
                result.message.CopyFrom(response_msg)
                
                # Optional timing fields
                if "total_duration" in data:
                    result.total_duration = data["total_duration"]
                if "load_duration" in data:
                    result.load_duration = data["load_duration"]
                if "prompt_eval_count" in data:
                    result.prompt_eval_count = data["prompt_eval_count"]
                if "prompt_eval_duration" in data:
                    result.prompt_eval_duration = data["prompt_eval_duration"]
                if "eval_count" in data:
                    result.eval_count = data["eval_count"]
                if "eval_duration" in data:
                    result.eval_duration = data["eval_duration"]
                
                response.success = True
                response.result.CopyFrom(result)
                
                logger.info(
                    f"Completion generated for model {model}",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
        except Exception as e:
            response.success = False
            response.error = f"Completion failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_models_request(self, request_payload) -> ModelsResponse:
        """Handle models list requests via Protocol Buffers."""
        response = ModelsResponse()
        
        try:
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                ollama_response = await client.get(f"{ollama_url}/api/tags")
                
                if ollama_response.status_code != 200:
                    raise Exception(f"Ollama error: {ollama_response.status_code} - {ollama_response.text}")
                
                ollama_data = ollama_response.json()
                
                for model_data in ollama_data.get("models", []):
                    model_info = ModelInfo()
                    model_info.name = model_data["name"]
                    model_info.model = model_data["name"]
                    model_info.size = model_data.get("size", 0)
                    model_info.digest = model_data.get("digest", "")
                    
                    # Convert timestamp if present
                    if "modified_at" in model_data:
                        try:
                            dt = datetime.fromisoformat(model_data["modified_at"].replace('Z', '+00:00'))
                            model_info.modified_at.FromDatetime(dt)
                        except:
                            pass
                    
                    response.models.append(model_info)
                
                response.success = True
                
                logger.info(
                    f"Retrieved {len(response.models)} models from Ollama",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
        except Exception as e:
            response.success = False
            response.error = f"Models request failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
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
            
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                ollama_response = await client.post(
                    f"{ollama_url}/api/show",
                    json={"name": model_name}
                )
                
                if ollama_response.status_code != 200:
                    raise Exception(f"Ollama error: {ollama_response.status_code} - {ollama_response.text}")
                
                ollama_data = ollama_response.json()
                
                from aico.proto.aico_modelservice_pb2 import ModelDetails
                details = ModelDetails()
                details.format = ollama_data.get("format", "")
                details.family = ollama_data.get("family", "")
                details.parameter_size = ollama_data.get("parameter_size", 0)
                details.quantization_level = ollama_data.get("quantization_level", 0)
                
                response.success = True
                response.details.CopyFrom(details)
                
                logger.info(
                    f"Retrieved info for model {model_name}",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
        except Exception as e:
            response.success = False
            response.error = f"Model info request failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_embeddings_request(self, request_payload) -> EmbeddingsResponse:
        """Handle embeddings requests via Protocol Buffers."""
        response = EmbeddingsResponse()
        
        try:
            model = request_payload.model
            prompt = request_payload.prompt
            
            if not model or not prompt:
                response.success = False
                response.error = "model and prompt are required"
                return response
            
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": prompt
                    }
                )
                
                if ollama_response.status_code != 200:
                    raise Exception(f"Ollama error: {ollama_response.status_code} - {ollama_response.text}")
                
                ollama_data = ollama_response.json()
                
                # Add embeddings to response
                if "embedding" in ollama_data:
                    response.embedding.extend(ollama_data["embedding"])
                
                response.success = True
                
                logger.info(
                    f"Generated embeddings for model {model}",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
        except Exception as e:
            response.success = False
            response.error = f"Embeddings request failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def handle_status_request(self, request_payload) -> StatusResponse:
        """Handle status requests via Protocol Buffers."""
        response = StatusResponse()
        
        try:
            # Create service status
            status = ServiceStatus()
            status.version = self.version
            status.ollama_running = True  # Will be updated by health check
            status.ollama_version = "unknown"
            status.loaded_models_count = 0
            
            # Check Ollama status
            ollama_status = await self._check_ollama_status()
            if ollama_status.get("available", False):
                status.ollama_running = True
                # Get models count
                try:
                    models_response = await self.handle_models_request(None)
                    if models_response.success:
                        status.loaded_models_count = len(models_response.models)
                        for model in models_response.models:
                            status.loaded_models.append(model.name)
                except:
                    pass
            else:
                status.ollama_running = False
            
            response.success = True
            response.status.CopyFrom(status)
            
            logger.info(
                "Status request completed",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
            
        except Exception as e:
            response.success = False
            response.error = f"Status request failed: {str(e)}"
            logger.error(response.error, extra={"topic": AICOTopics.LOGS_ENTRY})
        
        return response
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        health_data = {
            "status": "healthy",
            "checks": {},
            "issues": []
        }
        
        try:
            # Check Ollama connectivity
            ollama_status = await self._check_ollama_status()
            health_data["checks"]["ollama"] = ollama_status
            
            if not ollama_status.get("available", False):
                health_data["status"] = "degraded"
                health_data["issues"].append("Ollama service unavailable")
            
            # Check API Gateway connectivity (optional)
            try:
                gateway_status = await self._check_gateway_status()
                health_data["checks"]["api_gateway"] = gateway_status
            except Exception as e:
                health_data["checks"]["api_gateway"] = {
                    "available": False,
                    "error": str(e)
                }
                # Gateway connectivity is not critical for modelservice
            
        except Exception as e:
            health_data["status"] = "unhealthy"
            health_data["issues"].append(f"Health check error: {str(e)}")
        
        return health_data
    
    async def _check_ollama_status(self) -> Dict[str, Any]:
        """Check Ollama service status."""
        try:
            ollama_url = f"http://{self.config['ollama']['host']}:{self.config['ollama']['port']}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = time.time()
                response = await client.get(f"{ollama_url}/api/tags")
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "available": response.status_code == 200,
                    "response_time_ms": round(response_time),
                    "url": ollama_url
                }
                
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "url": f"http://{self.config['ollama']['host']}:{self.config['ollama']['port']}"
            }
    
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
