"""
AI Processor Registration and Management

Simple registry system for AI processors following AICO's modular architecture.
Provides clean integration points for future AI algorithm implementations.
"""

from typing import Dict, Any, Optional, Protocol
from .base import ProcessingContext


class EmotionProcessor(Protocol):
    """Protocol for emotion analysis processors"""
    async def analyze_emotion(self, context: ProcessingContext) -> Dict[str, Any]:
        """Analyze emotional content and return emotion data"""
        ...


class PersonalityProcessor(Protocol):
    """Protocol for personality expression processors"""
    async def express_personality(self, context: ProcessingContext) -> Dict[str, Any]:
        """Generate personality-driven response parameters"""
        ...


class MemoryProcessor(Protocol):
    """Protocol for memory retrieval processors"""
    async def retrieve_memories(self, context: ProcessingContext) -> Dict[str, Any]:
        """Retrieve relevant memories for context"""
        ...


class EmbodimentProcessor(Protocol):
    """Protocol for embodiment (avatar/voice) processors"""
    async def generate_avatar_actions(self, context: ProcessingContext) -> Dict[str, Any]:
        """Generate avatar actions for response"""
        ...
    
    async def generate_voice_parameters(self, context: ProcessingContext) -> Dict[str, Any]:
        """Generate voice synthesis parameters"""
        ...


class AIProcessorRegistry:
    """
    Simple registry for AI processors.
    
    Usage:
        # Register processor
        registry.register("emotion", emotion_processor)
        
        # Get processor
        processor = registry.get("emotion")
    """
    
    def __init__(self):
        self.processors: Dict[str, Any] = {}
    
    def register(self, component_name: str, processor: Any) -> None:
        """Register an AI processor"""
        self.processors[component_name] = processor
    
    def get(self, component_name: str) -> Optional[Any]:
        """Get registered processor by name"""
        return self.processors.get(component_name)
    
    def unregister(self, component_name: str) -> None:
        """Unregister a processor"""
        self.processors.pop(component_name, None)
    
    def list_processors(self) -> Dict[str, str]:
        """List all registered processors"""
        return {name: type(proc).__name__ for name, proc in self.processors.items()}


# Global registry instance
ai_registry = AIProcessorRegistry()
