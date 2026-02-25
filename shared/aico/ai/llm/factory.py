"""LLM client factory for vLLM."""

from typing import Optional
from .client import LLMClient
from .vllm_client import VLLMClient




class LLMClientFactory:
    """Factory for creating vLLM clients."""
    
    @staticmethod
    def create(config: dict) -> LLMClient:
        """Create vLLM client from configuration.
        
        Args:
            config: Configuration dict with 'vllm' key
            
        Returns:
            VLLMClient instance
            
        Raises:
            ValueError: If vLLM configuration is invalid
        """
        vllm_config = config.get("vllm", {})
        if not vllm_config:
            raise ValueError("vLLM configuration missing")
        
        return VLLMClient(
            host=vllm_config.get("host", "localhost"),
            port=vllm_config.get("port", 8774),
            api_key=vllm_config.get("api_key", "EMPTY")
        )
