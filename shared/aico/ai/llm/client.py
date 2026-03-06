"""Base LLM client interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncIterator[Dict[str, Any]]:
        """Generate chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional engine-specific parameters
            
        Returns:
            Response dict or async iterator for streaming
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is healthy.
        
        Returns:
            True if service is available and responding
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models.
        
        Returns:
            List of model identifiers
        """
        pass
