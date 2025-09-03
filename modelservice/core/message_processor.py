"""
Message Processing Core

Handles the complex logic for processing user messages through the AI pipeline.
This module centralizes all completion-related processing logic.
"""

import time
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from ..api.schemas import CompletionRequest, CompletionResponse, UsageStats
from .ollama_manager import OllamaManager
from shared.aico.core.config import ConfigurationManager


@dataclass
class ProcessingContext:
    """Context for message processing."""
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class MessageProcessor:
    """Handles complex message processing logic."""
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        # Initialize configuration
        self.config_manager = config_manager or ConfigurationManager()
        if not hasattr(self.config_manager, 'config_cache') or not self.config_manager.config_cache:
            self.config_manager.initialize()
        
        # Get Ollama configuration
        self.ollama_config = self.config_manager.get("core.modelservice.ollama", {})
        
        # Build Ollama URL from config
        ollama_host = self.ollama_config.get("host", "127.0.0.1")
        ollama_port = self.ollama_config.get("port", 11434)
        self.ollama_url = f"http://{ollama_host}:{ollama_port}"
        
        # Initialize logger first
        try:
            from shared.aico.core.logging import get_logger
            self.logger = get_logger("modelservice", "message_processor")
        except RuntimeError:
            # Logging not initialized yet, use basic Python logger as fallback
            import logging
            self.logger = logging.getLogger("message_processor")
            self.logger.setLevel(logging.INFO)
        
        self.ollama_manager = OllamaManager()
        # Ensure ollama_manager has logger initialized
        if not hasattr(self.ollama_manager, 'logger') or self.ollama_manager.logger is None:
            self.ollama_manager._ensure_logger()
        
    async def process_completion(
        self, 
        request: CompletionRequest,
        context: Optional[ProcessingContext] = None
    ) -> CompletionResponse:
        """
        Process a completion request through the full AI pipeline.
        
        Args:
            request: The completion request
            context: Optional processing context
            
        Returns:
            CompletionResponse with the generated completion
        """
        try:
            self.logger.info(f"[DEBUG] Starting completion processing for model: {request.model}")
            
            # Step 1: Validate and preprocess request
            self.logger.info("[DEBUG] Step 1: Validating request")
            await self._validate_request(request)
            processed_prompt = await self._preprocess_prompt(request.prompt, context)
            
            # Step 2: Ensure model is available and running
            self.logger.info("[DEBUG] Step 2: Ensuring model ready")
            await self._ensure_model_ready(request.model)
            
            # Step 3: Generate completion via Ollama
            self.logger.info("[DEBUG] Step 3: Generating completion")
            ollama_response = await self._generate_completion(request, processed_prompt)
            
            # Step 4: Postprocess and format response
            self.logger.info("[DEBUG] Step 4: Postprocessing response")
            completion_response = await self._postprocess_response(
                ollama_response, request, context
            )
            
            self.logger.info("[DEBUG] Completion processing completed successfully")
            return completion_response
            
        except Exception as e:
            self.logger.error(f"Error in completion processing: {e}")
            raise
    
    async def _validate_request(self, request: CompletionRequest) -> None:
        """Validate the incoming completion request."""
        if not request.prompt or not request.prompt.strip():
            raise ValueError("Prompt cannot be empty")
            
        if not request.model:
            raise ValueError("Model must be specified")
            
        # Validate parameters if present
        if request.parameters:
            params = request.parameters
            if params.max_tokens is not None and params.max_tokens <= 0:
                raise ValueError("max_tokens must be positive")
            if params.temperature is not None and not (0.0 <= params.temperature <= 2.0):
                raise ValueError("temperature must be between 0.0 and 2.0")
    
    async def _preprocess_prompt(
        self, 
        prompt: str, 
        context: Optional[ProcessingContext] = None
    ) -> str:
        """
        Preprocess the prompt before sending to the model.
        
        This is where we can add:
        - Prompt templates
        - Context injection
        - Safety filtering
        - Conversation history
        """
        # For now, return prompt as-is
        # TODO: Add prompt templates, context injection, etc.
        return prompt.strip()
    
    async def _ensure_model_ready(self, model_name: str) -> None:
        """Ensure the specified model is loaded and ready."""
        try:
            # Check if model is already running
            if not await self.ollama_manager._is_model_running(model_name):
                # Start the model if not running
                success = await self.ollama_manager.start_model(model_name)
                if not success:
                    raise RuntimeError(f"Failed to start model: {model_name}")
        except Exception as e:
            self.logger.error(f"Error ensuring model ready: {e}")
            raise RuntimeError(f"Model readiness check failed: {e}")
    
    async def _generate_completion(
        self, 
        request: CompletionRequest, 
        processed_prompt: str
    ) -> Dict[str, Any]:
        """Generate completion using Ollama."""
        # Prepare Ollama request payload
        ollama_payload = {
            "model": request.model,
            "prompt": processed_prompt,
            "stream": False,
            "options": {}
        }
        
        # Map parameters to Ollama options
        if request.parameters:
            params = request.parameters
            if params.max_tokens is not None:
                ollama_payload["options"]["num_predict"] = params.max_tokens
            if params.temperature is not None:
                ollama_payload["options"]["temperature"] = params.temperature
            if params.top_p is not None:
                ollama_payload["options"]["top_p"] = params.top_p
            if params.top_k is not None:
                ollama_payload["options"]["top_k"] = params.top_k
            if params.repeat_penalty is not None:
                ollama_payload["options"]["repeat_penalty"] = params.repeat_penalty
            if params.stop is not None:
                ollama_payload["options"]["stop"] = params.stop
        
        # Send request to Ollama
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_payload
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")
                
            return response.json()
    
    async def _postprocess_response(
        self,
        ollama_response: Dict[str, Any],
        original_request: CompletionRequest,
        context: Optional[ProcessingContext] = None
    ) -> CompletionResponse:
        """
        Postprocess the Ollama response into a CompletionResponse.
        
        This is where we can add:
        - Content filtering
        - Response formatting
        - Usage tracking
        - Logging
        """
        # Extract completion text
        completion_text = ollama_response.get("response", "")
        
        # Apply any postprocessing filters
        filtered_completion = await self._filter_completion(completion_text)
        
        # Calculate token usage (approximate for now)
        prompt_tokens = len(original_request.prompt.split())
        completion_tokens = len(filtered_completion.split())
        
        usage = UsageStats(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        return CompletionResponse(
            completion=filtered_completion,
            model=original_request.model,
            usage=usage,
            finish_reason="stop",
            created=int(time.time())
        )
    
    async def _filter_completion(self, completion_text: str) -> str:
        """
        Apply content filtering to the completion.
        
        This is where we can add:
        - Safety filtering
        - Content moderation
        - Format validation
        """
        # For now, return as-is
        # TODO: Add content filtering logic
        return completion_text.strip()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the message processing pipeline."""
        return {
            "status": "healthy",
            "ollama_url": self.ollama_url,
            "ollama_running": await self.ollama_manager.is_running(),
            "timestamp": int(time.time())
        }
