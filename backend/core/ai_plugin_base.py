"""
AI Plugin Contracts and Interfaces

Defines standardized contracts for AI processing plugins that integrate with
the conversation engine. All AI components implement these interfaces.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime

from .plugin_base import BasePlugin, PluginMetadata, PluginPriority


@dataclass
class ProcessingRequest:
    """Standard request contract for AI processing"""
    request_id: str
    user_id: str
    conversation_id: str
    text: str
    context: Dict[str, Any]
    timestamp: datetime


@dataclass
class ProcessingResponse:
    """Standard response contract from AI processing"""
    request_id: str
    success: bool
    data: Dict[str, Any]
    confidence: float = 0.0
    processing_time_ms: int = 0
    error: Optional[str] = None


@dataclass
class CapabilityContract:
    """Contract defining AI plugin capabilities"""
    name: str
    version: str
    description: str
    input_requirements: List[str]
    output_format: Dict[str, str]
    features: List[str]
    dependencies: List[str] = None


class AIProcessingPlugin(BasePlugin):
    """
    Base class for AI processing plugins that inherit from the standard plugin system.
    
    Provides standardized contracts for conversation AI components while maintaining
    consistency with the overall AICO plugin architecture.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
    
    @property
    def metadata(self) -> PluginMetadata:
        """Standard plugin metadata"""
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description=f"AI processing plugin: {self.name}",
            priority=PluginPriority.BUSINESS,
            dependencies=[]
        )
    
    @abstractmethod
    async def process(self, request: ProcessingRequest) -> ProcessingResponse:
        """
        Core processing contract - all AI plugins must implement this.
        
        Args:
            request: Standardized processing request
            
        Returns:
            Standardized processing response
        """
        pass
    
    @abstractmethod
    def get_capability_contract(self) -> CapabilityContract:
        """
        Return capability contract defining what this plugin can do.
        
        Returns:
            Contract specifying inputs, outputs, and features
        """
        pass
    
    async def initialize(self) -> None:
        """Initialize AI plugin - override if needed"""
        self.logger.info(f"AI plugin {self.name} initialized")
    
    async def start(self) -> None:
        """Start AI plugin operations - override if needed"""
        self.logger.info(f"AI plugin {self.name} started")
    
    async def stop(self) -> None:
        """Stop AI plugin operations - override if needed"""
        self.logger.info(f"AI plugin {self.name} stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check including capability info"""
        base_health = await super().health_check()
        capability = self.get_capability_contract()
        
        return {
            **base_health,
            "capability": {
                "features": capability.features,
                "input_requirements": capability.input_requirements,
                "output_format": capability.output_format
            }
        }
