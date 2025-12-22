"""
Proactive Conversation API Endpoints

Handles AICO-initiated conversation tracking and user responses.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from backend.api.conversation.dependencies import get_current_user
from aico.data.libsql import EncryptedLibSQLConnection
from aico.core.logging import get_logger

logger = get_logger("backend", "api.conversation.proactive")

router = APIRouter(prefix="/proactive", tags=["proactive_conversation"])


class InitiationResponse(BaseModel):
    """User response to proactive initiation"""
    initiation_id: str = Field(..., description="Initiation ID")
    response_type: str = Field(..., description="answered, dismissed, or deferred")
    response_text: Optional[str] = Field(None, description="User's response text if answered")
    engagement_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Engagement quality score")


class InitiationStatus(BaseModel):
    """Status of a proactive initiation"""
    initiation_id: str
    user_id: str
    conversation_id: str
    question: str
    initiated_at: str
    resolution_status: str
    resolved_at: Optional[str]
    user_response_time: Optional[int]
    engagement_score: Optional[float]


def get_db_connection(request: Request):
    """Get database connection from service container."""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    return container.get_service("database")


@router.get("/pending", response_model=list[InitiationStatus])
async def get_pending_initiations(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get all pending proactive initiations for current user.
    
    Returns initiations that are waiting for user response.
    Resilient to offline users - initiations persist until responded to.
    """
    try:
        user_id = current_user['user_uuid']
        db = get_db_connection(request)
        
        print(f"📋 [PROACTIVE_API] Fetching pending initiations for user {user_id[:8]}")
        logger.info(f"📋 [PROACTIVE_API] Fetching pending initiations for user {user_id}")
        
        cursor = db.execute(
            """SELECT initiation_id, user_id, conversation_id, question,
                      initiated_at, resolution_status, resolved_at,
                      user_response_time, engagement_score
               FROM conversation_initiations
               WHERE user_id = ? AND resolution_status = 'pending'
               ORDER BY initiated_at DESC""",
            (user_id,)
        )
        
        initiations = []
        for row in cursor.fetchall():
            initiations.append(InitiationStatus(
                initiation_id=row['initiation_id'],
                user_id=row['user_id'],
                conversation_id=row['conversation_id'],
                question=row['question'],
                initiated_at=row['initiated_at'],
                resolution_status=row['resolution_status'],
                resolved_at=row['resolved_at'],
                user_response_time=row['user_response_time'],
                engagement_score=row['engagement_score']
            ))
        
        print(f"📋 [PROACTIVE_API] ✅ Found {len(initiations)} pending initiations")
        logger.info(f"📋 [PROACTIVE_API] Returning {len(initiations)} pending initiations")
        
        return initiations
        
    except Exception as e:
        print(f"📋 [PROACTIVE_API] ❌ Error fetching pending initiations: {e}")
        logger.error(f"📋 [PROACTIVE_API] Error fetching pending initiations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending initiations: {str(e)}"
        )


@router.post("/respond")
async def respond_to_initiation(
    response: InitiationResponse,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Record user response to proactive initiation.
    
    Updates initiation status and triggers learning system update.
    """
    try:
        user_id = current_user['user_uuid']
        db = get_db_connection(request)
        
        print(f"📝 [PROACTIVE_API] Recording response to initiation {response.initiation_id[:8]}")
        logger.info(
            f"📝 [PROACTIVE_API] Recording response to initiation {response.initiation_id} "
            f"from user {user_id}"
        )
        
        # Verify initiation exists and belongs to user
        cursor = db.execute(
            """SELECT initiation_id, user_id, initiated_at, resolution_status, trigger_reason
               FROM conversation_initiations
               WHERE initiation_id = ?""",
            (response.initiation_id,)
        )
        
        initiation = cursor.fetchone()
        if not initiation:
            print(f"📝 [PROACTIVE_API] ⚠️ Initiation not found: {response.initiation_id[:8]}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiation not found"
            )
        
        if initiation['user_id'] != user_id:
            print(f"📝 [PROACTIVE_API] ⚠️ Unauthorized access attempt")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to respond to this initiation"
            )
        
        if initiation['resolution_status'] != 'pending':
            print(f"📝 [PROACTIVE_API] ⚠️ Initiation already resolved: {initiation['resolution_status']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Initiation already {initiation['resolution_status']}"
            )
        
        # Calculate response time
        initiated_at = datetime.fromisoformat(initiation['initiated_at'])
        if initiated_at.tzinfo is None:
            initiated_at = initiated_at.replace(tzinfo=timezone.utc)
        resolved_at = datetime.now(timezone.utc)
        response_time = int((resolved_at - initiated_at).total_seconds())
        
        # Update initiation status
        db.execute(
            """UPDATE conversation_initiations
               SET resolution_status = ?,
                   resolved_at = ?,
                   user_response_time = ?,
                   engagement_score = ?,
                   updated_at = ?
               WHERE initiation_id = ?""",
            (
                response.response_type,
                resolved_at.isoformat(),
                response_time,
                response.engagement_score,
                resolved_at.isoformat(),
                response.initiation_id
            )
        )
        db.commit()
        
        print(f"📝 [PROACTIVE_API] ✅ Updated initiation status to '{response.response_type}'")
        logger.info(
            f"📝 [PROACTIVE_API] Updated initiation {response.initiation_id} "
            f"status to '{response.response_type}', response_time={response_time}s"
        )
        
        # Trigger learning system update
        try:
            from aico.ai.agency.skills.communication.learning import ContextualBanditLearner
            from aico.ai.agency.skills.communication.learning import extract_contextual_features
            
            print(f"🎓 [PROACTIVE_API] Updating learning system...")
            
            # Extract context at time of response
            context = extract_contextual_features(db, user_id)
            
            # Determine strategy from trigger_reason
            trigger_reason = initiation['trigger_reason']
            strategy_id = None
            if 'strategy_' in trigger_reason:
                strategy_id = trigger_reason.split('strategy_')[1]
            
            if strategy_id:
                # Initialize bandit and update
                bandit = ContextualBanditLearner(db)
                bandit.update_from_outcome(
                    strategy_id=strategy_id,
                    context=context,
                    outcome=response.response_type,
                    response_time=float(response_time) if response.response_type == 'answered' else None
                )
                
                print(f"🎓 [PROACTIVE_API] ✅ Learning system updated for strategy {strategy_id}")
                logger.info(
                    f"🎓 [PROACTIVE_API] Updated bandit for strategy {strategy_id}, "
                    f"outcome={response.response_type}"
                )
            else:
                print(f"🎓 [PROACTIVE_API] ⚠️ No strategy ID found in trigger_reason")
                logger.warning(
                    f"🎓 [PROACTIVE_API] Could not extract strategy from trigger_reason: {trigger_reason}"
                )
            
        except Exception as learning_error:
            # Don't fail the response if learning update fails
            print(f"🎓 [PROACTIVE_API] ⚠️ Learning update failed: {learning_error}")
            logger.warning(
                f"🎓 [PROACTIVE_API] Failed to update learning system: {learning_error}"
            )
        
        return {
            "success": True,
            "message": f"Response recorded: {response.response_type}",
            "initiation_id": response.initiation_id,
            "response_time_seconds": response_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"📝 [PROACTIVE_API] ❌ Error recording response: {e}")
        logger.error(
            f"📝 [PROACTIVE_API] Error recording response: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record response: {str(e)}"
        )


@router.get("/history", response_model=list[InitiationStatus])
async def get_initiation_history(
    limit: int = 20,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get initiation history for current user.
    
    Returns recent initiations regardless of status.
    """
    try:
        user_id = current_user['user_uuid']
        db = get_db_connection(request)
        
        print(f"📜 [PROACTIVE_API] Fetching history for user {user_id[:8]}")
        logger.info(f"📜 [PROACTIVE_API] Fetching initiation history for user {user_id}")
        
        cursor = db.execute(
            """SELECT initiation_id, user_id, conversation_id, question,
                      initiated_at, resolution_status, resolved_at,
                      user_response_time, engagement_score
               FROM conversation_initiations
               WHERE user_id = ?
               ORDER BY initiated_at DESC
               LIMIT ?""",
            (user_id, limit)
        )
        
        initiations = []
        for row in cursor.fetchall():
            initiations.append(InitiationStatus(
                initiation_id=row['initiation_id'],
                user_id=row['user_id'],
                conversation_id=row['conversation_id'],
                question=row['question'],
                initiated_at=row['initiated_at'],
                resolution_status=row['resolution_status'],
                resolved_at=row['resolved_at'],
                user_response_time=row['user_response_time'],
                engagement_score=row['engagement_score']
            ))
        
        print(f"📜 [PROACTIVE_API] ✅ Returning {len(initiations)} historical initiations")
        logger.info(f"📜 [PROACTIVE_API] Returning {len(initiations)} historical initiations")
        
        return initiations
        
    except Exception as e:
        print(f"📜 [PROACTIVE_API] ❌ Error fetching history: {e}")
        logger.error(f"📜 [PROACTIVE_API] Error fetching history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )
