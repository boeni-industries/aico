"""
Curiosity Scan Scheduled Task

Periodically scans for curiosity opportunities and creates hobby goals.
Based on agency-component-curiosity-engine.md Section 4.4.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from .base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger
from aico.ai import ai_registry

# Defer logger initialization to avoid import-time errors
logger = None

def _get_logger():
    global logger
    if logger is None:
        logger = get_logger("backend.scheduler.tasks.curiosity_scan")
    return logger


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
    default_config = {
        "enabled": True,
        "schedule": "0 */6 * * *",  # Every 6 hours
        "description": "Scan for curiosity opportunities and generate hobby goals",
        "requires_idle": True,
        "max_duration_seconds": 300,
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute curiosity scan.
        
        Args:
            context: Task execution context with services
            
        Returns:
            TaskResult with scan statistics
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            _get_logger().info("[CURIOSITY_SCAN] Starting curiosity scan")
            
            # Get required services from AI registry
            curiosity_engine = ai_registry.get("curiosity")
            agency_engine = ai_registry.get("agency")
            
            if not curiosity_engine:
                _get_logger().warning("[CURIOSITY_SCAN] CuriosityEngine not available, skipping")
                return TaskResult(
                    success=True,
                    message="CuriosityEngine not available",
                    skipped=True,
                )
            
            if not agency_engine:
                _get_logger().warning("[CURIOSITY_SCAN] AgencyEngine not available, skipping")
                return TaskResult(
                    success=True,
                    message="AgencyEngine not available",
                    skipped=True,
                )
            
            # Get all active users from database via UoW
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Only scan non-technical active users
                # CRITICAL: Exclude system_user - it must NEVER have agency goals
                active_users = await uow.user_profiles.list(
                    filters={"is_active": True, "is_technical": False},
                    limit=100000,
                )
            # Explicitly filter out system_user
            user_ids = [u.uuid for u in active_users if u.uuid != 'system_user']
            
            if not user_ids:
                _get_logger().warning("[CURIOSITY_SCAN] No active users found")
                return TaskResult(
                    success=True,
                    message="No active users",
                    skipped=True,
                )
            
            # Check lifecycle state (if available)
            lifecycle_state = getattr(context, "lifecycle_state", "unknown")
            _get_logger().debug(f"[CURIOSITY_SCAN] Lifecycle state: {lifecycle_state}")
            
            # Defer if user is active (not idle)
            if lifecycle_state == "active":
                _get_logger().info("[CURIOSITY_SCAN] User active, deferring scan")
                return TaskResult(
                    success=True,
                    message="Deferred - user active",
                    skipped=True,
                    data={"reason": "user_active"},
                )
            
            # Scan for opportunities for all users
            total_signals = 0
            total_goals_created = 0
            total_goals_failed = 0
            
            # Performance tracking
            user_timings = []
            users_skipped = 0
            users_timeout = 0
            
            print(f"\n🔍 Scanning {len(user_ids)} user(s) for curiosity opportunities...")
            for idx, user_id in enumerate(user_ids, 1):
                user_start_time = datetime.now(timezone.utc)
                timings = {"user_id": user_id[:8], "operations": {}}
                
                print(f"\n{'='*60}")
                print(f"👤 User {idx}/{len(user_ids)}: {user_id[:8]}...")
                print(f"{'='*60}")
                _get_logger().info(f"[CURIOSITY_SCAN] Scanning for user {user_id}")
                
                # Per-user timeout wrapper (60s max)
                async def process_user():
                    """Process single user with detailed timing."""
                    # Get config from services.agency.curiosity
                    config_start = datetime.now(timezone.utc)
                    curiosity_config = context.config_manager.get("agency.curiosity", {})
                    max_signals = curiosity_config.get("max_signals_per_scan", 10)
                    min_score = curiosity_config.get("min_signal_score", 0.3)
                    timings["operations"]["config_load"] = (datetime.now(timezone.utc) - config_start).total_seconds()
                    
                    # Scan for opportunities with timing
                    scan_start = datetime.now(timezone.utc)
                    signals = await curiosity_engine.scan_for_opportunities(
                        user_id=user_id,
                        max_signals=max_signals,
                    )
                    scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
                    timings["operations"]["scan_opportunities"] = scan_duration
                    
                    _get_logger().info(
                        f"[CURIOSITY_SCAN] Found {len(signals)} curiosity signals for {user_id} "
                        f"in {scan_duration:.2f}s"
                    )
                    nonlocal total_signals
                    total_signals += len(signals)
                    high_score_signals = [s for s in signals if s.total_score >= min_score]
                    print(f"  ✨ Found {len(signals)} curiosity signals ({len(high_score_signals)} above {min_score} threshold) in {scan_duration:.2f}s")
                    
                    # Create goals from high-scoring signals
                    goal_creation_times = []
                    for signal_idx, signal in enumerate(signals, 1):
                        # Only create goals for signals with score >= min_score threshold
                        if signal.total_score < min_score:
                            _get_logger().debug(
                                f"[CURIOSITY_SCAN] Skipping low-score signal: "
                                f"{signal.topic} (score={signal.total_score:.2f})"
                            )
                            continue
                        
                        print(f"  📝 Creating goal {signal_idx}/{len(signals)}: {signal.topic}...", end=" ", flush=True)
                        
                        try:
                            goal_start = datetime.now(timezone.utc)
                            # Per-goal timeout (30s max)
                            goal, plan = await asyncio.wait_for(
                                agency_engine.create_goal_from_curiosity_signal(
                                    user_id=user_id,
                                    signal=signal,
                                    auto_plan=False,
                                ),
                                timeout=30.0
                            )
                            goal_duration = (datetime.now(timezone.utc) - goal_start).total_seconds()
                            goal_creation_times.append(goal_duration)
                            
                            nonlocal total_goals_created
                            total_goals_created += 1
                            _get_logger().info(
                                f"[CURIOSITY_SCAN] Created {signal.signal_type.value} goal: "
                                f"{goal.title} (score={signal.total_score:.2f}) in {goal_duration:.2f}s"
                            )
                            print(f"✅ ({goal_duration:.1f}s)")
                        except asyncio.TimeoutError:
                            goal_duration = (datetime.now(timezone.utc) - goal_start).total_seconds()
                            goal_creation_times.append(goal_duration)
                            nonlocal total_goals_failed
                            total_goals_failed += 1
                            print(f"❌ TIMEOUT ({goal_duration:.1f}s)")
                            _get_logger().error(
                                f"[CURIOSITY_SCAN] Goal creation timed out after {goal_duration:.2f}s "
                                f"for signal {signal.signal_id}"
                            )
                        except Exception as e:
                            goal_duration = (datetime.now(timezone.utc) - goal_start).total_seconds()
                            goal_creation_times.append(goal_duration)
                            total_goals_failed += 1
                            print(f"❌ {str(e)[:50]} ({goal_duration:.1f}s)")
                            _get_logger().error(
                                f"[CURIOSITY_SCAN] Failed to create goal from signal "
                                f"{signal.signal_id} after {goal_duration:.2f}s: {e}"
                            )
                    
                    # Record goal creation timings
                    if goal_creation_times:
                        timings["operations"]["goal_creation_total"] = sum(goal_creation_times)
                        timings["operations"]["goal_creation_avg"] = sum(goal_creation_times) / len(goal_creation_times)
                        timings["operations"]["goal_creation_max"] = max(goal_creation_times)
                        timings["operations"]["goal_count"] = len(goal_creation_times)
                
                try:
                    # Execute with 60s timeout per user
                    await asyncio.wait_for(process_user(), timeout=60.0)
                except asyncio.TimeoutError:
                    user_duration = (datetime.now(timezone.utc) - user_start_time).total_seconds()
                    _get_logger().error(
                        f"[CURIOSITY_SCAN] User {user_id} timed out after {user_duration:.2f}s"
                    )
                    timings["operations"]["error"] = "User processing timeout (60s)"
                    users_timeout += 1
                except Exception as e:
                    scan_duration = (datetime.now(timezone.utc) - user_start_time).total_seconds()
                    _get_logger().error(
                        f"[CURIOSITY_SCAN] Failed to scan for user {user_id} after {scan_duration:.2f}s: {e}"
                    )
                    timings["operations"]["error"] = str(e)
                
                # Record total user processing time
                user_duration = (datetime.now(timezone.utc) - user_start_time).total_seconds()
                timings["total_duration"] = user_duration
                user_timings.append(timings)
                
                # Log performance summary for this user
                _get_logger().info(
                    f"[CURIOSITY_SCAN] User {user_id[:8]} completed in {user_duration:.2f}s - "
                    f"Scan: {timings['operations'].get('scan_opportunities', 0):.2f}s, "
                    f"Goals: {timings['operations'].get('goal_creation_total', 0):.2f}s "
                    f"({timings['operations'].get('goal_count', 0)} goals)"
                )
                print(f"⏱️  User processing time: {user_duration:.2f}s")
            
            # Calculate execution time
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Performance analysis
            if user_timings:
                total_scan_time = sum(t["operations"].get("scan_opportunities", 0) for t in user_timings)
                total_goal_time = sum(t["operations"].get("goal_creation_total", 0) for t in user_timings)
                avg_user_time = sum(t["total_duration"] for t in user_timings) / len(user_timings)
                max_user_time = max(t["total_duration"] for t in user_timings)
                
                _get_logger().info(
                    f"[CURIOSITY_SCAN] Performance Summary - "
                    f"Total scan time: {total_scan_time:.2f}s, "
                    f"Total goal creation: {total_goal_time:.2f}s, "
                    f"Avg per user: {avg_user_time:.2f}s, "
                    f"Max user: {max_user_time:.2f}s"
                )
                
                # Identify slow users
                slow_users = [t for t in user_timings if t["total_duration"] > 30]
                if slow_users:
                    _get_logger().warning(
                        f"[CURIOSITY_SCAN] {len(slow_users)} slow users detected (>30s): "
                        f"{[u['user_id'] for u in slow_users]}"
                    )
            
            # Build result
            result = TaskResult(
                success=True,
                message=f"Scan complete: {total_goals_created} goals created for {len(user_ids)} users",
                data={
                    "users_scanned": len(user_ids),
                    "users_timeout": users_timeout,
                    "users_skipped": users_skipped,
                    "signals_found": total_signals,
                    "goals_created": total_goals_created,
                    "goals_failed": total_goals_failed,
                    "lifecycle_state": lifecycle_state,
                    "performance": {
                        "user_timings": user_timings,
                        "total_scan_time": sum(t["operations"].get("scan_opportunities", 0) for t in user_timings) if user_timings else 0,
                        "total_goal_time": sum(t["operations"].get("goal_creation_total", 0) for t in user_timings) if user_timings else 0,
                        "avg_user_time": sum(t["total_duration"] for t in user_timings) / len(user_timings) if user_timings else 0,
                        "max_user_time": max(t["total_duration"] for t in user_timings) if user_timings else 0,
                    },
                },
                duration_seconds=duration,
            )
            
            # Log summary
            print("=" * 80)
            print(" CURIOSITY SCAN COMPLETE")
            print("=" * 80)
            print(f"  Users Scanned:    {len(user_ids)}")
            print(f"  Signals Found:    {total_signals}")
            print(f"  Goals Created:    {total_goals_created}")
            print(f"  Goals Failed:     {total_goals_failed}")
            print(f"  Duration:         {duration:.2f}s")
            print(f"  Lifecycle State:  {lifecycle_state}")
            print("=" * 80)
            
            _get_logger().info(
                f"[CURIOSITY_SCAN] Complete: {len(user_ids)} users, {total_signals} signals, "
                f"{total_goals_created} goals created, {duration:.1f}s"
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            _get_logger().error(f"[CURIOSITY_SCAN] Task failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Curiosity scan failed: {str(e)}",
                error=str(e),
                duration_seconds=duration,
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
                _get_logger().debug("[CURIOSITY_SCAN] Unknown lifecycle state, allowing run")
                return True
            
            # Defer during active interaction
            if lifecycle_state == "active":
                _get_logger().debug("[CURIOSITY_SCAN] User active, deferring")
                return False
            
            # Check quiet hours (if configured)
            quiet_hours = context.get("quiet_hours", {})
            if quiet_hours.get("enabled", False):
                current_hour = datetime.now(timezone.utc).hour
                start_hour = quiet_hours.get("start_hour", 22)
                end_hour = quiet_hours.get("end_hour", 7)
                
                # Check if current time is in quiet hours
                if start_hour > end_hour:  # Crosses midnight
                    in_quiet_hours = current_hour >= start_hour or current_hour < end_hour
                else:
                    in_quiet_hours = start_hour <= current_hour < end_hour
                
                if in_quiet_hours:
                    _get_logger().debug("[CURIOSITY_SCAN] In quiet hours, deferring")
                    return False
            
            return True
            
        except Exception as e:
            _get_logger().error(f"[CURIOSITY_SCAN] Error checking should_run: {e}")
            # Default to allowing run on error
            return True
