"""
ZeroMQ message handlers for modelservice - pure Protocol Buffer implementation.

This module implements ZMQ request/response handlers that work directly with
Protocol Buffer messages, providing type-safe message handling.
"""

import asyncio
import time
import httpx
from datetime import datetime
from typing import Optional

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
    
    async def handle_models_request(self, request_data: dict) -> dict:
        """Handle models list requests via ZMQ."""
        try:
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                
                if response.status_code != 200:
                    raise Exception(f"Ollama error: {response.status_code} - {response.text}")
                
                ollama_data = response.json()
                models = []
                
                for model_data in ollama_data.get("models", []):
                    model_info = {
                        "name": model_data["name"],
                        "size": model_data.get("size", 0),
                        "digest": model_data.get("digest", ""),
                        "modified_at": model_data.get("modified_at", ""),
                        "status": "available",
                        "type": "llm"
                    }
                    models.append(model_info)
                
                models_response = {"models": models}
                
                logger.info(
                    f"Retrieved {len(models)} models from Ollama",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
                return {"success": True, "data": models_response}
                
        except Exception as e:
            error_msg = f"Models request failed: {str(e)}"
            logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
    
    async def handle_model_info_request(self, request_data: dict) -> dict:
        """Handle model info requests via ZMQ."""
        try:
            model_name = request_data.get("model_name")
            if not model_name:
                raise ValueError("model_name is required")
            
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/show",
                    json={"name": model_name}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama error: {response.status_code} - {response.text}")
                
                ollama_data = response.json()
                
                model_info = {
                    "name": model_name,
                    "size": ollama_data.get("size", 0),
                    "digest": ollama_data.get("digest", ""),
                    "modified_at": ollama_data.get("modified_at", ""),
                    "status": "available",
                    "type": "llm",
                    "parameters": ollama_data.get("parameters", {}),
                    "template": ollama_data.get("template", ""),
                    "system": ollama_data.get("system", "")
                }
                
                logger.info(
                    f"Retrieved info for model {model_name}",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
                return {"success": True, "data": model_info}
                
        except Exception as e:
            error_msg = f"Model info request failed: {str(e)}"
            logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
    
    async def handle_embeddings_request(self, request_data: dict) -> dict:
        """Handle embeddings requests via ZMQ."""
        try:
            model = request_data.get("model")
            prompt = request_data.get("prompt")
            
            if not model or not prompt:
                raise ValueError("model and prompt are required")
            
            # Forward to Ollama
            ollama_url = f"http://{self.config.get('ollama', {}).get('host', 'localhost')}:{self.config.get('ollama', {}).get('port', 11434)}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": prompt
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama error: {response.status_code} - {response.text}")
                
                ollama_data = response.json()
                
                logger.info(
                    f"Generated embeddings for model {model}",
                    extra={"topic": AICOTopics.LOGS_ENTRY}
                )
                
                return {"success": True, "data": ollama_data}
                
        except Exception as e:
            error_msg = f"Embeddings request failed: {str(e)}"
            logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
    
    async def handle_status_request(self, request_data: dict) -> dict:
        """Handle status requests via ZMQ."""
        try:
            # Get comprehensive status information
            status_data = {
                "service": "modelservice",
                "version": self.version,
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "ollama_status": await self._check_ollama_status(),
                "uptime": time.time() - getattr(self, '_start_time', time.time())
            }
            
            logger.info(
                "Status request completed",
                extra={"topic": AICOTopics.LOGS_ENTRY}
            )
            
            return {"success": True, "data": status_data}
            
        except Exception as e:
            error_msg = f"Status request failed: {str(e)}"
            logger.error(error_msg, extra={"topic": AICOTopics.LOGS_ENTRY})
            return {"success": False, "error": error_msg}
    
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
    
    async def _check_gateway_status(self) -> Dict[str, Any]:
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
