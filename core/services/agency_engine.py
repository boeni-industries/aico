"""Agency AI plugin - thin adapter over shared AgencyEngine.

This plugin exposes a standardized capability contract to the API gateway
and conversation engine, while delegating all autonomous agency logic to
the shared/aico/ai/agency/AgencyEngine orchestrator registered in ai_registry.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.ai import ai_registry

from core.services.ai_plugin_base import AIProcessingPlugin, ProcessingRequest, ProcessingResponse, CapabilityContract


logger = get_logger("core.services.agency_plugin")


class AgencyPlugin(AIProcessingPlugin):
    """
    Autonomous agency plugin providing standardized agency processing contract.
    
    Implements pure interface for conversation engine integration.
    Actual agency algorithms will be implemented in shared/aico/ai/agency/
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        # Override config to use agency domain instead of core.services.agency
        self.config = container.config.get("agency", {})
        # Resolve shared AgencyEngine from AI processor registry (Phase 1)
        self._agency_engine = ai_registry.get("agency")
        if not self._agency_engine:
            logger.error("[AGENCY_PLUGIN] AgencyEngine not found in ai_registry under key 'agency'")
    
    def get_capability_contract(self) -> CapabilityContract:
        """Define autonomous agency capabilities contract"""
        return CapabilityContract(
            name="autonomous_agency",
            version="1.0.0",
            description="Autonomous goal generation and proactive behavior",
            input_requirements=["text", "user_id", "context"],
            output_format={
                "proactive_suggestions": "list",
                "autonomous_goals": "list",
                "behavioral_triggers": "dict",
                "confidence": "float"
            },
            features=[
                "goal_generation",
                "proactive_behavior",
                "autonomous_learning"
            ]
        )

    
    async def process(self, request: ProcessingRequest) -> ProcessingResponse:
        """
        Process autonomous agency request using contract interface.
        
        Args:
            request: Processing request with text and context
            
        Returns:
            Agency analysis results following contract
        """
        start_time = datetime.now()
        
        try:
            if not self._agency_engine:
                # Fail-safe: engine not available, return empty but successful response
                logger.warning("[AGENCY_PLUGIN] AgencyEngine not available, returning empty analysis result")
                result_data = {
                    "proactive_suggestions": [],
                    "autonomous_goals": [],
                    "behavioral_triggers": {},
                    "analysis_timestamp": start_time.isoformat(),
                }
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return ProcessingResponse(
                    request_id=request.request_id,
                    success=True,
                    data=result_data,
                    confidence=0.0,
                    processing_time_ms=processing_time,
                )

            # Delegate analysis to shared AgencyEngine
            engine_result: Dict[str, Any] = await self._agency_engine.analyze_conversation_turn(
                user_id=request.user_id or "",
                text=request.text or "",
                context=request.context or {},
            )

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProcessingResponse(
                request_id=request.request_id,
                success=True,
                data=engine_result,
                confidence=float(engine_result.get("confidence", 0.0) or 0.0),
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ProcessingResponse(
                request_id=request.request_id,
                success=False,
                data={},
                confidence=0.0,
                processing_time_ms=processing_time,
                error=str(e)
            )


# Plugin factory for service container registration
def create_agency_plugin(container, **kwargs):
    """Factory function for agency plugin creation"""
    return AgencyPlugin("agency", container)
