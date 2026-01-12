"""
System Overview API Router

Provides aggregated system metrics for the Studio overview page.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
import time

from aico.core.logging import get_logger
from backend.api.system.dependencies import get_current_user, get_db_connection

logger = get_logger("backend.api.system")

router = APIRouter()

# Include new modular metrics router (InfluxDB-based, zero LibSQL dependencies)
from backend.api.metrics import router as metrics_router
router.include_router(metrics_router)

# Import shared start_time to ensure consistency across all endpoints
from backend.api.metrics.start_time import start_time


class SystemEvent(BaseModel):
    """System event entry"""
    timestamp: str = Field(..., description="Most recent occurrence timestamp")
    severity: str = Field(..., description="Event severity (error, warning, info)")
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    domain: str = Field(..., description="Event domain/source")
    count: int = Field(default=1, description="Number of occurrences")


class SystemOverviewResponse(BaseModel):
    """System overview metrics"""
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    uptime_formatted: str = Field(..., description="Formatted uptime (e.g., '3h 42m')")
    active_conversations: int = Field(..., description="Number of active conversations")
    active_goals: int = Field(..., description="Number of active goals")
    system_status: str = Field(..., description="Overall system status")
    recent_events: List[SystemEvent] = Field(default_factory=list, description="Recent system events")


def format_uptime(seconds: float) -> str:
    """Format uptime seconds to human-readable string"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


@router.get("/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> SystemOverviewResponse:
    """
    Get system overview metrics.
    
    Returns:
        - uptime: System uptime
        - active_conversations: Count of recent conversations
        - active_goals: Count of active goals from agency
        - system_status: Overall health status
    """
    from backend.api.system.profiler import PerformanceTimer
    timer = PerformanceTimer("get_system_overview")
    
    try:
        timer.start("auth_check")
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        timer.stop("auth_check")
        
        timer.start("uptime_calc")
        # Calculate uptime
        uptime_seconds = time.time() - start_time
        uptime_formatted = format_uptime(uptime_seconds)
        timer.stop("uptime_calc")
        
        timer.start("lmdb_conversation_scan")
        # Get active conversations count from working memory (LMDB)
        # Conversations are stored in LMDB, not in SQL tables
        active_conversations = 0
        try:
            from aico.ai import ai_registry
            memory_manager = ai_registry.get("memory")
            
            if memory_manager and hasattr(memory_manager, '_working_store'):
                working_store = memory_manager._working_store
                
                # Count unique conversation_ids from LMDB keys in last 24 hours
                from datetime import datetime, timedelta
                cutoff_time = datetime.utcnow() - timedelta(days=1)
                
                conversation_ids = set()
                db = working_store.dbs.get("session_memory")
                if db:
                    with working_store.env.begin(db=db) as txn:
                        cursor = txn.cursor()
                        for key_bytes, _ in cursor:
                            key_str = key_bytes.decode('utf-8')
                            # Key format: {conversation_id}:{timestamp}
                            if ':' in key_str:
                                conv_id, timestamp_str = key_str.split(':', 1)
                                try:
                                    msg_time = datetime.fromisoformat(timestamp_str.rstrip('Z'))
                                    if msg_time > cutoff_time:
                                        conversation_ids.add(conv_id)
                                except:
                                    pass
                
                active_conversations = len(conversation_ids)
        except Exception as e:
            logger.debug(f"Conversation count unavailable: {e}")
        timer.stop("lmdb_conversation_scan")
        
        timer.start("db_goals_query")
        # Get active goals count from agency_goals table
        active_goals = 0
        try:
            result = db_connection.execute(
                """
                SELECT COUNT(*) 
                FROM agency_goals 
                WHERE user_id = ? 
                AND status IN ('active', 'in_progress')
                """,
                [user_id]
            ).fetchone()
            active_goals = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Goals count unavailable: {e}")
        timer.stop("db_goals_query")
        
        # Recent events from logs removed - system_logs table no longer exists
        # Logs now stored in InfluxDB - use admin API /logs endpoint for log queries
        recent_events = []
        
        timer.start("status_calculation")
        # Determine system status based on recent errors
        error_count = sum(1 for event in recent_events if event.severity == 'error')
        if error_count >= 3:
            system_status = "degraded"
        elif error_count > 0:
            system_status = "attention"
        else:
            system_status = "ok"
        timer.stop("status_calculation")
        
        timer.start("response_construction")
        response = SystemOverviewResponse(
            uptime_seconds=uptime_seconds,
            uptime_formatted=uptime_formatted,
            active_conversations=active_conversations,
            active_goals=active_goals,
            system_status=system_status,
            recent_events=recent_events
        )
        timer.stop("response_construction")
        
        timer.report(log_threshold_ms=500)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system overview: {str(e)}"
        )
