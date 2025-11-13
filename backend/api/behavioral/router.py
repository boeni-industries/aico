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
from backend.core.lifecycle_manager import get_database
from aico.ai.memory.behavioral import SkillStore, FeedbackEvent

from .schemas import FeedbackRequest, FeedbackResponse

logger = get_logger("backend", "api.behavioral")

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db = Depends(get_database)
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
        # Create feedback event
        event_id = str(uuid.uuid4())
        feedback_event = FeedbackEvent(
            event_id=event_id,
            user_id=user_id,
            message_id=request.message_id,
            skill_id=request.skill_id,
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
        
        # Store feedback event
        db.execute(
            """INSERT INTO feedback_events (
                event_id, user_id, message_id, skill_id, reward,
                reason, free_text, timestamp, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feedback_event.event_id,
                feedback_event.user_id,
                feedback_event.message_id,
                feedback_event.skill_id,
                feedback_event.reward,
                feedback_event.reason,
                feedback_event.free_text,
                feedback_event.timestamp.isoformat(),
                feedback_event.processed
            )
        )
        db.commit()
        
        logger.info("📊 [FEEDBACK] Feedback event stored in database", extra={
            "event_id": event_id,
            "table": "feedback_events"
        })
        
        # Update skill confidence if skill_id provided and reward is not neutral
        skill_updated = False
        new_confidence = None
        
        if request.skill_id and request.reward != 0:
            logger.info("📊 [FEEDBACK] Updating skill confidence", extra={
                "skill_id": request.skill_id,
                "reward": request.reward
            })
            skill_store = SkillStore(db)
            new_confidence = await skill_store.update_confidence(
                user_id=user_id,
                skill_id=request.skill_id,
                reward=request.reward
            )
            skill_updated = True
            
            logger.info("📊 [FEEDBACK] ✅ Skill confidence updated", extra={
                "user_id": user_id,
                "skill_id": request.skill_id,
                "reward": request.reward,
                "new_confidence": new_confidence
            })
        else:
            logger.info("📊 [FEEDBACK] Skipping skill confidence update", extra={
                "skill_id": request.skill_id,
                "reward": request.reward,
                "reason": "no_skill_id" if not request.skill_id else "neutral_reward"
            })
        
        logger.info("📊 [FEEDBACK] ✅ Feedback processing complete", extra={
            "event_id": event_id,
            "user_id": user_id,
            "message_id": request.message_id,
            "reward": request.reward,
            "skill_updated": skill_updated,
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
