"""
Goal Reflection Skill

Analyzes goal progress, identifies blockers, and generates insights.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger
from aico.services.agency_service import AgencyService


logger = get_logger("shared.ai.agency.skills.reflection.goal")


class ReflectOnGoalSkill(Skill):
    """
    Reflect on goal progress and generate insights.
    
    Used for: Deep Dive Learning, Skill Building goals
    """
    
    def __init__(self, agency_service: Optional[AgencyService] = None):
        self.agency_service = agency_service
    
    @property
    def skill_id(self) -> str:
        return "reflect_on_goal"
    
    @property
    def name(self) -> str:
        return "Reflect on Goal"
    
    @property
    def description(self) -> str:
        return "Analyze goal progress, identify blockers, and generate improvement insights"
    
    @property
    def category(self) -> str:
        return "reflection"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="goal_id",
                type=SkillParameterType.STRING,
                description="Goal to reflect on",
                required=True,
            ),
            SkillParameter(
                name="include_history",
                type=SkillParameterType.BOOLEAN,
                description="Include historical execution data",
                required=False,
                default=True,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute goal reflection."""
        goal_id = input_data.get("goal_id")
        include_history = input_data.get("include_history", True)
        
        logger.info(
            f"🤔 [REFLECT_ON_GOAL] Reflecting on goal {goal_id[:8]}... "
            f"for user {user_id[:8]}... (include_history={include_history})"
        )
        
        try:
            if not self.agency_service:
                raise RuntimeError("AgencyService not available")

            # Get goal details via AgencyService
            goal = await self.agency_service.get_goal(goal_id)

            if not goal or goal.user_id != user_id:
                raise ValueError(f"Goal {goal_id} not found")

            logger.info(f"🤔 [REFLECT_ON_GOAL] Analyzing goal: {goal.title}")

            # Get plans for this goal
            plans = await self.agency_service.list_plans(goal_id)

            # Get executions if history is requested
            executions: List[Any] = []
            if include_history and plans:
                for plan in plans:
                    plan_execs = await self.agency_service.get_plan_executions(plan.plan_id)
                    executions.extend(plan_execs[:5])
            
            # Analyze progress
            blockers = []
            insights = []
            recommendations = []
            
            # Check goal status
            if goal.status.value == "pending":
                insights.append("Goal is pending - no active work yet")
                recommendations.append("Consider activating this goal if it's a priority")
            elif goal.status.value == "active":
                insights.append("Goal is actively being worked on")
            elif goal.status.value == "paused":
                blockers.append("Goal is currently paused")
                recommendations.append("Review why goal was paused and consider resuming")
            
            # Analyze plans
            if not plans:
                blockers.append("No plans created for this goal yet")
                recommendations.append("Create a plan to start making progress")
            else:
                draft_plans = [p for p in plans if p.status.value == "draft"]
                active_plans = [p for p in plans if p.status.value == "active"]
                
                if draft_plans:
                    insights.append(f"{len(draft_plans)} draft plan(s) available")
                if active_plans:
                    insights.append(f"{len(active_plans)} active plan(s) in progress")
            
            # Analyze executions
            failed = []
            if executions:
                completed = [e for e in executions if getattr(e, "status", None) == "completed"]
                failed = [e for e in executions if getattr(e, "status", None) == "failed"]
                running = [e for e in executions if getattr(e, "status", None) == "running"]
                
                if completed:
                    insights.append(f"{len(completed)} execution(s) completed successfully")
                if failed:
                    blockers.append(f"{len(failed)} execution(s) failed")
                    # Extract error messages
                    for exec in failed[:3]:  # Show up to 3 errors
                        error_msg = getattr(exec, "error_message", None)
                        if error_msg:
                            blockers.append(f"Error: {error_msg[:100]}")
                if running:
                    insights.append(f"{len(running)} execution(s) currently running")
                
                # Calculate progress
                total_steps = sum(getattr(e, "steps_total", 0) or 0 for e in executions)
                completed_steps = sum(getattr(e, "steps_completed", 0) or 0 for e in executions)
                if total_steps > 0:
                    progress_pct = (completed_steps / total_steps) * 100
                    insights.append(f"Overall progress: {progress_pct:.1f}% ({completed_steps}/{total_steps} steps)")
            
            # Generate recommendations
            if not blockers:
                recommendations.append("Continue current approach - no major blockers identified")
            else:
                recommendations.append("Address identified blockers to improve progress")
            
            if failed:
                recommendations.append("Review failed executions and adjust plan if needed")
            
            # Check goal age
            created_at = goal.created_at or datetime.now(UTC)
            age_days = (datetime.now(UTC) - created_at).days
            if age_days > 30 and goal.status.value == "pending":
                insights.append(f"Goal has been pending for {age_days} days")
                recommendations.append("Consider prioritizing or retiring this goal")
            
            reflection = {
                "goal_id": goal_id,
                "goal_title": goal.title,
                "goal_status": goal.status.value,
                "progress_assessment": "Making progress" if executions else "Not started",
                "blockers": blockers,
                "insights": insights,
                "recommendations": recommendations,
                "plans_count": len(plans),
                "executions_analyzed": len(executions),
                "reflected_at": datetime.now(UTC).isoformat(),
            }
            
            logger.info(
                f"🤔 [REFLECT_ON_GOAL] Reflection complete: "
                f"{len(blockers)} blockers, "
                f"{len(insights)} insights, "
                f"{len(recommendations)} recommendations"
            )
            
            return SkillResult(
                success=True,
                output=reflection,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.now(UTC).isoformat(),
                },
            )
            
        except Exception as e:
            logger.exception(
                f"🤔 [REFLECT_ON_GOAL] Reflection failed: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Goal reflection failed: {str(e)}",
            )
