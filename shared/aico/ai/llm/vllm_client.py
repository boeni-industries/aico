"""vLLM client implementation using OpenAI-compatible API."""

from typing import List, Dict, Any, AsyncIterator, Optional
from openai import AsyncOpenAI
from .client import LLMClient


class VLLMClient(LLMClient):
    """vLLM client using OpenAI-compatible API."""
    
    def __init__(self, host: str, port: int, api_key: str = "EMPTY"):
        """Initialize vLLM client.
        
        Args:
            host: vLLM server host
            port: vLLM server port
            api_key: API key (default "EMPTY" for local vLLM)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1"
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncIterator[Dict[str, Any]]:
        """Generate chat completion via vLLM.
        
        Maps AICO parameters to vLLM/OpenAI format.
        """
        # Extract vLLM-specific parameters
        extra_body = {}

        # Qwen3 thinking mode / reasoning models
        # vLLM supports request-level chat_template_kwargs overrides.
        chat_template_kwargs = kwargs.pop("chat_template_kwargs", None)
        if chat_template_kwargs is None:
            chat_template_kwargs = {"enable_thinking": True}
        if chat_template_kwargs:
            extra_body["chat_template_kwargs"] = chat_template_kwargs
        
        # Map AICO parameters to vLLM extra_body
        if "top_k" in kwargs:
            extra_body["top_k"] = kwargs.pop("top_k")
        if "repeat_penalty" in kwargs:
            extra_body["repetition_penalty"] = kwargs.pop("repeat_penalty")
        if "min_p" in kwargs:
            extra_body["min_p"] = kwargs.pop("min_p")
        if "repeat_last_n" in kwargs:
            # vLLM doesn't have direct equivalent, skip
            kwargs.pop("repeat_last_n")
        if "num_ctx" in kwargs:
            # Map to max_model_len (but this is server-side config)
            kwargs.pop("num_ctx")
        
        # Call vLLM via OpenAI-compatible API
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=kwargs.pop("top_p", 0.9),
            stream=stream,
            extra_body=extra_body if extra_body else None,
            **kwargs
        )
        
        if stream:
            return response  # AsyncIterator
        else:
            # Convert to dict format
            return {
                "id": response.id,
                "model": response.model,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            }
    
    async def health_check(self) -> bool:
        """Check if vLLM server is healthy."""
        try:
            # Try to list models as health check
            models = await self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """List available models from vLLM."""
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data]
        except Exception:
            return []
