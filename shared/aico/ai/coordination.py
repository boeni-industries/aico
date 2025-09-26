"""
AI Processing Coordination Framework

Provides message bus-based coordination for AI components, including request/response
patterns, scatter-gather coordination, and performance monitoring for AICO AI processing.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime, timedelta
import logging

from ..core.topics import AICOTopics
from ..core.bus import MessageBusClient
from .base import ProcessingContext, ProcessingResult, BaseAIProcessor


@dataclass
class AIProcessingRequest:
    """
    Request for AI processing via message bus coordination.
    
    Contains processing parameters, coordination metadata, and performance
    requirements for distributed AI component processing.
    """
    # Core request data
    component: str
    operation: str
    context: ProcessingContext
    
    # Coordination metadata
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    
    # Performance requirements
    timeout_ms: int = 5000
    max_retries: int = 2
    require_response: bool = True
    
    # Coordination patterns
    coordination_type: str = "request_response"  # request_response, fire_and_forget, scatter_gather
    parallel_components: List[str] = field(default_factory=list)
    dependency_components: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requester: str = "conversation_engine"


@dataclass
class AIProcessingResponse:
    """
    Response from AI processing with coordination metadata.
    
    Contains processing results, performance metrics, and coordination
    information for result aggregation and flow control.
    """
    # Core response data
    request_id: str
    component: str
    operation: str
    result: ProcessingResult
    
    # Coordination metadata
    correlation_id: Optional[str] = None
    sequence_number: int = 0
    is_final: bool = True
    
    # Performance data
    processing_time_ms: float = 0.0
    queue_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    responder: str = ""


class AIProcessingCoordinator:
    """
    Coordinates AI processing requests across multiple components via message bus.
    
    Implements request/response, fire-and-forget, and scatter-gather coordination
    patterns with timeout handling, retry logic, and performance monitoring.
    """
    
    def __init__(self, client_name: str = "ai_coordinator"):
        self.client_name = client_name
        self.bus_client: Optional[MessageBusClient] = None
        self.logger = logging.getLogger(f"aico.ai.coordination.{client_name}")
        
        # Coordination state
        self.pending_requests: Dict[str, AIProcessingRequest] = {}
        self.pending_responses: Dict[str, List[AIProcessingResponse]] = {}
        self.correlation_groups: Dict[str, Set[str]] = {}  # correlation_id -> request_ids
        
        # Performance tracking
        self.request_count = 0
        self.response_count = 0
        self.timeout_count = 0
        self.average_response_time = 0.0
        
        # Callbacks
        self.response_callbacks: Dict[str, Callable] = {}
        self.timeout_callbacks: Dict[str, Callable] = {}
    
    async def initialize(self):
        """Initialize message bus client and subscriptions."""
        try:
            self.bus_client = MessageBusClient(self.client_name)
            await self.bus_client.connect()
            
            # Subscribe to all AI response topics
            await self.bus_client.subscribe(
                AICOTopics.ZMQ_AI_PREFIX,
                self._handle_ai_response
            )
            
            self.logger.info("AI Processing Coordinator initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI coordinator: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown coordinator and cleanup resources."""
        if self.bus_client:
            await self.bus_client.disconnect()
        
        # Cancel pending requests
        for request_id in list(self.pending_requests.keys()):
            await self._handle_request_timeout(request_id)
        
        self.logger.info("AI Processing Coordinator shutdown complete")
    
    async def process_request(self, request: AIProcessingRequest) -> Optional[AIProcessingResponse]:
        """
        Process AI request using specified coordination pattern.
        
        Args:
            request: AI processing request
            
        Returns:
            Processing response or None for fire-and-forget
        """
        start_time = time.time()
        
        try:
            if request.coordination_type == "fire_and_forget":
                return await self._process_fire_and_forget(request)
            elif request.coordination_type == "scatter_gather":
                return await self._process_scatter_gather(request)
            else:
                return await self._process_request_response(request)
                
        except Exception as e:
            self.logger.error(f"Error processing AI request {request.request_id}: {e}")
            return self._create_error_response(request, str(e))
        
        finally:
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(processing_time)
    
    async def _process_request_response(self, request: AIProcessingRequest) -> Optional[AIProcessingResponse]:
        """Process request using request/response pattern."""
        self.pending_requests[request.request_id] = request
        
        # Build topic for request
        topic = AICOTopics.ai_processing(
            request.component,
            request.operation,
            "request"
        )
        
        # Publish request
        await self.bus_client.publish(topic, {
            "request_id": request.request_id,
            "correlation_id": request.correlation_id,
            "component": request.component,
            "operation": request.operation,
            "context": self._serialize_context(request.context),
            "priority": request.priority,
            "timeout_ms": request.timeout_ms,
            "timestamp": request.timestamp.isoformat()
        })
        
        self.request_count += 1
        self.logger.debug(f"Published AI request {request.request_id} to {topic}")
        
        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                self._wait_for_response(request.request_id),
                timeout=request.timeout_ms / 1000.0
            )
            return response
            
        except asyncio.TimeoutError:
            self.timeout_count += 1
            self.logger.warning(f"AI request {request.request_id} timed out")
            await self._handle_request_timeout(request.request_id)
            return self._create_timeout_response(request)
    
    async def _process_fire_and_forget(self, request: AIProcessingRequest) -> None:
        """Process request using fire-and-forget pattern."""
        topic = AICOTopics.ai_processing(
            request.component,
            request.operation,
            "request"
        )
        
        await self.bus_client.publish(topic, {
            "request_id": request.request_id,
            "component": request.component,
            "operation": request.operation,
            "context": self._serialize_context(request.context),
            "priority": request.priority,
            "require_response": False,
            "timestamp": request.timestamp.isoformat()
        })
        
        self.request_count += 1
        self.logger.debug(f"Published fire-and-forget request {request.request_id}")
        return None
    
    async def _process_scatter_gather(self, request: AIProcessingRequest) -> AIProcessingResponse:
        """Process request using scatter-gather pattern."""
        if not request.parallel_components:
            raise ValueError("Scatter-gather requires parallel_components")
        
        correlation_id = request.correlation_id or str(uuid.uuid4())
        request.correlation_id = correlation_id
        
        # Track correlation group
        self.correlation_groups[correlation_id] = set()
        
        # Send requests to all parallel components
        for component in request.parallel_components:
            component_request = AIProcessingRequest(
                component=component,
                operation=request.operation,
                context=request.context,
                correlation_id=correlation_id,
                priority=request.priority,
                timeout_ms=request.timeout_ms
            )
            
            self.pending_requests[component_request.request_id] = component_request
            self.correlation_groups[correlation_id].add(component_request.request_id)
            
            topic = AICOTopics.ai_coordination(
                correlation_id,
                component,
                request.operation
            )
            
            await self.bus_client.publish(topic, {
                "request_id": component_request.request_id,
                "correlation_id": correlation_id,
                "component": component,
                "operation": request.operation,
                "context": self._serialize_context(request.context),
                "priority": request.priority,
                "timeout_ms": request.timeout_ms,
                "timestamp": component_request.timestamp.isoformat()
            })
        
        # Wait for all responses
        try:
            responses = await asyncio.wait_for(
                self._wait_for_correlation_group(correlation_id),
                timeout=request.timeout_ms / 1000.0
            )
            
            # Aggregate responses
            return self._aggregate_responses(request, responses)
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Scatter-gather {correlation_id} timed out")
            return self._create_timeout_response(request)
    
    async def _handle_ai_response(self, topic: str, message: Any):
        """Handle AI processing response from message bus."""
        try:
            request_id = message.get("request_id")
            if not request_id or request_id not in self.pending_requests:
                return
            
            response = AIProcessingResponse(
                request_id=request_id,
                component=message.get("component", ""),
                operation=message.get("operation", ""),
                result=self._deserialize_result(message.get("result", {})),
                correlation_id=message.get("correlation_id"),
                processing_time_ms=message.get("processing_time_ms", 0.0),
                responder=message.get("responder", "")
            )
            
            # Store response
            if request_id not in self.pending_responses:
                self.pending_responses[request_id] = []
            self.pending_responses[request_id].append(response)
            
            self.response_count += 1
            self.logger.debug(f"Received AI response for {request_id}")
            
            # Trigger callback if registered
            if request_id in self.response_callbacks:
                callback = self.response_callbacks.pop(request_id)
                await callback(response)
        
        except Exception as e:
            self.logger.error(f"Error handling AI response: {e}")
    
    async def _wait_for_response(self, request_id: str) -> AIProcessingResponse:
        """Wait for response to specific request."""
        while request_id in self.pending_requests:
            if request_id in self.pending_responses and self.pending_responses[request_id]:
                response = self.pending_responses[request_id][0]
                self._cleanup_request(request_id)
                return response
            
            await asyncio.sleep(0.01)  # 10ms polling
        
        raise asyncio.TimeoutError(f"No response received for {request_id}")
    
    async def _wait_for_correlation_group(self, correlation_id: str) -> List[AIProcessingResponse]:
        """Wait for all responses in correlation group."""
        if correlation_id not in self.correlation_groups:
            return []
        
        expected_count = len(self.correlation_groups[correlation_id])
        responses = []
        
        while len(responses) < expected_count:
            for request_id in self.correlation_groups[correlation_id]:
                if (request_id in self.pending_responses and 
                    self.pending_responses[request_id] and
                    request_id not in [r.request_id for r in responses]):
                    
                    responses.append(self.pending_responses[request_id][0])
            
            if len(responses) < expected_count:
                await asyncio.sleep(0.01)
        
        # Cleanup correlation group
        for request_id in self.correlation_groups[correlation_id]:
            self._cleanup_request(request_id)
        del self.correlation_groups[correlation_id]
        
        return responses
    
    async def _handle_request_timeout(self, request_id: str):
        """Handle request timeout."""
        if request_id in self.timeout_callbacks:
            callback = self.timeout_callbacks.pop(request_id)
            await callback(request_id)
        
        self._cleanup_request(request_id)
    
    def _cleanup_request(self, request_id: str):
        """Cleanup request state."""
        self.pending_requests.pop(request_id, None)
        self.pending_responses.pop(request_id, None)
        self.response_callbacks.pop(request_id, None)
        self.timeout_callbacks.pop(request_id, None)
    
    def _serialize_context(self, context: ProcessingContext) -> Dict[str, Any]:
        """Serialize processing context for message bus."""
        return {
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "correlation_id": context.correlation_id,
            "message_content": context.message_content,
            "message_type": context.message_type,
            "turn_number": context.turn_number,
            "conversation_phase": context.conversation_phase,
            "user_name": context.user_name,
            "relationship_type": context.relationship_type,
            "conversation_style": context.conversation_style,
            "processing_priority": context.processing_priority,
            "timeout_ms": context.timeout_ms,
            "shared_state": context.shared_state,
            "timestamp": context.timestamp.isoformat()
        }
    
    def _deserialize_result(self, result_data: Dict[str, Any]) -> ProcessingResult:
        """Deserialize processing result from message bus."""
        return ProcessingResult(
            component=result_data.get("component", ""),
            operation=result_data.get("operation", ""),
            success=result_data.get("success", False),
            result_data=result_data.get("result_data", {}),
            confidence_score=result_data.get("confidence_score", 0.0),
            processing_time_ms=result_data.get("processing_time_ms", 0.0),
            algorithm_used=result_data.get("algorithm_used", "default"),
            error_message=result_data.get("error_message"),
            error_code=result_data.get("error_code"),
            fallback_used=result_data.get("fallback_used", False)
        )
    
    def _create_error_response(self, request: AIProcessingRequest, error: str) -> AIProcessingResponse:
        """Create error response for failed request."""
        return AIProcessingResponse(
            request_id=request.request_id,
            component=request.component,
            operation=request.operation,
            result=ProcessingResult(
                component=request.component,
                operation=request.operation,
                success=False,
                error_message=error,
                error_code="PROCESSING_ERROR"
            )
        )
    
    def _create_timeout_response(self, request: AIProcessingRequest) -> AIProcessingResponse:
        """Create timeout response for timed out request."""
        return AIProcessingResponse(
            request_id=request.request_id,
            component=request.component,
            operation=request.operation,
            result=ProcessingResult(
                component=request.component,
                operation=request.operation,
                success=False,
                error_message="Request timed out",
                error_code="TIMEOUT",
                fallback_used=True
            )
        )
    
    def _aggregate_responses(self, request: AIProcessingRequest, responses: List[AIProcessingResponse]) -> AIProcessingResponse:
        """Aggregate multiple responses into single response."""
        successful_responses = [r for r in responses if r.result.success]
        
        if not successful_responses:
            # All failed - return first error
            return responses[0] if responses else self._create_error_response(request, "No responses received")
        
        # Use response with highest confidence
        best_response = max(successful_responses, key=lambda r: r.result.confidence_score)
        
        # Aggregate result data
        aggregated_data = {}
        for response in successful_responses:
            aggregated_data.update(response.result.result_data)
        
        best_response.result.result_data = aggregated_data
        return best_response
    
    def _update_performance_metrics(self, processing_time_ms: float):
        """Update coordinator performance metrics."""
        if self.request_count == 1:
            self.average_response_time = processing_time_ms
        else:
            alpha = 0.1  # Smoothing factor
            self.average_response_time = (
                alpha * processing_time_ms + 
                (1 - alpha) * self.average_response_time
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get coordinator performance statistics."""
        return {
            "request_count": self.request_count,
            "response_count": self.response_count,
            "timeout_count": self.timeout_count,
            "timeout_rate": self.timeout_count / max(self.request_count, 1),
            "average_response_time_ms": self.average_response_time,
            "pending_requests": len(self.pending_requests),
            "active_correlations": len(self.correlation_groups)
        }
