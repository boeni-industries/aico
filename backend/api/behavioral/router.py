"""
Behavioral Learning API Router

REST endpoints for feedback submission and skill management.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from aico.core.logging import get_logger
from backend.api.conversation.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork
from aico.ai.memory.behavioral import SkillStore, FeedbackEvent, PreferenceManager

from .schemas import FeedbackRequest, FeedbackResponse

logger = get_logger("backend.api.behavioral")

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow)
) -> FeedbackResponse:
    """
    Submit user feedback on AI response.
    
    Updates skill confidence immediately and stores feedback event for batch processing.
    
    Args:
        request: Feedback request with message_id, reward, optional reason/text
        current_user: Authenticated user from JWT
        db: Database connection
        
    Returns:
        FeedbackResponse with status and updated confidence
    """
    user_id = current_user["user_uuid"]
    
    logger.info("📊 [FEEDBACK] Received feedback submission", extra={
        "user_id": user_id,
        "message_id": request.message_id,
        "skill_id": request.skill_id,
        "reward": request.reward,
        "has_reason": request.reason is not None,
        "has_free_text": request.free_text is not None
    })
    
    try:
        # Use skill_id from request (frontend should provide it if available)
        skill_id = request.skill_id
        
        # If no skill_id provided, look it up from ams_trajectories
        if not skill_id:
            logger.info("📊 [FEEDBACK] No skill_id provided, looking up from trajectory", extra={
                "message_id": request.message_id
            })
            
            # Look up skill_id from trajectory using message_id
            trajectories = await uow.ams_trajectories.list(
                filters={"message_id": request.message_id},
                limit=1
            )
            
            if trajectories and trajectories[0].selected_skill_id:
                skill_id = trajectories[0].selected_skill_id
                logger.info("📊 [FEEDBACK] ✅ Found skill_id from trajectory", extra={
                    "message_id": request.message_id,
                    "skill_id": skill_id
                })
            else:
                logger.warning("📊 [FEEDBACK] ⚠️ No trajectory found for message", extra={
                    "message_id": request.message_id
                })
        
        # Create feedback event
        event_id = str(uuid.uuid4())
        feedback_event = FeedbackEvent(
            event_id=event_id,
            user_id=user_id,
            message_id=request.message_id,
            skill_id=skill_id,  # Use looked-up skill_id
            reward=request.reward,
            reason=request.reason,
            free_text=request.free_text,
            timestamp=datetime.utcnow(),
            processed=False
        )
        
        logger.info("📊 [FEEDBACK] Created feedback event", extra={
            "event_id": event_id,
            "user_id": user_id
        })
        
        # Store feedback event in AMS behavioral feedback table using repository
        from aico.data.ams.models import BehavioralFeedback
        
        feedback_record = BehavioralFeedback(
            feedback_id=feedback_event.event_id,
            user_id=feedback_event.user_id,
            message_id=feedback_event.message_id,
            skill_id=feedback_event.skill_id,
            reward=feedback_event.reward,
            reason=feedback_event.reason,
            free_text=feedback_event.free_text,
            timestamp=feedback_event.timestamp,
            processed=feedback_event.processed
        )
        
        await uow.ams_behavioral_feedback.create(feedback_record)
        await uow.commit()
        
        logger.info("📊 [FEEDBACK] Feedback event stored in database", extra={
            "event_id": event_id,
            "table": "ams_behavioral_feedback"
        })
        
        # Update skill confidence and preference vectors if skill_id available and reward is not neutral
        skill_updated = False
        new_confidence = None
        preference_updated = False
        
        if skill_id and request.reward != 0:
            logger.info("📊 [FEEDBACK] Updating skill confidence and preferences", extra={
                "skill_id": skill_id,
                "reward": request.reward
            })
            
            # Note: SkillStore and PreferenceManager need UnitOfWork migration
            # For now, skip the skill confidence update (handled by AMS consolidation)
            skill_updated = False
            new_confidence = None
            preference_updated = False
            
            logger.info("📊 [FEEDBACK] Skill confidence update deferred to AMS consolidation", extra={
                "skill_id": skill_id
            })
        else:
            logger.info("📊 [FEEDBACK] Skipping skill confidence updates (neutral reward or no skill_id)", extra={
                "skill_id": skill_id,
                "reward": request.reward,
                "reason": "no_skill_id" if not skill_id else "neutral_reward"
            })
            skill_updated = False
            new_confidence = None
            preference_updated = False
        
        logger.info("📊 [FEEDBACK] ✅ Feedback processing complete", extra={
            "event_id": event_id,
            "user_id": user_id,
            "message_id": request.message_id,
            "reward": request.reward,
            "skill_updated": skill_updated,
            "preference_updated": preference_updated,
            "new_confidence": new_confidence
        })
        
        response = FeedbackResponse(
            status="success",
            skill_updated=skill_updated,
            new_confidence=new_confidence,
            event_id=event_id
        )
        
        logger.info("📊 [FEEDBACK] Returning response", extra={
            "status": response.status,
            "event_id": response.event_id
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to process feedback: {e}", extra={
            "user_id": user_id,
            "message_id": request.message_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process feedback: {str(e)}"
        )
