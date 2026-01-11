"""
Behavioral Learning API Router

REST endpoints for feedback submission and skill management.
"""

import uuid
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from aico.core.logging import get_logger
from backend.api.conversation.dependencies import get_current_user
from backend.core.lifecycle_manager import get_database
from aico.ai.memory.behavioral import SkillStore, FeedbackEvent, PreferenceManager

from .schemas import FeedbackRequest, FeedbackResponse

logger = get_logger("backend.api.behavioral")

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
        # Use skill_id from request (frontend should provide it if available)
        skill_id = request.skill_id
        
        # If no skill_id provided, look it up from ams_trajectories
        if not skill_id:
            logger.info("📊 [FEEDBACK] No skill_id provided, looking up from trajectory", extra={
                "message_id": request.message_id
            })
            
            # Look up skill_id from trajectory using message_id
            trajectory_row = db.execute(
                """SELECT selected_skill_id FROM ams_trajectories 
                   WHERE message_id = ? LIMIT 1""",
                (request.message_id,)
            ).fetchone()
            
            if trajectory_row and trajectory_row[0]:
                skill_id = trajectory_row[0]
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
        
        # Store feedback event in AMS behavioral feedback table (schema v36)
        db.execute(
            """INSERT INTO ams_behavioral_feedback (
                feedback_id, user_id, message_id, skill_id, reward,
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
            
            skill_store = SkillStore(db)
            
            # Update skill confidence
            new_confidence = await skill_store.update_confidence(
                user_id=user_id,
                skill_id=skill_id,
                reward=request.reward
            )
            skill_updated = True
            
            logger.info("📊 [FEEDBACK] ✅ Skill confidence updated", extra={
                "user_id": user_id,
                "skill_id": skill_id,
                "reward": request.reward,
                "new_confidence": new_confidence
            })
            
            # Update preference vector
            try:
                # Get skill details for preference update
                skill = await skill_store.get_skill(skill_id)
                
                if skill:
                    # Calculate context bucket from message metadata
                    # For now, use a simple hash-based bucketing
                    # TODO: Use actual conversation context (intent, sentiment, time_of_day)
                    context_bucket = hash(f"{user_id}_{request.message_id}") % 100
                    
                    logger.info("📊 [FEEDBACK] Updating preference vector", extra={
                        "user_id": user_id,
                        "context_bucket": context_bucket,
                        "skill_id": skill_id
                    })
                    
                    # Initialize PreferenceManager
                    pref_manager = PreferenceManager(
                        db_connection=db,
                        learning_rate=0.1  # Default learning rate
                    )
                    
                    # Update preference vector based on feedback
                    updated_pref = await pref_manager.update_from_feedback(
                        user_id=user_id,
                        context_bucket=context_bucket,
                        skill=skill,
                        reward=request.reward
                    )
                    
                    preference_updated = True
                    
                    logger.info("📊 [FEEDBACK] ✅ Preference vector updated", extra={
                        "user_id": user_id,
                        "context_bucket": context_bucket,
                        "dimensions_count": len(updated_pref.dimensions)
                    })
                else:
                    logger.warning("📊 [FEEDBACK] Skill not found for preference update", extra={
                        "skill_id": skill_id
                    })
                    
            except sqlite3.OperationalError as db_error:
                logger.error(f"📊 [FEEDBACK] CRITICAL: Database error updating preferences: {db_error}", extra={
                    "user_id": user_id,
                    "skill_id": skill_id,
                    "error_type": "OperationalError"
                })
                # Fail fast on database errors - don't silently continue
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error: preference table missing or inaccessible. Contact administrator."
                )
            except ValueError as val_error:
                logger.warning(f"📊 [FEEDBACK] Invalid preference data: {val_error}", extra={
                    "user_id": user_id,
                    "skill_id": skill_id
                })
                # Only swallow expected validation errors
                
        else:
            logger.info("📊 [FEEDBACK] Skipping skill confidence and preference updates", extra={
                "skill_id": skill_id,
                "reward": request.reward,
                "reason": "no_skill_id" if not skill_id else "neutral_reward"
            })
        
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
