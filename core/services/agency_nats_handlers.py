"""
Agency NATS Handlers - Complete implementation for all agency endpoints.

This module contains all NATS handlers that proxy agency functionality from
gateway to core. Each handler corresponds to a REST endpoint in the gateway.
"""

from typing import Dict, Any
from datetime import datetime, UTC, timedelta
import logging
import json
import uuid

from aico.data.consent.models import ConsentRecord, ConsentAuditLog

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

            target_type = request_data.get("target_type")
            filters = {"active": True}
            if target_type:
                filters["target_type"] = target_type

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow:
                policies = await uow.ethics_policy_rules.list(filters=filters, limit=1000)

            policies.sort(key=lambda p: p.priority if getattr(p, "priority", None) is not None else 999)

            policy_items = [
                {
                    "rule_id": policy.rule_id,
                    "rule_name": policy.rule_name,
                    "target_type": policy.target_type,
                    "condition_type": policy.condition_type,
                    "condition_config": policy.condition_config or {},
                    "effect": policy.effect,
                    "priority": policy.priority,
                    "enabled": policy.enabled,
                    "scope": policy.scope,
                    "scope_id": policy.scope_id,
                    "created_at": policy.created_at.isoformat() if getattr(policy, "created_at", None) else None,
                    "updated_at": policy.updated_at.isoformat() if getattr(policy, "updated_at", None) else None,
                }
                for policy in policies
            ]

            return {
                "policies": policy_items,
                "total": len(policy_items),
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

            consent_id = f"consent-{user_id}-{datetime.now(UTC).timestamp()}"
            scope = consent_data.get("scope", {}) or {}
            decision = str(consent_data.get("decision") or "granted")
            granted_at = datetime.now(UTC)

            consent = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                consent_scope=json.dumps(scope),
                decision=decision,
                granted_at=granted_at,
            )

            audit_entry = ConsentAuditLog(
                audit_id=str(uuid.uuid4()),
                consent_id=consent_id,
                user_id=user_id,
                action="grant",
                reason=None,
                metadata=json.dumps({"scope": scope, "decision": decision}),
                created_at=granted_at,
            )

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow:
                await uow.consent_records.create(consent)
                await uow.consent_audit_log.create(audit_entry)
                await uow.commit()

            return {
                "consent_id": consent_id,
                "user_id": user_id,
                "scope": scope,
                "decision": decision,
                "granted_at": granted_at.isoformat(),
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

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow:
                consents = await uow.consent_records.list(filters={"user_id": user_id}, limit=1000)

            consents.sort(key=lambda c: c.granted_at if c.granted_at else datetime.min.replace(tzinfo=UTC), reverse=True)

            consent_list = [
                {
                    "consent_id": consent.consent_id,
                    "user_id": consent.user_id,
                    "scope": json.loads(consent.consent_scope) if consent.consent_scope and isinstance(consent.consent_scope, str) else {},
                    "decision": consent.decision,
                    "granted_at": consent.granted_at.isoformat() if consent.granted_at else datetime.now(UTC).isoformat(),
                }
                for consent in consents
            ]

            return {
                "consents": consent_list,
                "total": len(consent_list),
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

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow:
                consent = await uow.consent_records.get_by_id(consent_id)
                if not consent:
                    return {"error": "AGENCY_CONSENT_NOT_FOUND", "message": "Consent not found"}
                if consent.user_id != user_id:
                    return {"error": "FORBIDDEN", "message": "Not authorized"}

                consent.decision = "denied"
                await uow.consent_records.update(consent)
                await uow.consent_audit_log.create(
                    ConsentAuditLog(
                        audit_id=str(uuid.uuid4()),
                        consent_id=consent_id,
                        user_id=user_id,
                        action="revoke",
                        reason=None,
                        metadata=None,
                        created_at=datetime.now(UTC),
                    )
                )
                await uow.commit()

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
            from aico.ai import ai_registry

            user_id = request_data.get("user_id")
            scan_data = request_data.get("scan_data", {})
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}

            agency_engine = ai_registry.get("agency")
            if not agency_engine or not getattr(agency_engine, "skill_invoker", None):
                return {"error": "AGENCY_ENGINE_NOT_INITIALIZED", "message": "Agency engine not initialized"}

            input_data: Dict[str, Any] = {}
            targets = scan_data.get("targets")
            if targets is not None:
                input_data["targets"] = targets

            result = await agency_engine.skill_invoker.invoke_skill(
                skill_id="maint.connectivity.full_scan",
                user_id=user_id,
                input_data=input_data,
                context={
                    "trigger": "agency_connectivity_scan",
                    "initiator_type": "user",
                    "source": "agency_api",
                    "user_id": user_id,
                },
            )

            if not result.get("success"):
                return {
                    "error": "AGENCY_CONNECTIVITY_SCAN_REPORTED_FAILURE",
                    "message": result.get("error") or "Connectivity scan reported failure",
                }

            return result.get("output") or {}
            
        except Exception as e:
            self.logger.error(f"Failed to run connectivity scan: {e}", exc_info=True)
            return {"error": "AGENCY_CONNECTIVITY_SCAN_FAILED", "message": str(e)}
    
    async def handle_agency_tools_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency tools list request - mirrors POST /agency/tools/list"""
        try:
            user_id = request_data.get("user_id")
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}

            from aico.ai.agency.tools.registry import get_tool_registry
            import aico.ai.agency.tools as tools_package
            import importlib
            import pkgutil

            if getattr(tools_package, "__path__", None):
                for module_info in pkgutil.walk_packages(tools_package.__path__, tools_package.__name__ + "."):
                    importlib.import_module(module_info.name)

            registry = get_tool_registry()
            tools = registry.list_all()

            return {
                "tools": [
                    {
                        "tool_id": tool.tool_id,
                        "name": tool.name,
                        "description": tool.description,
                        "domain": tool.domain,
                        "safe": tool.safe,
                        "requires_confirmation": tool.requires_confirmation,
                        "capability_tags": list(tool.capability_tags or []),
                        "parameters": [
                            {
                                "name": parameter.name,
                                "type": parameter.type,
                                "required": parameter.required,
                                "description": parameter.description,
                                "default": parameter.default,
                            }
                            for parameter in tool.parameters
                        ],
                    }
                    for tool in tools
                ]
            }
            
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

            from aico.ai.agency.tools.registry import get_tool_registry
            import aico.ai.agency.tools as tools_package
            import importlib
            import pkgutil

            if getattr(tools_package, "__path__", None):
                for module_info in pkgutil.walk_packages(tools_package.__path__, tools_package.__name__ + "."):
                    importlib.import_module(module_info.name)

            registry = get_tool_registry()
            tool = registry.get(tool_id)
            if not tool:
                return {"error": "AGENCY_TOOL_NOT_FOUND", "message": f"Tool not found: {tool_id}"}

            return {
                "tool_id": tool.tool_id,
                "name": tool.name,
                "description": tool.description,
                "domain": tool.domain,
                "safe": tool.safe,
                "requires_confirmation": tool.requires_confirmation,
                "capability_tags": list(tool.capability_tags or []),
                "parameters": [
                    {
                        "name": parameter.name,
                        "type": parameter.type,
                        "required": parameter.required,
                        "description": parameter.description,
                        "default": parameter.default,
                    }
                    for parameter in tool.parameters
                ],
            }
            
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

            tool_id = tool_data.get("tool_id")
            if not tool_id:
                return {"error": "MISSING_TOOL_ID", "message": "tool_id is required"}

            from aico.ai.agency.tools.registry import get_tool_registry
            import aico.ai.agency.tools as tools_package
            import importlib
            import pkgutil

            if getattr(tools_package, "__path__", None):
                for module_info in pkgutil.walk_packages(tools_package.__path__, tools_package.__name__ + "."):
                    importlib.import_module(module_info.name)

            registry = get_tool_registry()
            tool = registry.get(tool_id)
            if not tool:
                return {"error": "AGENCY_TOOL_NOT_FOUND", "message": f"Tool not found: {tool_id}"}

            kwargs = tool_data.get("input") or {}

            try:
                result = await tool.handler(**kwargs)
            except TypeError:
                return {"error": "AGENCY_TOOL_ARGUMENT_MISMATCH", "message": "Tool invocation argument mismatch"}

            return result
            
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
            
            # Get UoW factory and fetch reflection runs
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                runs = await uow_instance.agency_reflection_runs.get_user_runs(user_id)
                
                # Convert to response format
                runs_data = []
                for run in runs[:limit]:
                    runs_data.append({
                        "run_id": run.run_id,
                        "user_id": run.user_id,
                        "run_type": run.run_type,
                        "trigger_reason": run.trigger_reason,
                        "analysis_window_start": run.analysis_window_start.isoformat() if hasattr(run.analysis_window_start, 'isoformat') else str(run.analysis_window_start),
                        "analysis_window_end": run.analysis_window_end.isoformat() if hasattr(run.analysis_window_end, 'isoformat') else str(run.analysis_window_end),
                        "lessons_generated": run.lessons_generated,
                        "lessons_applied": run.lessons_applied,
                        "started_at": run.started_at.isoformat() if hasattr(run.started_at, 'isoformat') else str(run.started_at),
                        "completed_at": run.completed_at.isoformat() if run.completed_at and hasattr(run.completed_at, 'isoformat') else (str(run.completed_at) if run.completed_at else None),
                        "duration_seconds": run.duration_seconds,
                        "status": run.status,
                        "error_message": run.error_message,
                    })
                
                return {
                    "runs": runs_data,
                    "total": len(runs),
                }
            
        except Exception as e:
            self.logger.error(f"Failed to list reflection runs: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_RUNS_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_lessons_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection lessons request - mirrors GET /agency/reflection/lessons"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 50)
            status = request_data.get("status")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Get UoW factory and fetch lessons
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                filters = {"user_id": user_id}
                if status:
                    filters["status"] = status
                
                lessons = await uow_instance.lessons.list(filters=filters, limit=limit)
                total = await uow_instance.lessons.count(filters=filters)
                
                # Convert to response format
                lessons_data = []
                for lesson in lessons:
                    lessons_data.append({
                        "lesson_id": lesson.lesson_id,
                        "user_id": lesson.user_id,
                        "lesson_type": lesson.lesson_type,
                        "target_kind": lesson.target_kind,
                        "target_id": lesson.target_id,
                        "summary_text": lesson.summary_text,
                        "confidence": lesson.confidence,
                        "scope": lesson.scope,
                        "status": lesson.status,
                        "applied_at": lesson.applied_at.isoformat() if lesson.applied_at and hasattr(lesson.applied_at, 'isoformat') else (str(lesson.applied_at) if lesson.applied_at else None),
                        "source_reflection_run_id": lesson.source_reflection_run_id,
                        "created_at": lesson.created_at.isoformat() if hasattr(lesson.created_at, 'isoformat') else str(lesson.created_at),
                        "updated_at": lesson.updated_at.isoformat() if hasattr(lesson.updated_at, 'isoformat') else str(lesson.updated_at),
                    })
                
                return {
                    "lessons": lessons_data,
                    "total": total,
                }
            
        except Exception as e:
            self.logger.error(f"Failed to list lessons: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_LESSONS_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_self_model_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection self-model request - mirrors GET /agency/reflection/self-model"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 100)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Get UoW factory and fetch self-model entries
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                models = await uow_instance.agency_self_model.get_user_models(user_id)
                
                # Convert to response format (apply limit after fetching)
                models_data = []
                for model in models[:limit]:
                    models_data.append({
                        "model_id": model.model_id,
                        "user_id": model.user_id,
                        "entity_type": model.entity_type,
                        "entity_id": model.entity_id,
                        "performance_summary": model.performance_summary,
                        "window_start": model.window_start.isoformat() if hasattr(model.window_start, 'isoformat') else str(model.window_start),
                        "window_end": model.window_end.isoformat() if hasattr(model.window_end, 'isoformat') else str(model.window_end),
                        "sample_size": model.sample_size,
                        "confidence": model.confidence,
                        "last_updated": model.last_updated.isoformat() if model.last_updated and hasattr(model.last_updated, 'isoformat') else (str(model.last_updated) if model.last_updated else None),
                    })
                
                return {
                    "models": models_data,
                    "total": len(models),
                }
            
        except Exception as e:
            self.logger.error(f"Failed to list self-model: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_SELF_MODEL_FAILED", "message": str(e)}
    
    async def handle_agency_skill_performance_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency skill performance request - mirrors GET /agency/reflection/skills/{id}/performance"""
        try:
            import json

            user_id = request_data.get("user_id")
            skill_id = request_data.get("skill_id")
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            if not skill_id:
                return {"error": "MISSING_SKILL_ID", "message": "skill_id is required"}

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow:
                model = await uow.agency_self_model.get_by_entity(
                    user_id=user_id,
                    entity_type="skill",
                    entity_id=skill_id,
                )

            performance_summary = None
            if model and getattr(model, "performance_summary", None):
                raw_summary = model.performance_summary
                if isinstance(raw_summary, str):
                    try:
                        performance_summary = json.loads(raw_summary)
                    except Exception:
                        performance_summary = None
                elif isinstance(raw_summary, dict):
                    performance_summary = raw_summary

            return {
                "user_id": user_id,
                "skill_id": skill_id,
                "performance_summary": performance_summary,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get skill performance: {e}", exc_info=True)
            return {"error": "AGENCY_SKILL_PERFORMANCE_FAILED", "message": str(e)}
    
    async def handle_agency_reflection_summary_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency reflection summary request - mirrors GET /agency/reflection/summary"""
        try:
            user_id = request_data.get("user_id")
            window_days = request_data.get("window_days", 30)
            recent_lessons_limit = request_data.get("recent_lessons_limit", 10)
            
            if not user_id:
                return {"error": "MISSING_USER_ID", "message": "user_id is required"}
            
            # Calculate window dates
            window_end = datetime.now(UTC)
            window_start = window_end - timedelta(days=window_days)
            
            # Get UoW factory and fetch reflection data
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get all runs for user
                all_runs = await uow_instance.agency_reflection_runs.get_user_runs(user_id)
                
                # Filter runs within window
                runs_in_window = [
                    run for run in all_runs
                    if run.started_at >= window_start and run.started_at <= window_end
                ]
                
                # Get lessons for user
                lessons = await uow_instance.lessons.list(filters={"user_id": user_id}, limit=1000)
                
                self.logger.info(f"[REFLECTION_SUMMARY] Fetched {len(lessons)} lessons for user {user_id}")
                self.logger.info(f"[REFLECTION_SUMMARY] Window: {window_start} to {window_end}")
                
                # Filter lessons within window (handle timezone-aware datetimes)
                lessons_in_window = []
                for lesson in lessons:
                    # Ensure both datetimes are timezone-aware for comparison
                    lesson_created = lesson.created_at
                    if lesson_created.tzinfo is None:
                        from datetime import timezone
                        lesson_created = lesson_created.replace(tzinfo=timezone.utc)
                    
                    self.logger.info(f"[REFLECTION_SUMMARY] Lesson {lesson.lesson_id} created_at: {lesson_created}, in_window: {lesson_created >= window_start and lesson_created <= window_end}")
                    
                    if lesson_created >= window_start and lesson_created <= window_end:
                        lessons_in_window.append(lesson)
                
                self.logger.info(f"[REFLECTION_SUMMARY] Filtered to {len(lessons_in_window)} lessons in window")
                
                # Calculate statistics
                lessons_applied = sum(1 for lesson in lessons_in_window if lesson.applied_at is not None)
                
                # Calculate average confidence
                avg_confidence = None
                if lessons_in_window:
                    confidences = [lesson.confidence for lesson in lessons_in_window if lesson.confidence is not None]
                    if confidences:
                        avg_confidence = sum(confidences) / len(confidences)
                
                # Get recent lessons
                recent_lessons_data = []
                for lesson in lessons_in_window[:recent_lessons_limit]:
                    recent_lessons_data.append({
                        "lesson_id": lesson.lesson_id,
                        "user_id": lesson.user_id,
                        "lesson_type": lesson.lesson_type,
                        "target_kind": lesson.target_kind,
                        "target_id": lesson.target_id,
                        "summary_text": lesson.summary_text,
                        "confidence": lesson.confidence,
                        "scope": lesson.scope,
                        "status": lesson.status,
                        "applied_at": lesson.applied_at.isoformat() if lesson.applied_at and hasattr(lesson.applied_at, 'isoformat') else (str(lesson.applied_at) if lesson.applied_at else None),
                        "source_reflection_run_id": lesson.source_reflection_run_id,
                        "created_at": lesson.created_at.isoformat() if hasattr(lesson.created_at, 'isoformat') else str(lesson.created_at),
                        "updated_at": lesson.updated_at.isoformat() if hasattr(lesson.updated_at, 'isoformat') else str(lesson.updated_at),
                    })
                
                return {
                    "user_id": user_id,
                    "window_days": window_days,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "reflections": len(runs_in_window),
                    "lessons_total": len(lessons_in_window),
                    "lessons_applied": lessons_applied,
                    "avg_confidence": avg_confidence,
                    "recent_lessons": recent_lessons_data,
                }
            
        except Exception as e:
            self.logger.error(f"Failed to get reflection summary: {e}", exc_info=True)
            return {"error": "AGENCY_REFLECTION_SUMMARY_FAILED", "message": str(e)}
