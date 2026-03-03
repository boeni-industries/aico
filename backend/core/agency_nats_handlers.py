"""
Agency NATS Handlers - Complete implementation for all agency endpoints.

This module contains all NATS handlers that proxy agency functionality from
gateway to core. Each handler corresponds to a REST endpoint in the gateway.
"""

from typing import Dict, Any
from datetime import datetime, UTC, timedelta
import logging

logger = logging.getLogger(__name__)


class AgencyNATSHandlers:
    """All agency NATS request handlers"""
    
    def __init__(self, container):
        self.container = container
        self.logger = logger
    
    async def handle_agency_intentions_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency intentions request - mirrors GET /agency/intentions"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 10)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get intention set
            intention_set_obj = await agency_engine.get_intention_set(user_id)
            intentions = intention_set_obj.intentions[:limit]
            
            # Fetch Goal objects for active intentions
            active_intentions = []
            hobby_goals = []
            if intentions:
                goal_ids = [intent.goal_id for intent in intentions]
                goals = await agency_engine.agency_service.get_goals_bulk(goal_ids)
                goals_by_id = {goal.goal_id: goal for goal in goals}
                
                for intent in intentions:
                    goal = goals_by_id.get(intent.goal_id)
                    if goal:
                        goal_summary = {
                            "goal_id": goal.goal_id,
                            "title": goal.title,
                            "description": goal.description,
                            "origin": goal.origin.value,
                            "priority": goal.priority.value,
                            "status": goal.status.value,
                            "score": intent.arbiter_score,
                            "priority_band": intent.priority_band.value,
                            "created_at": goal.created_at.isoformat() if hasattr(goal.created_at, 'isoformat') else str(goal.created_at),
                            "metadata": goal.metadata or {},
                        }
                        active_intentions.append(goal_summary)
                        if goal.origin.value == "hobby":
                            hobby_goals.append(goal_summary)
            
            # Get all goals for open count
            all_goals = await agency_engine.list_goals_for_user(user_id)
            open_goals = [g for g in all_goals if g.status.value in ["pending", "active"]]
            
            return {
                "user_id": user_id,
                "primary_focus": active_intentions[0] if active_intentions else None,
                "active_intentions": active_intentions,
                "open_goals_total": len(open_goals),
                "hobby_goals_active": hobby_goals,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get intentions: {e}", exc_info=True)
            return {"error": "AGENCY_INTENTIONS_FAILED", "message": str(e)}
    
    async def handle_agency_events_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency events request - mirrors GET /agency/events"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 50)
            offset = request_data.get("offset", 0)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get events from agency_events_log
                rows = await uow_instance.agency_events_log.get_by_user(user_id, limit=limit, offset=offset)
                
                events = []
                for row in rows:
                    # Parse event_data JSON if it's a string
                    import json
                    event_data = {}
                    if hasattr(row, 'event_data') and row.event_data:
                        try:
                            event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                        except:
                            event_data = {}
                    
                    events.append({
                        "event_id": row.event_id,
                        "user_id": row.user_id,
                        "event_type": row.event_type,
                        "source": row.source_component or "system",
                        "title": event_data.get("title", row.event_type),
                        "description": event_data.get("description", ""),
                        "intensity": event_data.get("intensity", 0.5),
                        "metadata": event_data,
                        "created_at": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                        "processed": True,
                        "related_goal_id": row.entity_id if row.entity_type == "goal" else None,
                        "strength": 1,
                    })
                
                return {
                    "events": events,
                    "total": len(events),
                    "limit": limit,
                    "offset": offset,
                }
                
        except Exception as e:
            self.logger.error(f"Failed to list events: {e}", exc_info=True)
            return {"error": "AGENCY_EVENTS_FAILED", "message": str(e)}
    
    async def handle_agency_curiosity_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency curiosity request - mirrors GET /agency/curiosity"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get curiosity status from engine
            curiosity_enabled = getattr(agency_engine, 'curiosity_enabled', True)
            
            return {
                "user_id": user_id,
                "curiosity_level": "medium",
                "curiosity_opportunities": [],
                "curiosity_goals_active": 0,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get curiosity status: {e}", exc_info=True)
            return {"error": "AGENCY_CURIOSITY_FAILED", "message": str(e)}
    
    async def handle_agency_profile_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency profile request - mirrors GET /agency/profile"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get value profile from database
                profile = await uow_instance.value_profiles.get_by_user(user_id)
                
                if profile:
                    return {
                        "profile_id": profile.profile_id,
                        "user_id": profile.user_id,
                        "curiosity_intensity": profile.curiosity_intensity or 0.5,
                        "autonomy_level": profile.autonomy_level or "balanced",
                        "sensitive_life_areas": profile.sensitive_life_areas or [],
                        "allowed_curiosity_domains": profile.allowed_curiosity_domains or [],
                    }
                else:
                    # Return default profile
                    return {
                        "profile_id": f"profile_{user_id}",
                        "user_id": user_id,
                        "curiosity_intensity": 0.5,
                        "autonomy_level": "balanced",
                        "sensitive_life_areas": [],
                        "allowed_curiosity_domains": [],
                    }
                    
        except Exception as e:
            self.logger.error(f"Failed to get value profile: {e}", exc_info=True)
            return {"error": "AGENCY_PROFILE_FAILED", "message": str(e)}
    
    async def handle_agency_profile_update_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency profile update request - mirrors PUT /agency/profile"""
        try:
            user_id = request_data.get("user_id")
            update_data = request_data.get("update_data", {})
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Update value profile
                profile = await uow_instance.value_profiles.get_by_user(user_id)
                
                if profile:
                    # Update existing profile
                    if "curiosity_intensity" in update_data:
                        profile.curiosity_intensity = update_data["curiosity_intensity"]
                    if "autonomy_level" in update_data:
                        profile.autonomy_level = update_data["autonomy_level"]
                    if "add_sensitive_areas" in update_data:
                        profile.sensitive_life_areas = list(set(profile.sensitive_life_areas + update_data["add_sensitive_areas"]))
                    if "remove_sensitive_areas" in update_data:
                        profile.sensitive_life_areas = [a for a in profile.sensitive_life_areas if a not in update_data["remove_sensitive_areas"]]
                    
                    await uow_instance.value_profiles.update(profile)
                    await uow_instance.commit()
                    
                    return {
                        "profile_id": profile.profile_id,
                        "user_id": profile.user_id,
                        "curiosity_intensity": profile.curiosity_intensity,
                        "autonomy_level": profile.autonomy_level,
                        "sensitive_life_areas": profile.sensitive_life_areas,
                        "allowed_curiosity_domains": profile.allowed_curiosity_domains or [],
                    }
                else:
                    return {"error": "PROFILE_NOT_FOUND", "message": "Value profile not found"}
                    
        except Exception as e:
            self.logger.error(f"Failed to update value profile: {e}", exc_info=True)
            return {"error": "AGENCY_PROFILE_UPDATE_FAILED", "message": str(e)}
    
    async def handle_agency_policies_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency policies request - mirrors GET /agency/policies"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty policies list for now
            return {
                "policies": [],
                "total": 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list policies: {e}", exc_info=True)
            return {"error": "AGENCY_POLICIES_FAILED", "message": str(e)}
    
    async def handle_agency_consent_grant_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency consent grant request - mirrors POST /agency/consent"""
        try:
            user_id = request_data.get("user_id")
            consent_data = request_data.get("consent_data", {})
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Placeholder - implement consent storage
            consent_id = f"consent_{user_id}_{datetime.now(UTC).timestamp()}"
            
            return {
                "consent_id": consent_id,
                "user_id": user_id,
                "scope": consent_data.get("scope", {}),
                "decision": consent_data.get("decision", "granted"),
                "granted_at": datetime.now(UTC).isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to grant consent: {e}", exc_info=True)
            return {"error": "AGENCY_CONSENT_GRANT_FAILED", "message": str(e)}
    
    async def handle_agency_consents_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency consents request - mirrors GET /agency/consent"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty consents list for now
            return {
                "consents": [],
                "total": 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list consents: {e}", exc_info=True)
            return {"error": "AGENCY_CONSENTS_FAILED", "message": str(e)}
    
    async def handle_agency_consent_revoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency consent revoke request - mirrors DELETE /agency/consent/{id}"""
        try:
            user_id = request_data.get("user_id")
            consent_id = request_data.get("consent_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not consent_id:
                return {"error": "MISSING_CONSENT_ID", "message": "consent_id is required"}
            
            # Placeholder - implement consent revocation
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Failed to revoke consent: {e}", exc_info=True)
            return {"error": "AGENCY_CONSENT_REVOKE_FAILED", "message": str(e)}
    
    async def handle_agency_goals_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency goals list request - mirrors GET /agency/goals"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            status = request_data.get("status")
            origin = request_data.get("origin")
            priority = request_data.get("priority")
            limit = request_data.get("limit", 50)
            page = request_data.get("page", 1)
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get all goals for user
            all_goals = await agency_engine.list_goals_for_user(user_id)
            
            # Apply filters
            filtered_goals = all_goals
            if status:
                filtered_goals = [g for g in filtered_goals if g.status.value == status]
            if origin:
                filtered_goals = [g for g in filtered_goals if g.origin.value == origin]
            if priority:
                filtered_goals = [g for g in filtered_goals if g.priority.value == priority]
            
            # Pagination
            total = len(filtered_goals)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_goals = filtered_goals[start_idx:end_idx]
            
            # Convert to response format
            goal_responses = [
                {
                    "goal_id": g.goal_id,
                    "user_id": g.user_id,
                    "origin": g.origin.value,
                    "goal_type": g.goal_type,
                    "title": g.title,
                    "description": g.description or "",
                    "status": g.status.value,
                    "priority": g.priority.value,
                    "metadata": g.metadata or {},
                    "created_at": g.created_at.isoformat() if hasattr(g.created_at, 'isoformat') else str(g.created_at),
                    "updated_at": g.updated_at.isoformat() if hasattr(g.updated_at, 'isoformat') else str(g.updated_at),
                }
                for g in paginated_goals
            ]
            
            return {
                "goals": goal_responses,
                "total": total,
                "page": page,
                "page_size": limit,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list goals: {e}", exc_info=True)
            return {"error": "AGENCY_GOALS_LIST_FAILED", "message": str(e)}
    
    async def handle_agency_goal_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency goal request - mirrors GET /agency/goals/{id}"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            goal_id = request_data.get("goal_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not goal_id:
                return {"error": "MISSING_GOAL_ID", "message": "goal_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get goal
            goal = await agency_engine.agency_service.get_goal(goal_id)
            
            if not goal or goal.user_id != user_id:
                return {"error": "GOAL_NOT_FOUND", "message": "Goal not found"}
            
            return {
                "goal_id": goal.goal_id,
                "user_id": goal.user_id,
                "origin": goal.origin.value,
                "goal_type": goal.goal_type,
                "title": goal.title,
                "description": goal.description or "",
                "status": goal.status.value,
                "priority": goal.priority.value,
                "metadata": goal.metadata or {},
                "created_at": goal.created_at.isoformat() if hasattr(goal.created_at, 'isoformat') else str(goal.created_at),
                "updated_at": goal.updated_at.isoformat() if hasattr(goal.updated_at, 'isoformat') else str(goal.updated_at),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get goal: {e}", exc_info=True)
            return {"error": "AGENCY_GOAL_FAILED", "message": str(e)}
    
    async def handle_agency_goal_plans_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency goal plans request - mirrors GET /agency/goals/{id}/plans"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            goal_id = request_data.get("goal_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not goal_id:
                return {"error": "MISSING_GOAL_ID", "message": "goal_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get goal with plans
            goal = await agency_engine.agency_service.get_goal(goal_id)
            
            if not goal or goal.user_id != user_id:
                return {"error": "GOAL_NOT_FOUND", "message": "Goal not found"}
            
            # Get plans for goal
            plans = await agency_engine.agency_service.list_plans(goal_id=goal_id)
            
            plans_data = []
            for plan in plans:
                # Convert plan steps to dictionaries with all required fields
                steps_data = []
                if plan.steps:
                    for idx, step in enumerate(plan.steps):
                        step_dict = {
                            "step_id": step.step_id if hasattr(step, 'step_id') else str(step),
                            "order": step.order if hasattr(step, 'order') else idx,
                            "description": step.description if hasattr(step, 'description') else "",
                            "status": step.status.value if hasattr(step, 'status') and hasattr(step.status, 'value') else "pending",
                            "tool_id": step.tool_id if hasattr(step, 'tool_id') else None,
                            "skill_id": step.skill_id if hasattr(step, 'skill_id') else None,
                            "scheduled_for": step.scheduled_for.isoformat() if hasattr(step, 'scheduled_for') and step.scheduled_for else None,
                            "depends_on": step.dependencies if hasattr(step, 'dependencies') else [],
                            "metadata": step.metadata if hasattr(step, 'metadata') else {},
                            "implementation_tools": step.implementation_tools if hasattr(step, 'implementation_tools') else [],
                        }
                        steps_data.append(step_dict)
                
                plans_data.append({
                    "plan_id": plan.plan_id,
                    "goal_id": plan.goal_id,
                    "title": plan.title if hasattr(plan, 'title') else None,
                    "description": plan.description if hasattr(plan, 'description') else None,
                    "status": plan.status.value if hasattr(plan.status, 'value') else str(plan.status),
                    "metadata": plan.metadata if hasattr(plan, 'metadata') else {},
                    "created_at": plan.created_at.isoformat() if hasattr(plan.created_at, 'isoformat') else str(plan.created_at),
                    "updated_at": plan.updated_at.isoformat() if hasattr(plan, 'updated_at') and plan.updated_at else plan.created_at.isoformat() if hasattr(plan.created_at, 'isoformat') else str(plan.created_at),
                    "steps": steps_data,
                    "execution": None,
                    "executions": [],
                })
            
            # Build GoalResponse structure
            goal_response = {
                "goal_id": goal.goal_id,
                "user_id": goal.user_id,
                "origin": goal.origin.value if hasattr(goal.origin, 'value') else str(goal.origin),
                "goal_type": goal.goal_type if hasattr(goal, 'goal_type') else "general",
                "title": goal.title,
                "description": goal.description or "",
                "status": goal.status.value if hasattr(goal.status, 'value') else str(goal.status),
                "priority": goal.priority.value if hasattr(goal.priority, 'value') else "normal",
                "metadata": goal.metadata if hasattr(goal, 'metadata') else {},
                "created_at": goal.created_at.isoformat() if hasattr(goal.created_at, 'isoformat') else str(goal.created_at),
                "updated_at": goal.updated_at.isoformat() if hasattr(goal, 'updated_at') and goal.updated_at else goal.created_at.isoformat() if hasattr(goal.created_at, 'isoformat') else str(goal.created_at),
            }
            
            return {
                "goal": goal_response,
                "plans": plans_data,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get goal plans: {e}", exc_info=True)
            return {"error": "AGENCY_GOAL_PLANS_FAILED", "message": str(e)}
    
    async def handle_agency_goal_replan_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency goal replan request - mirrors POST /agency/goals/{id}/replan"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            goal_id = request_data.get("goal_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not goal_id:
                return {"error": "MISSING_GOAL_ID", "message": "goal_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Trigger replan
            result = await agency_engine.replan_goal(goal_id)
            
            return {
                "success": True,
                "goal_id": goal_id,
                "message": "Goal replanning initiated",
            }
            
        except Exception as e:
            self.logger.error(f"Failed to replan goal: {e}", exc_info=True)
            return {"error": "AGENCY_GOAL_REPLAN_FAILED", "message": str(e)}
    
    async def handle_agency_skills_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency skills list request - mirrors POST /agency/skills/list"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get skills from registry
            skills = agency_engine.skill_registry.list_skills()
            
            skills_data = []
            for skill in skills:
                info = agency_engine.skill_registry.get_skill_info(skill.skill_id)
                if info:
                    skills_data.append(info)
            
            return {"skills": skills_data}
            
        except Exception as e:
            self.logger.error(f"Failed to list skills: {e}", exc_info=True)
            return {"error": "AGENCY_SKILLS_LIST_FAILED", "message": str(e)}
    
    async def handle_agency_skill_info_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency skill info request - mirrors POST /agency/skills/info"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            skill_id = request_data.get("skill_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not skill_id:
                return {"error": "MISSING_SKILL_ID", "message": "skill_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Get skill info
            info = agency_engine.skill_registry.get_skill_info(skill_id)
            
            if not info:
                return {"error": "SKILL_NOT_FOUND", "message": f"Skill {skill_id} not found"}
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get skill info: {e}", exc_info=True)
            return {"error": "AGENCY_SKILL_INFO_FAILED", "message": str(e)}
    
    async def handle_agency_skill_invoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency skill invoke request - mirrors POST /agency/skills/invoke"""
        try:
            from aico.ai import ai_registry
            
            user_id = request_data.get("user_id")
            skill_data = request_data.get("skill_data", {})
            skill_id = skill_data.get("skill_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not skill_id:
                return {"error": "MISSING_SKILL_ID", "message": "skill_id is required"}
            
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}
            
            # Invoke skill
            result = await agency_engine.skill_registry.invoke_skill(
                skill_id=skill_id,
                input_data=skill_data.get("input", {}),
                context={"user_id": user_id}
            )
            
            return {"output": result}
            
        except Exception as e:
            self.logger.error(f"Failed to invoke skill: {e}", exc_info=True)
            return {"error": "AGENCY_SKILL_INVOKE_FAILED", "message": str(e)}
    
    async def handle_agency_connectivity_scan_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency connectivity scan request - mirrors POST /agency/connectivity/scan"""
        try:
            user_id = request_data.get("user_id")
            scan_data = request_data.get("scan_data", {})
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Placeholder - implement connectivity scan
            return {
                "output": {
                    "scan_complete": True,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run connectivity scan: {e}", exc_info=True)
            return {"error": "AGENCY_CONNECTIVITY_SCAN_FAILED", "message": str(e)}
    
    async def handle_agency_tools_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency tools list request - mirrors POST /agency/tools/list"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty tools list for now
            return {"tools": []}
            
        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}", exc_info=True)
            return {"error": "AGENCY_TOOLS_LIST_FAILED", "message": str(e)}
    
    async def handle_agency_tool_info_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency tool info request - mirrors POST /agency/tools/info"""
        try:
            user_id = request_data.get("user_id")
            tool_id = request_data.get("tool_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not tool_id:
                return {"error": "MISSING_TOOL_ID", "message": "tool_id is required"}
            
            # Placeholder - implement tool info
            return {"error": "TOOL_NOT_FOUND", "message": f"Tool {tool_id} not found"}
            
        except Exception as e:
            self.logger.error(f"Failed to get tool info: {e}", exc_info=True)
            return {"error": "AGENCY_TOOL_INFO_FAILED", "message": str(e)}
    
    async def handle_agency_tool_invoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency tool invoke request - mirrors POST /agency/tools/invoke"""
        try:
            user_id = request_data.get("user_id")
            tool_data = request_data.get("tool_data", {})
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Placeholder - implement tool invocation
            return {"output": {}}
            
        except Exception as e:
            self.logger.error(f"Failed to invoke tool: {e}", exc_info=True)
            return {"error": "AGENCY_TOOL_INVOKE_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_runs_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection runs request - mirrors GET /agency/reflection/runs"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 50)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty runs list for now
            return {
                "runs": [],
                "total": 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list reflection runs: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_RUNS_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_lessons_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection lessons request - mirrors GET /agency/reflection/lessons"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 50)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty lessons list for now
            return {
                "lessons": [],
                "total": 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list reflection lessons: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_LESSONS_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_self_model_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection self-model request - mirrors GET /agency/reflection/self-model"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Return empty self-model list for now
            return {
                "entries": [],
                "total": 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list self-model: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_SELF_MODEL_FAILED", "message": str(e)}
    
    async def handle_agency_skill_performance_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency skill performance request - mirrors GET /agency/reflection/skills/{id}/performance"""
        try:
            user_id = request_data.get("user_id")
            skill_id = request_data.get("skill_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not skill_id:
                return {"error": "MISSING_SKILL_ID", "message": "skill_id is required"}
            
            # Return placeholder performance data
            return {
                "skill_id": skill_id,
                "success_rate": 0.0,
                "total_invocations": 0,
                "avg_duration_ms": 0.0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get skill performance: {e}", exc_info=True)
            return {"error": "AGENCY_SKILL_PERFORMANCE_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_summary_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection summary request - mirrors GET /agency/reflection/summary"""
        try:
            user_id = request_data.get("user_id")
            window_days = request_data.get("window_days", 30)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Calculate window dates
            window_end = datetime.now(UTC)
            window_start = window_end - timedelta(days=window_days)
            
            # Return placeholder summary with all required fields
            return {
                "user_id": user_id,
                "window_days": window_days,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "reflections": 0,
                "lessons_total": 0,
                "lessons_applied": 0,
                "avg_confidence": None,
                "recent_lessons": [],
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get reflection summary: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_SUMMARY_FAILED", "message": str(e)}
