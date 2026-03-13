"""
AMS (Adaptive Memory System) API Router

REST endpoints for AMS statistics, consolidation status, behavioral learning,
user preferences, and feedback analytics.

Follows AICO architectural patterns:
- Message-driven design
- Modular, single-responsibility endpoints
- Proper error handling and logging
- User authentication via dependencies
"""

from typing import Annotated, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta, timezone
import json
import uuid

from aico.core.logging import get_logger
from gateway.api.dependencies import get_current_user
from aico.common.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

from .schemas import (
    ConsolidationStatusResponse,
    ConsolidationSessionResponse,
    BehavioralLearningStatsResponse,
    BehavioralFeedbackSubmitRequest,
    BehavioralFeedbackSubmitResponse,
    SkillInfoResponse,
    UserPreferencesResponse,
    PreferenceDimensionResponse,
    FeedbackStatsResponse,
    RecentFeedbackResponse,
    AMSStatsResponse,
    SkillDetailResponse,
    SkillOverviewResponse,
    MemoryMetricsSnapshot,
    MemoryGrowthStats,
    MemoryEvolutionResponse,
)
from . import router_extensions

logger = get_logger("gateway.api.ams")

router = APIRouter(prefix="/ams", tags=["ams"])
behavioral_router = APIRouter(tags=["behavioral"])


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_consolidation_status(uow: UnitOfWork, user_id: str) -> ConsolidationStatusResponse:
    """
    Get consolidation engine status from database.
    
    Queries ams_consolidation_state table for last run info and schedule.
    """
    try:
        # Get last consolidation state from repository
        states = await uow.ams_consolidation_state.list(limit=1)
        
        state_row = states[0] if states else None
        state_json = state_row.state_json if state_row and isinstance(state_row.state_json, dict) else {}
        last_session = None
        last_run = None
        
        if state_row:
            try:
                state_data = json.loads(state_row.state_json) if isinstance(state_row.state_json, str) else state_row.state_json
                
                # Extract session data from JSON
                messages_processed = state_data.get("messages_processed", 0)
                duration = state_data.get("duration_seconds", 0)
                completed_at = state_data.get("last_consolidated_at", state_row.updated_at.isoformat() if hasattr(state_row.updated_at, 'isoformat') else state_row.updated_at)
                
                # Create session response
                last_session = ConsolidationSessionResponse(
                    experiences_replayed=messages_processed,
                    facts_consolidated=0,  # Not tracked in current schema
                    graph_updates={
                        "entities": 0,  # Not tracked in current schema
                        "relationships": 0,  # Not tracked in current schema
                    },
                    duration_seconds=int(duration),
                    success=state_data.get("status") == "completed",
                    completed_at=completed_at,
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse consolidation state JSON: {e}")
        
            # Calculate time since last run
            if last_session and last_session.completed_at:
                try:
                    completed = datetime.fromisoformat(last_session.completed_at.replace('Z', '+00:00'))
                    delta = datetime.now(timezone.utc) - completed
                    
                    if delta.total_seconds() < 3600:
                        minutes = int(delta.total_seconds() / 60)
                        last_run = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                    elif delta.total_seconds() < 86400:
                        hours = int(delta.total_seconds() / 3600)
                        last_run = f"{hours} hour{'s' if hours != 1 else ''} ago"
                    else:
                        days = int(delta.total_seconds() / 86400)
                        last_run = f"{days} day{'s' if days != 1 else ''} ago"
                except Exception as e:
                    logger.warning(f"Failed to parse completed_at timestamp: {e}")
                    last_run = None
        
        # Get current cycle day (based on actual date progression)
        # Use day of year modulo 7 to ensure consistent daily progression
        from datetime import datetime
        current_date = datetime.now(timezone.utc)
        day_of_year = current_date.timetuple().tm_yday
        current_cycle_day = (day_of_year % 7) + 1
        
        next_scheduled = str(state_json.get("next_scheduled") or "unknown")
        
        # Check if consolidation is currently running
        user_states = await uow.ams_consolidation_state.list(filters={"user_id": user_id}, limit=1)
        
        current_status = "idle"
        if str(state_json.get("status") or "").lower() == "running":
            current_status = "running"
        elif state_row:
            current_status = "idle"
        else:
            current_status = "scheduled"
        
        return ConsolidationStatusResponse(
            last_run=last_run,
            next_scheduled=next_scheduled,
            current_cycle_day=current_cycle_day,
            total_cycle_days=7,
            status=current_status,
            last_session=last_session,
        )
        
    except (RuntimeError, ValueError) as e:
        logger.warning(f"AMS consolidation tables not found: {e}")
        raise


async def _get_behavioral_learning_stats(uow: UnitOfWork, user_id: str) -> BehavioralLearningStatsResponse:
    """
    Get behavioral learning statistics from database.
    
    Queries ams_behavioral_skills and ams_behavioral_feedback tables.
    """
    try:
        # Get total active skills
        skill_confidences = await uow.user_skill_confidence.list(filters={"user_id": user_id}, limit=10000)
        active_skills = len(set(sc.skill_id for sc in skill_confidences))
        
        # Get total feedback received
        all_feedback = await uow.ams_behavioral_feedback.list(filters={"user_id": user_id}, limit=10000)
        total_feedback = len(all_feedback)
        
        logger.info(f"📊 [AMS_DEBUG] Total feedback count for user {user_id}: {total_feedback}")
        
        # Get average confidence (convert from 0.0-1.0 to 0-100 percentage)
        if skill_confidences:
            avg_conf = sum(sc.confidence_score for sc in skill_confidences) / len(skill_confidences)
            avg_confidence = avg_conf * 100
        else:
            avg_confidence = 0.0
        
        # Get top 5 skills
        skills_dict = {}
        behavioral_skills = await uow.ams_behavioral_skills.list(limit=10000)
        skills_by_id = {s.skill_id: s.skill_name for s in behavioral_skills}
        
        # Sort by confidence and take top 5
        sorted_skills = sorted(skill_confidences, key=lambda x: x.confidence_score, reverse=True)[:5]
        
        top_skills = []
        for sc in sorted_skills:
            # Get last feedback for this skill
            skill_feedback = [f for f in all_feedback if f.skill_id == sc.skill_id]
            skill_feedback.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min, reverse=True)
            
            last_feedback = None
            if skill_feedback:
                reward = skill_feedback[0].reward
                if reward > 0:
                    last_feedback = "positive"
                elif reward < 0:
                    last_feedback = "negative"
                else:
                    last_feedback = "neutral"
            
            top_skills.append(
                SkillInfoResponse(
                    skill_id=sc.skill_id,
                    skill_name=skills_by_id.get(sc.skill_id, sc.skill_id),
                    confidence=sc.confidence_score * 100,  # Convert to percentage
                    last_feedback=last_feedback,
                    last_updated=sc.last_updated_at.isoformat() if hasattr(sc.last_updated_at, 'isoformat') else sc.last_updated_at
                )
            )     # Determine learning rate based on recent feedback
        learning_rate = "No feedback yet"
        if total_feedback > 0:
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_feedback = sum(1 for f in all_feedback if f.timestamp and f.timestamp > seven_days_ago)
            
            if recent_feedback > 10:
                learning_rate = "Adapting"
            elif recent_feedback > 5:
                learning_rate = "Learning"
            else:
                learning_rate = "Stable"
        
        # Generate recent learning insights
        insights = []
        if total_feedback > 0 and sorted_skills:
            # Get most improved skill
            top_skill_name = skills_by_id.get(sorted_skills[0].skill_id, sorted_skills[0].skill_id)
            insights.append(f"Learned: {top_skill_name} performing well")
        
        # Only show insights if we have actual data to base them on
        if not insights:
            insights = []
        
        return BehavioralLearningStatsResponse(
            active_skills=active_skills,
            total_feedback_received=total_feedback,
            learning_rate=learning_rate,
            average_confidence=avg_confidence,
            top_skills=top_skills,
            recent_learning_insights=insights[:3],
        )
        
    except (RuntimeError, ValueError) as e:
        logger.warning(f"AMS behavioral learning tables not found: {e}")
        raise


async def _get_user_preferences(uow: UnitOfWork, user_id: str) -> UserPreferencesResponse:
    """
    Get user preference profile from database.
    
    Queries context_preference_vectors table for preference dimensions.
    """
    try:
        # Dimension names for the 16-dimensional preference vector
        DIMENSION_NAMES = [
            "verbosity",
            "formality",
            "technical_depth",
            "proactivity",
            "emotional_expression",
            "structure",
            "explanation_depth",
            "example_usage",
            "question_asking",
            "reassurance_level",
            "directness",
            "enthusiasm",
            "patience",
            "creativity",
            "reserved_1",
            "reserved_2"
        ]
        
        dimensions = []
        insights = []
        
        # Get all preference vectors for this user across context buckets
        pref_vectors = await uow.ams_context_preference_vectors.list(filters={"user_id": user_id}, limit=1000)
        pref_vectors.sort(key=lambda p: p.last_updated_at if p.last_updated_at else datetime.min, reverse=True)
        
        if pref_vectors:
            # Use the most recently updated context bucket as representative
            most_recent = pref_vectors[0]
            dimensions = json.loads(most_recent.dimensions) if isinstance(most_recent.dimensions, str) else most_recent.dimensions
            
            # Create dimension responses
            dimension_values = dimensions  # Use parsed dimensions
            for i, name in enumerate(DIMENSION_NAMES):
                if i < len(dimension_values):
                    value = dimension_values[i]
                    
                    # Generate human-readable label based on value
                    if name == "verbosity":
                        label = "Concise" if value < 0.4 else "Balanced" if value < 0.7 else "Verbose"
                    elif name == "formality":
                        label = "Casual" if value < 0.4 else "Balanced" if value < 0.7 else "Formal"
                    elif name == "technical_depth":
                        label = "Simple" if value < 0.4 else "Moderate" if value < 0.7 else "Technical"
                    elif name == "proactivity":
                        label = "Reactive" if value < 0.4 else "Balanced" if value < 0.7 else "Proactive"
                    elif name == "emotional_expression":
                        label = "Reserved" if value < 0.4 else "Balanced" if value < 0.7 else "Expressive"
                    elif name == "structure":
                        label = "Flexible" if value < 0.4 else "Balanced" if value < 0.7 else "Structured"
                    elif name == "explanation_depth":
                        label = "Brief" if value < 0.4 else "Moderate" if value < 0.7 else "Detailed"
                    elif name == "example_usage":
                        label = "Few" if value < 0.4 else "Some" if value < 0.7 else "Many"
                    elif name == "directness":
                        label = "Indirect" if value < 0.4 else "Balanced" if value < 0.7 else "Direct"
                    elif name.startswith("reserved_"):
                        continue  # Skip reserved dimensions
                    else:
                        label = "Low" if value < 0.4 else "Moderate" if value < 0.7 else "High"
                    
                    # Only add non-reserved dimensions that have been learned (not at default 0.5)
                    if not name.startswith("reserved_") and abs(value - 0.5) > 0.05:
                        dimensions.append(PreferenceDimensionResponse(
                            name=name.replace("_", " ").title(),
                            value=value,
                            label=label,
                        ))
            
            # Generate insights
            learned_dims = sum(1 for d in dimensions if abs(d.value - 0.5) > 0.05)
            if learned_dims > 0:
                insights.append(f"{learned_dims} preference dimensions learned")
            
            if most_recent.context_bucket:
                insights.append(f"Learning from context bucket {most_recent.context_bucket}")
            
            if len(pref_vectors) > 1:
                insights.append(f"Tracking preferences across {len(pref_vectors)} contexts")
        else:
            # No preferences learned yet - check if we have feedback to learn from
            feedback_list = await uow.ams_behavioral_feedback.list(filters={"user_id": user_id}, limit=1)
            feedback_count = len(feedback_list)
            
            if feedback_count > 0:
                insights.append(f"Learning from {feedback_count} feedback events")
            else:
                insights.append("No preferences learned yet")
        
        context_bucket_count = len(
            {
                str(getattr(vector, "context_bucket", "") or "")
                for vector in pref_vectors
                if getattr(vector, "context_bucket", None) is not None
            }
        )

        return UserPreferencesResponse(
            dimensions=dimensions,
            context_buckets=context_bucket_count,
            insights=insights,
        )
        
    except (RuntimeError, ValueError) as e:
        logger.warning(f"AMS user preferences tables not found: {e}")
        raise


async def _get_feedback_stats(uow: UnitOfWork, user_id: str) -> FeedbackStatsResponse:
    """
    Get feedback statistics from database.
    
    Queries ams_behavioral_feedback table.
    """
    try:
        # Get all feedback for this user
        all_feedback = await uow.ams_behavioral_feedback.list(filters={"user_id": user_id}, limit=10000)
        
        # Calculate counts
        total = len(all_feedback)
        positive = sum(1 for f in all_feedback if f.reward > 0)
        negative = sum(1 for f in all_feedback if f.reward < 0)
        neutral = sum(1 for f in all_feedback if f.reward == 0)
        
        # Calculate response rate using actual message count from system_events
        response_rate = 0.0
        if total > 0:
            # Get system events for this user
            system_events = await uow.system_events.list(filters={"user_id": user_id}, limit=10000)
            conversation_events = [e for e in system_events if e.message_type and 'conversation/' in e.message_type]
            total_messages = len(conversation_events)
            
            if total_messages > 0:
                response_rate = (total / total_messages) * 100
            else:
                response_rate = 0.0
        
        # Get recent feedback (last 3)
        sorted_feedback = sorted(all_feedback, key=lambda f: f.timestamp if f.timestamp else datetime.min, reverse=True)[:3]
        
        # Get skill names
        behavioral_skills = await uow.ams_behavioral_skills.list(limit=10000)
        skills_by_id = {s.skill_id: s.skill_name for s in behavioral_skills}
        
        recent_feedback = []
        for feedback in sorted_feedback:
            try:
                if feedback.timestamp:
                    if isinstance(feedback.timestamp, str):
                        timestamp = datetime.fromisoformat(feedback.timestamp.replace('Z', '+00:00'))
                    else:
                        timestamp = feedback.timestamp
                    delta = datetime.now(timezone.utc) - timestamp
                    
                    if delta.total_seconds() < 3600:
                        time_str = f"{int(delta.total_seconds() / 60)} minutes ago"
                    elif delta.total_seconds() < 86400:
                        time_str = f"{int(delta.total_seconds() / 3600)} hours ago"
                    else:
                        time_str = f"{int(delta.total_seconds() / 86400)} days ago"
                else:
                    time_str = "Recently"
            except:
                time_str = "Recently"
            
            message = feedback.free_text if feedback.free_text else "Feedback received"
            skill = skills_by_id.get(feedback.skill_id, "General")
            reward = feedback.reward
            
            feedback_type = "positive" if reward > 0 else "negative" if reward < 0 else "neutral"
            
            recent_feedback.append(RecentFeedbackResponse(
                time=time_str,
                message=message,
                skill=skill,
                type=feedback_type,
            ))
        
        return FeedbackStatsResponse(
            total=total,
            positive=positive,
            negative=negative,
            neutral=neutral,
            response_rate=response_rate,
            recent_feedback=recent_feedback,
        )
        
    except (RuntimeError, ValueError) as e:
        logger.warning(f"AMS consolidation tables not found: {e}")
        raise


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/consolidation/status", response_model=ConsolidationStatusResponse)
async def get_consolidation_status(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ConsolidationStatusResponse:
    """
    Get current consolidation engine status.
    
    Returns information about last consolidation run, next scheduled run,
    current position in 7-day rotation cycle, and last session statistics.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching consolidation status", extra={"user_id": user_id})
    
    try:
        status = await _get_consolidation_status(uow, user_id)
        logger.info("📊 [AMS] ✅ Consolidation status retrieved", extra={
            "user_id": user_id,
            "status": status.status,
            "cycle_day": status.current_cycle_day,
        })
        return status
    except Exception as e:
        logger.error(f"Failed to get consolidation status: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve consolidation status: {str(e)}"
        )


@router.get("/behavioral/stats", response_model=BehavioralLearningStatsResponse)
async def get_behavioral_learning_stats(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> BehavioralLearningStatsResponse:
    """
    Get behavioral learning statistics.
    
    Returns active skills count, feedback received, learning rate,
    average confidence, top performing skills, and recent insights.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching behavioral learning stats", extra={"user_id": user_id})
    
    try:
        stats = await _get_behavioral_learning_stats(uow, user_id)
        logger.info("📊 [AMS] ✅ Behavioral learning stats retrieved", extra={
            "user_id": user_id,
            "active_skills": stats.active_skills,
            "total_feedback": stats.total_feedback_received,
        })
        return stats
    except Exception as e:
        logger.error(f"Failed to get behavioral learning stats: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve behavioral learning stats: {str(e)}"
        )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserPreferencesResponse:
    """
    Get user preference profile.
    
    Returns preference dimensions (verbosity, formality, technical depth, etc.),
    context bucket count, and context-specific insights.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching user preferences", extra={"user_id": user_id})
    
    try:
        preferences = await _get_user_preferences(uow, user_id)
        logger.info("📊 [AMS] ✅ User preferences retrieved", extra={
            "user_id": user_id,
            "dimensions": len(preferences.dimensions),
        })
        return preferences
    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user preferences: {str(e)}"
        )


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> FeedbackStatsResponse:
    """
    Get feedback statistics.
    
    Returns total feedback count, positive/negative/neutral breakdown,
    response rate, and recent feedback events.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching feedback stats", extra={"user_id": user_id})
    
    try:
        stats = await _get_feedback_stats(uow, user_id)
        logger.info("📊 [AMS] ✅ Feedback stats retrieved", extra={
            "user_id": user_id,
            "total_feedback": stats.total,
            "positive": stats.positive,
            "negative": stats.negative,
        })
        return stats
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback stats: {str(e)}"
        )


@behavioral_router.post("/behavioral/feedback", response_model=BehavioralFeedbackSubmitResponse)
async def submit_behavioral_feedback(
    payload: BehavioralFeedbackSubmitRequest,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> BehavioralFeedbackSubmitResponse:
    user_id = user.get("user_uuid")

    try:
        from aico.data.ams.models import BehavioralFeedback

        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=user_id,
            message_id=payload.message_id,
            reward=payload.reward,
            reason=payload.reason,
            timestamp=datetime.now(timezone.utc),
            free_text=payload.free_text,
        )
        await uow.ams_behavioral_feedback.create(feedback)
        await uow.commit()
        return BehavioralFeedbackSubmitResponse(
            event_id=feedback.feedback_id,
            skill_updated=False,
            new_confidence=None,
        )
    except Exception as e:
        logger.error(f"Failed to submit behavioral feedback: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit behavioral feedback: {str(e)}"
        )


@router.get("/stats", response_model=AMSStatsResponse)
async def get_ams_stats(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> AMSStatsResponse:
    """
    Get complete AMS statistics.
    
    Returns all AMS metrics in a single response: consolidation status,
    behavioral learning stats, user preferences, and feedback statistics.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching complete AMS stats", extra={"user_id": user_id})
    
    try:
        consolidation = await _get_consolidation_status(uow, user_id)
        behavioral_learning = await _get_behavioral_learning_stats(uow, user_id)
        user_preferences = await _get_user_preferences(uow, user_id)
        feedback = await _get_feedback_stats(uow, user_id)
        
        stats = AMSStatsResponse(
            consolidation=consolidation,
            behavioral_learning=behavioral_learning,
            user_preferences=user_preferences,
            feedback=feedback,
        )
        
        logger.info("📊 [AMS] ✅ Complete AMS stats retrieved", extra={"user_id": user_id})
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get AMS stats: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AMS stats: {str(e)}"
        )


@router.get("/skills/overview", response_model=SkillOverviewResponse)
async def get_skills_overview(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> SkillOverviewResponse:
    """
    Get comprehensive overview of all available skills with usage data.
    
    Returns complete skill inventory including skill details, confidence scores,
    usage counts, feedback statistics, and activity status.
    
    Note: This endpoint uses router_extensions which may still need migration.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching skills overview", extra={"user_id": user_id})
    
    try:
        overview = await router_extensions.get_skill_overview(user_id)
        logger.info("📊 [AMS] ✅ Skills overview retrieved", extra={
            "user_id": user_id,
        })
        return overview
    except Exception as e:
        logger.error(f"Failed to get skills overview: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve skills overview: {str(e)}"
        )


@router.get("/memory/evolution", response_model=MemoryEvolutionResponse)
async def get_memory_evolution(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> MemoryEvolutionResponse:
    """
    Get memory evolution metrics showing how memory grows over time.
    
    Returns current memory state, growth statistics for 7-day and 30-day periods,
    historical snapshots, and insights about memory development.
    
    Note: This endpoint uses router_extensions which may still need migration.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching memory evolution", extra={"user_id": user_id})
    
    try:
        evolution = await router_extensions.get_memory_evolution(user_id)
        logger.info("📊 [AMS] ✅ Memory evolution retrieved", extra={
            "user_id": user_id,
        })
        return evolution
    except Exception as e:
        logger.error(f"Failed to get memory evolution: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory evolution: {str(e)}"
        )
