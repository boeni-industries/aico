"""
Intent Classification Handler for ModelService

Lightweight handler that delegates to AICO's AI processing architecture.
Follows AICO patterns by using the shared AI processor in /shared/aico/ai/
"""

from typing import Optional, List
from aico.core.logging import get_logger
from aico.proto.aico_modelservice_pb2 import (
    IntentClassificationRequest, IntentClassificationResponse,
    IntentPrediction
)
from shared.aico.ai.base import ProcessingContext
from shared.aico.ai.analysis.intent_classifier import get_intent_classifier

logger = get_logger("modelservice", "handlers.intent_classification")


class IntentClassificationHandler:
    """
    ModelService handler for intent classification.
    
    Delegates to AICO's AI processing architecture in /shared/aico/ai/
    following established patterns for AI component coordination.
    """
    
    def __init__(self):
        self.processor = None
        logger.info("[INTENT_HANDLER] Intent classification handler initialized")

    async def initialize(self):
        """Initialize the AI processor"""
        try:
            self.processor = await get_intent_classifier()
            logger.info("[INTENT_HANDLER] ✅ AI processor initialized")
        except Exception as e:
            logger.error(f"[INTENT_HANDLER] Failed to initialize AI processor: {e}")
            raise

    async def handle_request(self, request: IntentClassificationRequest) -> IntentClassificationResponse:
        """Handle ZMQ intent classification request"""
        try:
            if not self.processor:
                await self.initialize()
            
            # Create processing context following AICO patterns
            context = ProcessingContext(
                thread_id="intent_classification",  # Not thread-specific
                user_id=request.user_id or "anonymous",
                request_id=f"intent_{hash(request.text)}",
                message_content=request.text,
                shared_state={
                    'recent_intents': list(request.conversation_context) if request.conversation_context else []
                }
            )
            
            # Process using AI processor
            result = await self.processor.process(context)
            
            # Create response
            response = IntentClassificationResponse()
            response.success = result.success
            
            if result.success:
                data = result.data
                response.predicted_intent = data.get("predicted_intent", "general")
                response.confidence = data.get("confidence", 0.0)
                response.detected_language = data.get("detected_language", "unknown")
                response.inference_time_ms = data.get("inference_time_ms", 0.0)
                
                # Add alternative predictions
                alternatives = data.get("alternatives", [])
                for intent, confidence in alternatives:
                    alt_prediction = response.alternative_predictions.add()
                    alt_prediction.intent = intent
                    alt_prediction.confidence = confidence
                
                # Add metadata
                for key, value in result.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        response.metadata[key] = str(value)
            else:
                response.error = result.error or "Processing failed"
            
            return response
            
        except Exception as e:
            logger.error(f"[INTENT_HANDLER] Request handling failed: {e}")
            
            # Return error response
            response = IntentClassificationResponse()
            response.success = False
            response.predicted_intent = "general"
            response.confidence = 0.0
            response.detected_language = "unknown"
            response.error = str(e)
            
            return response


# Global handler instance
intent_handler = IntentClassificationHandler()


async def get_intent_classification_handler() -> IntentClassificationHandler:
    """Get the global intent classification handler"""
    return intent_handler
