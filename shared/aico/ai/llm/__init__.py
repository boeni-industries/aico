"""LLM client abstraction layer for AICO.

Provides unified interface for different LLM inference engines (vLLM, Ollama).
"""

from .client import LLMClient
from .factory import LLMClientFactory

__all__ = ["LLMClient", "LLMClientFactory"]
