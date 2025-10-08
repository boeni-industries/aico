"""
Base classes for AI processing components in the AICO framework.

Provides foundational interfaces and data structures for AI component coordination
via message bus, including processing contexts, results, and base processor classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid


@dataclass
class ProcessingContext:
    """
    Shared context for AI processing operations across components.
    
    Contains conversation state, user information, and cross-component
    coordination data for maintaining consistency across AI processing.
    """
    # Core identifiers
    conversation_id: str
    user_id: str
    request_id: str
    correlation_id: Optional[str] = None
    
    # Conversation context
    message_content: str = ""
    message_type: str = "text"
    turn_number: int = 0
    conversation_phase: str = "active"
    
    # User context
    user_name: str = ""
    relationship_type: str = "user"
    conversation_style: str = "friendly"
    
    # Processing metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_priority: str = "normal"  # low, normal, high, urgent
    timeout_ms: int = 5000
    
    # Cross-component state
    shared_state: Dict[str, Any] = field(default_factory=dict)
    processing_history: List[str] = field(default_factory=list)
    
    # Performance tracking
    start_time: Optional[datetime] = None
    processing_times: Dict[str, float] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """
    Result of AI processing operation with metadata and performance tracking.
    
    Contains processing output, confidence scores, performance metrics,
    and coordination information for result aggregation.
    """
    # Core result data
    component: str
    operation: str
    success: bool
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    confidence_score: float = 0.0
    processing_time_ms: float = 0.0
    algorithm_used: str = "default"
    
    # Error handling
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    fallback_used: bool = False
    
    # Coordination
    correlation_id: Optional[str] = None
    dependencies_met: bool = True
    next_components: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "v1"


class BaseAIProcessor(ABC):
    """
    Abstract base class for AI processing components.
    
    Defines the standard interface for AI processors that can be coordinated
    via message bus, including processing methods, health checks, and metrics.
    """
    
    def __init__(self, component_name: str, version: str = "v1"):
        self.component_name = component_name
        self.version = version
        self.is_healthy = True
        self.processing_count = 0
        self.error_count = 0
        self.average_processing_time = 0.0
    
    @abstractmethod
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """
        Process AI request with given context.
        
        Args:
            context: Processing context with conversation and user state
            
        Returns:
            ProcessingResult with output data and metadata
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if processor is healthy and ready to handle requests.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Get processor capabilities and configuration.
        
        Returns:
            Dictionary describing processor capabilities
        """
        return {
            "component": self.component_name,
            "version": self.version,
            "operations": self.get_supported_operations(),
            "performance": {
                "average_processing_time_ms": self.average_processing_time,
                "processing_count": self.processing_count,
                "error_rate": self.error_count / max(self.processing_count, 1)
            }
        }
    
    @abstractmethod
    def get_supported_operations(self) -> List[str]:
        """
        Get list of operations supported by this processor.
        
        Returns:
            List of operation names
        """
        pass
    
    def update_metrics(self, processing_time_ms: float, success: bool):
        """
        Update processor performance metrics.
        
        Args:
            processing_time_ms: Time taken for processing
            success: Whether processing was successful
        """
        self.processing_count += 1
        if not success:
            self.error_count += 1
        
        # Update rolling average processing time
        if self.processing_count == 1:
            self.average_processing_time = processing_time_ms
        else:
            alpha = 0.1  # Smoothing factor
            self.average_processing_time = (
                alpha * processing_time_ms + 
                (1 - alpha) * self.average_processing_time
            )
    
    def should_skip_processing(self, context: ProcessingContext) -> bool:
        """
        Determine if processing should be skipped based on context and health.
        
        Args:
            context: Processing context
            
        Returns:
            True if processing should be skipped
        """
        # Skip if unhealthy
        if not self.is_healthy:
            return True
        
        # Skip if error rate too high
        error_rate = self.error_count / max(self.processing_count, 1)
        if error_rate > 0.5:  # 50% error rate threshold
            return True
        
        # Skip if processing time too slow for priority
        if context.processing_priority == "urgent" and self.average_processing_time > 1000:
            return True
        
        return False


class AIProcessorRegistry:
    """
    Registry for managing AI processor instances and routing requests.
    
    Maintains a registry of available processors, handles load balancing,
    and provides processor discovery and health monitoring.
    """
    
    def __init__(self):
        self.processors: Dict[str, List[BaseAIProcessor]] = {}
        self.processor_health: Dict[str, bool] = {}
    
    def register_processor(self, processor: BaseAIProcessor):
        """
        Register an AI processor in the registry.
        
        Args:
            processor: AI processor instance to register
        """
        component = processor.component_name
        if component not in self.processors:
            self.processors[component] = []
        
        self.processors[component].append(processor)
        self.processor_health[f"{component}_{id(processor)}"] = True
    
    def get_processor(self, component: str, operation: str = None) -> Optional[BaseAIProcessor]:
        """
        Get best available processor for component and operation.
        
        Args:
            component: Component name
            operation: Optional operation name for filtering
            
        Returns:
            Best available processor or None if not found
        """
        if component not in self.processors:
            return None
        
        available_processors = [
            p for p in self.processors[component]
            if self.processor_health.get(f"{component}_{id(p)}", False)
        ]
        
        if not available_processors:
            return None
        
        # Filter by operation if specified
        if operation:
            available_processors = [
                p for p in available_processors
                if operation in p.get_supported_operations()
            ]
        
        if not available_processors:
            return None
        
        # Return processor with best performance (lowest average processing time)
        return min(available_processors, key=lambda p: p.average_processing_time)
    
    async def health_check_all(self):
        """
        Perform health check on all registered processors.
        """
        for component, processors in self.processors.items():
            for processor in processors:
                processor_id = f"{component}_{id(processor)}"
                try:
                    is_healthy = await processor.health_check()
                    self.processor_health[processor_id] = is_healthy
                    processor.is_healthy = is_healthy
                except Exception:
                    self.processor_health[processor_id] = False
                    processor.is_healthy = False
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get status of all processors in registry.
        
        Returns:
            Dictionary with processor status information
        """
        status = {}
        for component, processors in self.processors.items():
            component_status = []
            for processor in processors:
                processor_id = f"{component}_{id(processor)}"
                component_status.append({
                    "processor_id": processor_id,
                    "healthy": self.processor_health.get(processor_id, False),
                    "processing_count": processor.processing_count,
                    "error_count": processor.error_count,
                    "average_processing_time_ms": processor.average_processing_time
                })
            status[component] = component_status
        
        return status
