"""
Curiosity Scan Scheduled Task

Periodically scans for curiosity opportunities and creates hobby goals.
Based on agency-component-curiosity-engine.md Section 4.4.
"""

from datetime import datetime
from typing import Any, Dict

from backend.tasks.base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger

logger = get_logger("backend", "tasks.curiosity_scan")


class CuriosityScanTask(BaseTask):
    """Scheduled task to scan for curiosity opportunities.
    
    Runs periodically to:
    1. Scan for curiosity opportunities using CuriosityEngine
    2. Generate IntrinsicSignals
    3. Create hobby goals for high-scoring signals
    
    From agency-component-curiosity-engine.md:
    - Runs every 6 hours
    - Respects lifecycle phases (prefers idle/sleep-like)
    - Creates agent-self/curiosity goals
    """
    
    task_id = "agency.curiosity_scan"
    description = "Scan for curiosity opportunities and generate hobby goals"
    
    # Schedule: Every 6 hours
    schedule = "0 */6 * * *"
    
    # Lifecycle awareness
    requires_idle = True  # Prefer to run when user is idle
    max_duration_seconds = 300  # 5 minutes max
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute curiosity scan.
        
        Args:
            context: Task execution context with services
            
        Returns:
            TaskResult with scan statistics
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("[CURIOSITY_SCAN] Starting curiosity scan")
            
            # Get required services from context
            curiosity_engine = context.get_service("curiosity_engine")
            agency_engine = context.get_service("agency_engine")
            
            if not curiosity_engine:
                logger.warning("[CURIOSITY_SCAN] CuriosityEngine not available, skipping")
                return TaskResult(
                    success=True,
                    message="CuriosityEngine not available",
                    metadata={"skipped": True},
                )
            
            if not agency_engine:
                logger.warning("[CURIOSITY_SCAN] AgencyEngine not available, skipping")
                return TaskResult(
                    success=True,
                    message="AgencyEngine not available",
                    metadata={"skipped": True},
                )
            
            # Get user ID from context
            user_id = context.get("user_id")
            if not user_id:
                logger.error("[CURIOSITY_SCAN] No user_id in context")
                return TaskResult(
                    success=False,
                    message="No user_id provided",
                )
            
            # Check lifecycle state (if available)
            lifecycle_state = context.get("lifecycle_state", "unknown")
            logger.debug(f"[CURIOSITY_SCAN] Lifecycle state: {lifecycle_state}")
            
            # Defer if user is active (not idle)
            if lifecycle_state == "active":
                logger.info("[CURIOSITY_SCAN] User active, deferring scan")
                return TaskResult(
                    success=True,
                    message="Deferred - user active",
                    metadata={"deferred": True, "reason": "user_active"},
                )
            
            # Scan for opportunities
            logger.info(f"[CURIOSITY_SCAN] Scanning for user {user_id}")
            signals = await curiosity_engine.scan_for_opportunities(
                user_id=user_id,
                max_signals=10,
            )
            
            logger.info(f"[CURIOSITY_SCAN] Found {len(signals)} curiosity signals")
            
            # Create goals from high-scoring signals
            goals_created = 0
            goals_failed = 0
            
            for signal in signals:
                # Only create goals for signals with score >= 0.5
                if signal.total_score < 0.5:
                    logger.debug(
                        f"[CURIOSITY_SCAN] Skipping low-score signal: "
                        f"{signal.topic} (score={signal.total_score:.2f})"
                    )
                    continue
                
                try:
                    goal, plan = await agency_engine.create_goal_from_curiosity_signal(
                        user_id=user_id,
                        signal=signal,
                        auto_plan=True,
                    )
                    
                    goals_created += 1
                    logger.info(
                        f"[CURIOSITY_SCAN] Created {signal.signal_type.value} goal: "
                        f"{goal.title} (score={signal.total_score:.2f})"
                    )
                    
                except Exception as e:
                    goals_failed += 1
                    logger.error(
                        f"[CURIOSITY_SCAN] Failed to create goal from signal "
                        f"{signal.signal_id}: {e}"
                    )
            
            # Calculate execution time
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Build result
            result = TaskResult(
                success=True,
                message=f"Scan complete: {goals_created} goals created",
                metadata={
                    "signals_found": len(signals),
                    "goals_created": goals_created,
                    "goals_failed": goals_failed,
                    "duration_seconds": duration,
                    "lifecycle_state": lifecycle_state,
                },
            )
            
            logger.info(
                f"[CURIOSITY_SCAN] Complete: {len(signals)} signals, "
                f"{goals_created} goals created, {duration:.1f}s"
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"[CURIOSITY_SCAN] Task failed: {e}", exc_info=True)
            
            return TaskResult(
                success=False,
                message=f"Curiosity scan failed: {str(e)}",
                metadata={
                    "duration_seconds": duration,
                    "error": str(e),
                },
            )
    
    async def should_run(self, context: TaskContext) -> bool:
        """Check if task should run based on lifecycle state.
        
        From agency-component-curiosity-engine.md Section 5.3:
        - Prefer idle or sleep-like phases
        - Avoid during active user interaction
        - Respect quiet hours
        
        Args:
            context: Task execution context
            
        Returns:
            True if task should run
        """
        try:
            # Check lifecycle state
            lifecycle_state = context.get("lifecycle_state", "unknown")
            
            # Prefer idle or sleep-like phases
            if lifecycle_state in ["idle", "sleep", "consolidation"]:
                return True
            
            # Allow during unknown state (fallback)
            if lifecycle_state == "unknown":
                logger.debug("[CURIOSITY_SCAN] Unknown lifecycle state, allowing run")
                return True
            
            # Defer during active interaction
            if lifecycle_state == "active":
                logger.debug("[CURIOSITY_SCAN] User active, deferring")
                return False
            
            # Check quiet hours (if configured)
            quiet_hours = context.get("quiet_hours", {})
            if quiet_hours.get("enabled", False):
                current_hour = datetime.utcnow().hour
                start_hour = quiet_hours.get("start_hour", 22)
                end_hour = quiet_hours.get("end_hour", 7)
                
                # Check if current time is in quiet hours
                if start_hour > end_hour:  # Crosses midnight
                    in_quiet_hours = current_hour >= start_hour or current_hour < end_hour
                else:
                    in_quiet_hours = start_hour <= current_hour < end_hour
                
                if in_quiet_hours:
                    logger.debug("[CURIOSITY_SCAN] In quiet hours, deferring")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"[CURIOSITY_SCAN] Error checking should_run: {e}")
            # Default to allowing run on error
            return True
