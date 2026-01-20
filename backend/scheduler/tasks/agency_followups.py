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
            
            # Query open goals across all users via UoW
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=min_hours)).isoformat()
            session_factory = await get_session_factory()
            
            candidates: List[Dict[str, Any]] = []
            
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)

                # Limit to goals belonging to non-technical active users
                from aico.data.uow import UnitOfWork as _UOW  # type: ignore[unused-import]
                non_technical_users = await uow.user_profiles.list(
                    filters={"is_active": True, "is_technical": False},
                    limit=100000,
                )
                allowed_user_ids = {u.uuid for u in non_technical_users}
                
                # Get active and pending goals
                active_goals = await agency_service.get_goals_by_status('active', limit=max_followups * 2)
                pending_goals = await agency_service.get_goals_by_status('pending', limit=max_followups * 2)
                all_goals = [
                    g for g in (active_goals + pending_goals)
                    if g.user_id in allowed_user_ids
                ][:max_followups]
                
                for goal in all_goals:
                    # Check if this goal has had recent activity in agency_events
                    recent_events = await uow.agency_events.list(
                        filters={
                            'goal_id': goal.goal_id,
                            'created_at__gte': cutoff_time
                        },
                        limit=1
                    )
                    
                    if not recent_events:
                        candidates.append({
                            "goal_id": goal.goal_id,
                            "user_id": goal.user_id,
                            "title": goal.title,
                            "status": goal.status.value if hasattr(goal.status, 'value') else goal.status,
                            "updated_at": goal.updated_at,
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

                async with UnitOfWork(session_factory) as uow:
                    from aico.data.agency.models import AgencyEvent
                    
                    for candidate in candidates[:max_followups_to_send]:
                        # Log candidate identification event
                        event1 = AgencyEvent(
                            user_id=candidate["user_id"],
                            goal_id=candidate["goal_id"],
                            plan_id=None,
                            event_type="followup_candidate_identified",
                            source="agency_followup_task",
                            payload_json=f'{{"title": "{candidate["title"]}"}}',
                            created_at=datetime.now(timezone.utc)
                        )
                        await uow.agency_events.create(event1)

                        # Send proactive follow-up (Phase 1: just log as agency_event)
                        followup_message = f"Checking in on your goal: {candidate['title']}"
                        
                        event2 = AgencyEvent(
                            user_id=candidate["user_id"],
                            goal_id=candidate["goal_id"],
                            plan_id=None,
                            event_type="proactive_followup_sent",
                            source="agency_followup_task",
                            payload_json=f'{{"message": "{followup_message}", "title": "{candidate["title"]}"}}',
                            created_at=datetime.now(timezone.utc)
                        )
                        await uow.agency_events.create(event2)
                        
                        await uow.commit()

                        followup_sent_count += 1
                        self.logger.info(
                            f"[AGENCY_FOLLOWUP] Sent proactive follow-up for goal: {candidate['goal_id']}"
                        )
                
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
