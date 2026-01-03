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
from datetime import datetime, timedelta
import sqlite3

from aico.core.logging import get_logger
from backend.api.conversation.dependencies import get_current_user
from backend.core.lifecycle_manager import get_database

from .schemas import (
    ConsolidationStatusResponse,
    ConsolidationSessionResponse,
    BehavioralLearningStatsResponse,
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

logger = get_logger("backend", "api.ams")

router = APIRouter(prefix="/ams", tags=["ams"])


# ============================================================================
# Helper Functions
# ============================================================================

def _get_consolidation_status(db: sqlite3.Connection, user_id: str) -> ConsolidationStatusResponse:
    """
    Get consolidation engine status from database.
    
    Queries ams_consolidation_state table for last run info and schedule.
    """
    try:
        # Get last consolidation state from JSON
        cursor = db.execute("""
            SELECT state_json, updated_at
            FROM ams_consolidation_state
            WHERE id LIKE 'consolidation_%'
            ORDER BY updated_at DESC
            LIMIT 1
        """, ())
        
        state_row = cursor.fetchone()
        last_session = None
        last_run = None
        
        if state_row:
            import json
            try:
                state_data = json.loads(state_row[0])
                
                # Extract session data from JSON
                messages_processed = state_data.get("messages_processed", 0)
                duration = state_data.get("duration_seconds", 0)
                completed_at = state_data.get("last_consolidated_at", state_row[1])
                
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
                    delta = datetime.utcnow() - completed
                    
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
                    last_run = "Unknown"
        
        # Get current cycle day (based on actual date progression)
        # Use day of year modulo 7 to ensure consistent daily progression
        from datetime import datetime
        current_date = datetime.utcnow()
        day_of_year = current_date.timetuple().tm_yday
        current_cycle_day = (day_of_year % 7) + 1
        
        # Next scheduled is always 2 AM (configurable in scheduler)
        next_scheduled = "Tonight at 2:00 AM"
        
        # Check if consolidation is currently running
        cursor = db.execute("""
            SELECT status FROM ams_consolidation_state
            WHERE user_id = ?
        """, (user_id,))
        
        state_row = cursor.fetchone()
        current_status = "idle"
        if state_row and state_row[0] == "running":
            current_status = "running"
        elif last_session_row:
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
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        # Tables don't exist yet - return default values
        logger.warning(f"AMS consolidation tables not found: {e}")
        return ConsolidationStatusResponse(
            last_run=None,
            next_scheduled="Tonight at 2:00 AM",
            current_cycle_day=1,
            total_cycle_days=7,
            status="scheduled",
            last_session=None,
        )


def _get_behavioral_learning_stats(db: sqlite3.Connection, user_id: str) -> BehavioralLearningStatsResponse:
    """
    Get behavioral learning statistics from database.
    
    Queries ams_behavioral_skills and ams_behavioral_feedback tables.
    """
    try:
        # Get total active skills
        cursor = db.execute("""
            SELECT COUNT(DISTINCT skill_id)
            FROM user_skill_confidence
            WHERE user_id = ?
        """, (user_id,))
        active_skills = cursor.fetchone()[0] or 0
        
        # Get total feedback received
        cursor = db.execute("""
            SELECT COUNT(*)
            FROM ams_behavioral_feedback
            WHERE user_id = ?
        """, (user_id,))
        total_feedback = cursor.fetchone()[0] or 0
        
        logger.info(f"📊 [AMS_DEBUG] Total feedback count for user {user_id}: {total_feedback}")
        
        # Get average confidence (convert from 0.0-1.0 to 0-100 percentage)
        cursor = db.execute("""
            SELECT AVG(confidence_score)
            FROM user_skill_confidence
            WHERE user_id = ?
        """, (user_id,))
        avg_confidence_row = cursor.fetchone()
        avg_confidence = (avg_confidence_row[0] * 100) if avg_confidence_row and avg_confidence_row[0] else 50.0
        
        # Get top 5 skills
        cursor = db.execute("""
            SELECT 
                usc.skill_id,
                s.skill_name,
                usc.confidence_score,
                usc.usage_count,
                usc.last_used_at
            FROM user_skill_confidence usc
            JOIN ams_behavioral_skills s ON usc.skill_id = s.skill_id
            WHERE usc.user_id = ?
            ORDER BY usc.confidence_score DESC, usc.usage_count DESC
            LIMIT 5
        """, (user_id,))
        
        top_skills = []
        for row in cursor.fetchall():
            # Get last feedback for this skill
            feedback_cursor = db.execute("""
                SELECT reward
                FROM ams_behavioral_feedback
                WHERE user_id = ? AND skill_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id, row[0]))
            
            feedback_row = feedback_cursor.fetchone()
            last_feedback = None
            if feedback_row:
                reward = feedback_row[0]
                if reward > 0:
                    last_feedback = "positive"
                elif reward < 0:
                    last_feedback = "negative"
                else:
                    last_feedback = "neutral"
            
            top_skills.append(SkillInfoResponse(
                skill_id=row[0],
                name=row[1],
                confidence=row[2] * 100,  # Convert from 0.0-1.0 to 0-100 percentage
                usage_count=row[3] or 0,
                last_feedback=last_feedback,
                last_used=row[4],
            ))
        
        # Determine learning rate based on recent feedback
        learning_rate = "Stable"
        if total_feedback > 0:
            cursor = db.execute("""
                SELECT COUNT(*)
                FROM ams_behavioral_feedback
                WHERE user_id = ? 
                AND timestamp > datetime('now', '-7 days')
            """, (user_id,))
            recent_feedback = cursor.fetchone()[0] or 0
            
            if recent_feedback > 10:
                learning_rate = "Adapting"
            elif recent_feedback > 5:
                learning_rate = "Learning"
        
        # Generate recent learning insights
        insights = []
        if total_feedback > 0:
            # Get most improved skill
            cursor = db.execute("""
                SELECT s.skill_name
                FROM user_skill_confidence usc
                JOIN ams_behavioral_skills s ON usc.skill_id = s.skill_id
                WHERE usc.user_id = ?
                ORDER BY usc.confidence_score DESC
                LIMIT 1
            """, (user_id,))
            top_skill_row = cursor.fetchone()
            if top_skill_row:
                insights.append(f"Learned: {top_skill_row[0]} performing well")
        
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
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        logger.warning(f"AMS behavioral learning tables not found: {e}")
        return BehavioralLearningStatsResponse(
            active_skills=0,
            total_feedback_received=0,
            learning_rate="Stable",
            average_confidence=0.0,
            top_skills=[],
            recent_learning_insights=[],
        )


def _get_user_preferences(db: sqlite3.Connection, user_id: str) -> UserPreferencesResponse:
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
        cursor = db.execute("""
            SELECT context_bucket, dimensions, last_updated_at
            FROM ams_context_preference_vectors
            WHERE user_id = ?
            ORDER BY last_updated_at DESC
        """, (user_id,))
        
        pref_rows = cursor.fetchall()
        
        if pref_rows:
            # Use the most recently updated context bucket as representative
            import json
            most_recent = pref_rows[0]
            context_bucket = most_recent[0]
            dimension_values = json.loads(most_recent[1])
            
            # Create dimension responses
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
            
            insights.append(f"Learning from context bucket {context_bucket}")
            
            if len(pref_rows) > 1:
                insights.append(f"Tracking preferences across {len(pref_rows)} contexts")
        else:
            # No preferences learned yet - check if we have feedback to learn from
            cursor = db.execute("""
                SELECT COUNT(*) FROM ams_behavioral_feedback WHERE user_id = ?
            """, (user_id,))
            feedback_count = cursor.fetchone()[0] or 0
            
            if feedback_count > 0:
                insights.append(f"Learning from {feedback_count} feedback events")
            else:
                insights.append("No preferences learned yet")
        
        return UserPreferencesResponse(
            dimensions=dimensions,
            context_buckets=100,
            insights=insights,
        )
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        logger.warning(f"AMS user preferences tables not found: {e}")
        return UserPreferencesResponse(
            dimensions=[],
            context_buckets=0,
            insights=[],
        )


def _get_feedback_stats(db: sqlite3.Connection, user_id: str) -> FeedbackStatsResponse:
    """
    Get feedback statistics from database.
    
    Queries ams_behavioral_feedback table.
    """
    try:
        # Get total feedback counts
        cursor = db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN reward > 0 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN reward < 0 THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN reward = 0 THEN 1 ELSE 0 END) as neutral
            FROM ams_behavioral_feedback
            WHERE user_id = ?
        """, (user_id,))
        
        stats_row = cursor.fetchone()
        total = stats_row[0] or 0
        positive = stats_row[1] or 0
        negative = stats_row[2] or 0
        neutral = stats_row[3] or 0
        
        # Calculate response rate using actual message count from system_events
        response_rate = 0.0
        if total > 0:
            # Get actual AI response count from system_events
            cursor = db.execute("""
                SELECT COUNT(*) 
                FROM system_events 
                WHERE message_type LIKE 'conversation/%'
                AND json_extract(metadata, '$.user_id') = ?
            """, (user_id,))
            total_messages = cursor.fetchone()[0] or 0
            
            if total_messages > 0:
                response_rate = (total / total_messages) * 100
            else:
                response_rate = 0.0
        
        # Get recent feedback
        cursor = db.execute("""
            SELECT 
                f.timestamp,
                f.free_text,
                s.skill_name,
                f.reward
            FROM ams_behavioral_feedback f
            LEFT JOIN ams_behavioral_skills s ON f.skill_id = s.skill_id
            WHERE f.user_id = ?
            ORDER BY f.timestamp DESC
            LIMIT 3
        """, (user_id,))
        
        recent_feedback = []
        for row in cursor.fetchall():
            try:
                timestamp = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                delta = datetime.utcnow() - timestamp
                
                if delta.total_seconds() < 3600:
                    time_str = f"{int(delta.total_seconds() / 60)} minutes ago"
                elif delta.total_seconds() < 86400:
                    time_str = f"{int(delta.total_seconds() / 3600)} hours ago"
                else:
                    time_str = f"{int(delta.total_seconds() / 86400)} days ago"
            except:
                time_str = "Recently"
            
            message = row[1] if row[1] else "Feedback received"
            skill = row[2] if row[2] else "General"
            reward = row[3]
            
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
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        logger.warning(f"AMS feedback tables not found: {e}")
        return FeedbackStatsResponse(
            total=0,
            positive=0,
            negative=0,
            neutral=0,
            response_rate=0.0,
            recent_feedback=[],
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/consolidation/status", response_model=ConsolidationStatusResponse)
async def get_consolidation_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: sqlite3.Connection = Depends(get_database),
) -> ConsolidationStatusResponse:
    """
    Get current consolidation engine status.
    
    Returns information about last consolidation run, next scheduled run,
    current position in 7-day rotation cycle, and last session statistics.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching consolidation status", extra={"user_id": user_id})
    
    try:
        status = _get_consolidation_status(db, user_id)
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
    db: sqlite3.Connection = Depends(get_database),
) -> BehavioralLearningStatsResponse:
    """
    Get behavioral learning statistics.
    
    Returns active skills count, feedback received, learning rate,
    average confidence, top performing skills, and recent insights.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching behavioral learning stats", extra={"user_id": user_id})
    
    try:
        stats = _get_behavioral_learning_stats(db, user_id)
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
    db: sqlite3.Connection = Depends(get_database),
) -> UserPreferencesResponse:
    """
    Get user preference profile.
    
    Returns preference dimensions (verbosity, formality, technical depth, etc.),
    context bucket count, and context-specific insights.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching user preferences", extra={"user_id": user_id})
    
    try:
        preferences = _get_user_preferences(db, user_id)
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
    db: sqlite3.Connection = Depends(get_database),
) -> FeedbackStatsResponse:
    """
    Get feedback statistics.
    
    Returns total feedback count, positive/negative/neutral breakdown,
    response rate, and recent feedback events.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching feedback stats", extra={"user_id": user_id})
    
    try:
        stats = _get_feedback_stats(db, user_id)
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


@router.get("/stats", response_model=AMSStatsResponse)
async def get_ams_stats(
    user: Annotated[dict, Depends(get_current_user)],
    db: sqlite3.Connection = Depends(get_database),
) -> AMSStatsResponse:
    """
    Get complete AMS statistics.
    
    Returns all AMS metrics in a single response: consolidation status,
    behavioral learning stats, user preferences, and feedback statistics.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching complete AMS stats", extra={"user_id": user_id})
    
    try:
        consolidation = _get_consolidation_status(db, user_id)
        behavioral_learning = _get_behavioral_learning_stats(db, user_id)
        user_preferences = _get_user_preferences(db, user_id)
        feedback = _get_feedback_stats(db, user_id)
        
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
    db: sqlite3.Connection = Depends(get_database),
) -> SkillOverviewResponse:
    """
    Get comprehensive overview of all available skills with usage data.
    
    Returns complete skill inventory including skill details, confidence scores,
    usage counts, feedback statistics, and activity status.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching skills overview", extra={"user_id": user_id})
    
    try:
        from .router_extensions import get_skill_overview
        overview = get_skill_overview(db, user_id)
        logger.info("📊 [AMS] ✅ Skills overview retrieved", extra={
            "user_id": user_id,
            "total_skills": overview.total_skills,
            "active_skills": overview.active_skills,
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
    db: sqlite3.Connection = Depends(get_database),
) -> MemoryEvolutionResponse:
    """
    Get memory evolution metrics showing how memory grows over time.
    
    Returns current memory state, growth statistics for 7-day and 30-day periods,
    historical snapshots, and insights about memory development.
    """
    user_id = user.get("user_uuid")
    
    logger.info("📊 [AMS] Fetching memory evolution", extra={"user_id": user_id})
    
    try:
        from .router_extensions import get_memory_evolution as get_evolution
        evolution = get_evolution(db, user_id)
        logger.info("📊 [AMS] ✅ Memory evolution retrieved", extra={
            "user_id": user_id,
            "semantic_facts": evolution.current_metrics.semantic_facts_count,
            "kg_entities": evolution.current_metrics.knowledge_graph_entities,
        })
        return evolution
    except Exception as e:
        logger.error(f"Failed to get memory evolution: {e}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory evolution: {str(e)}"
        )
