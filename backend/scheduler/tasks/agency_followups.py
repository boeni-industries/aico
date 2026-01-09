"""
Agency Follow-Up Task

Periodic task that scans open goals and plans to determine when follow-ups
or reminders should be sent. This is the backbone for Phase 1 proactive behaviour.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from .base import BaseTask, TaskContext, TaskResult
from aico.ai import ai_registry


class AgencyFollowUpTask(BaseTask):
    """Periodic task for agency follow-ups and reminders.
    
    Phase 1: Scans open goals/plans and logs candidates for follow-ups.
    Later phases: Actually enqueues proactive messages based on policy/values.
    """
    
    task_id = "agency.follow_up"
    default_config = {
        "enabled": True,
        "schedule": "*/15 * * * *",  # Every 15 minutes
        "max_followups_per_run": 5,
        "min_hours_between_followups": 24,
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Scan open goals/plans and determine follow-up candidates."""
        
        try:
            # Get configuration
            max_followups = context.get_config("max_followups_per_run", 5)
            min_hours = context.get_config("min_hours_between_followups", 24)
            
            self.logger.info(
                f"[AGENCY_FOLLOWUP] Starting follow-up scan (max={max_followups}, min_hours={min_hours})"
            )
            
            # Get AgencyEngine from registry
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                self.logger.warning("[AGENCY_FOLLOWUP] AgencyEngine not available in ai_registry")
                return TaskResult(
                    success=False,
                    message="AgencyEngine not available",
                    skipped=True
                )
            
            # Query open goals across all users
            # For Phase 1, we'll scan directly via the DB to avoid per-user loops
            db = context.db_connection
            
            # Find active goals that haven't had a follow-up recently
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=min_hours)).isoformat()
            
            rows = db.execute(
                """
                SELECT g.goal_id, g.user_id, g.title, g.status, g.updated_at
                FROM agency_goals g
                WHERE g.status IN ('active', 'pending')
                ORDER BY g.updated_at ASC
                LIMIT ?
                """,
                (max_followups,)
            ).fetchall()
            
            candidates: List[Dict[str, Any]] = []
            for row in rows:
                goal_id, user_id, title, status, updated_at = row
                
                # Check if this goal has had recent activity in agency_events
                recent_events = db.execute(
                    """
                    SELECT COUNT(*) FROM agency_events
                    WHERE goal_id = ? AND created_at > ?
                    """,
                    (goal_id, cutoff_time)
                ).fetchone()[0]
                
                if recent_events == 0:
                    candidates.append({
                        "goal_id": goal_id,
                        "user_id": user_id,
                        "title": title,
                        "status": status,
                        "updated_at": updated_at,
                    })
            
            # Phase 1: Log candidates and send simple proactive follow-ups
            if candidates:
                self.logger.info(
                    f"[AGENCY_FOLLOWUP] Found {len(candidates)} follow-up candidates",
                    extra={"candidates": [c["goal_id"] for c in candidates]}
                )
                
                # For Phase 1: Send simple proactive follow-up for first candidate only
                # Later phases: more sophisticated selection, actual conversation messages
                followup_sent_count = 0
                max_followups_to_send = min(1, len(candidates))  # Conservative: 1 per run
                
                for candidate in candidates[:max_followups_to_send]:
                    # Log candidate identification event
                    db.execute(
                        """
                        INSERT INTO agency_events (user_id, goal_id, plan_id, event_type, source, payload_json, created_at)
                        VALUES (?, ?, NULL, ?, ?, ?, ?)
                        """,
                        (
                            candidate["user_id"],
                            candidate["goal_id"],
                            "followup_candidate_identified",
                            "agency_followup_task",
                            f'{{"title": "{candidate["title"]}"}}',
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    
                    # Send proactive follow-up (Phase 1: just log as agency_event)
                    # Later phases: enqueue actual conversation message via message bus
                    followup_message = f"Checking in on your goal: {candidate['title']}"
                    
                    db.execute(
                        """
                        INSERT INTO agency_events (user_id, goal_id, plan_id, event_type, source, payload_json, created_at)
                        VALUES (?, ?, NULL, ?, ?, ?, ?)
                        """,
                        (
                            candidate["user_id"],
                            candidate["goal_id"],
                            "proactive_followup_sent",
                            "agency_followup_task",
                            f'{{"message": "{followup_message}", "title": "{candidate["title"]}"}}',
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    
                    followup_sent_count += 1
                    self.logger.info(
                        f"[AGENCY_FOLLOWUP] Sent proactive follow-up for goal: {candidate['goal_id']}"
                    )
                
                db.commit()
                
                self.logger.info(
                    f"[AGENCY_FOLLOWUP] Sent {followup_sent_count} proactive follow-ups out of {len(candidates)} candidates"
                )
            else:
                self.logger.info("[AGENCY_FOLLOWUP] No follow-up candidates found")

            # Print a concise foreground summary (useful for `aico scheduler trigger --wait`)
            print("\n================================================================================")
            print(" AGENCY FOLLOW-UP SCAN COMPLETE")
            print("================================================================================")
            print(f"  Goals scanned (candidates): {len(candidates)}")
            print(f"  Follow-ups sent:            {followup_sent_count if candidates else 0}")
            print("================================================================================\n")

            return TaskResult(
                success=True,
                message=f"Scanned for follow-ups, found {len(candidates)} candidates",
                data={
                    "candidate_count": len(candidates),
                    "followups_sent": followup_sent_count if candidates else 0,
                }
            )
            
        except Exception as e:
            self.logger.error(f"[AGENCY_FOLLOWUP] Task failed: {e}")
            import traceback
            traceback.print_exc()
            return TaskResult(
                success=False,
                error=str(e)
            )
