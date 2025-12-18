"""
Agency API Router

REST API endpoints for agency system - intentions, goals, values, policies, and consents.
Based on agency-metrics.md user-facing metrics.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated, Optional, List
from datetime import datetime
import json

from backend.api.conversation.dependencies import get_current_user
from backend.api.agency.models import (
    IntentionSetResponse,
    CuriosityStatusResponse,
    ValueProfileResponse,
    UpdateValueProfileRequest,
    PolicyListResponse,
    PolicyRuleResponse,
    ConsentRequest,
    ConsentResponse,
    ConsentListResponse,
    AgencyStateResponse,
    CreateGoalRequest,
    GoalResponse,
    GoalListResponse,
    UpdateGoalRequest,
    GoalSummary,
    CuriosityOpportunity,
    CuriosityLevel,
    GoalOrigin,
    GoalStatus,
    GoalPriority,
    PolicyEffect,
)
from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.ai.agency import AgencyEngine
from aico.ai.agency.values_ethics import ValuesEthicsService, ProactiveBehaviorLevel
from aico.core.paths import get_default_database_path
from aico.data.libsql import EncryptedLibSQLConnection
from aico.security import AICOKeyManager
from aico.ai import ai_registry

logger = get_logger("backend", "api.agency")
router = APIRouter()


# ============================================================================
# Dependencies
# ============================================================================

async def get_agency_engine() -> AgencyEngine:
    """Get AgencyEngine instance from global ai_registry (with LLM client injected)"""
    try:
        # Get the global AgencyEngine instance that has LLM client injected during startup
        engine = ai_registry.get("agency")
        
        if not engine:
            raise HTTPException(
                status_code=500,
                detail="AgencyEngine not available in ai_registry - backend may not be fully initialized"
            )
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to get AgencyEngine from registry: {e}")
        raise HTTPException(status_code=500, detail=f"Agency service unavailable: {str(e)}")


async def get_values_ethics_service() -> ValuesEthicsService:
    """Get ValuesEthicsService instance"""
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        # Get encrypted database connection
        db_path = get_default_database_path()
        key_manager = AICOKeyManager(config)
        
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        else:
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                key_manager._cache_session(master_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            else:
                raise HTTPException(status_code=500, detail="Database authentication failed")
        
        db = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        service = ValuesEthicsService(db)
        
        return service
        
    except Exception as e:
        logger.error(f"Failed to initialize ValuesEthicsService: {e}")
        raise HTTPException(status_code=500, detail=f"Values/Ethics service unavailable: {str(e)}")


# ============================================================================
# Intention Set Endpoints
# ============================================================================

@router.get("/intentions", response_model=IntentionSetResponse)
async def get_intention_set(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    limit: int = Query(10, ge=1, le=50, description="Maximum number of intentions to return")
):
    """
    Get the active intention set - what AICO is currently working on.
    
    Returns the primary focus intention and list of active intentions with scores.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get intention set from engine
        intention_set = await engine.get_intention_set(user_id)
        
        # Limit results
        intentions = intention_set.intentions[:limit]
        
        # Fetch actual Goal objects for each intention
        active_intentions = []
        for intention in intentions:
            goal = await engine.get_goal(intention.goal_id)
            if goal:
                active_intentions.append(
                    GoalSummary(
                        goal_id=goal.goal_id,
                        title=goal.title,
                        description=goal.description,
                        origin=GoalOrigin(goal.origin.value),
                        priority=GoalPriority(goal.priority.value),
                        status=GoalStatus(goal.status.value),
                        score=intention.arbiter_score,
                        priority_band=intention.priority_band.value,
                        created_at=goal.created_at,
                        metadata=goal.metadata
                    )
                )
        
        # Get hobby goals
        hobby_goals = [g for g in active_intentions if g.origin == GoalOrigin.HOBBY]
        
        # Count all open goals
        all_goals = await engine.list_goals_for_user(user_id)
        open_goals = [g for g in all_goals if g.status in [GoalStatus.PENDING, GoalStatus.ACTIVE]]
        
        return IntentionSetResponse(
            user_id=user_id,
            primary_focus=active_intentions[0] if active_intentions else None,
            active_intentions=active_intentions,
            open_goals_total=len(open_goals),
            hobby_goals_active=hobby_goals,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get intention set: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Curiosity Endpoints
# ============================================================================

@router.get("/curiosity", response_model=CuriosityStatusResponse)
async def get_curiosity_status(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)]
):
    """
    Get current curiosity status - what AICO is curious about.
    
    Returns curiosity level and top curiosity opportunities.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get intention set to analyze curiosity goals
        intention_set = await engine.get_intention_set(user_id)
        
        # Fetch goals and filter for curiosity-driven ones
        curiosity_goals = []
        for intention in intention_set.intentions:
            goal = await engine.get_goal(intention.goal_id)
            if goal and goal.origin.value == "curiosity":
                curiosity_goals.append((intention, goal))
        
        # Determine curiosity level based on active curiosity goals
        if len(curiosity_goals) >= 3:
            curiosity_level = CuriosityLevel.HIGH
        elif len(curiosity_goals) >= 1:
            curiosity_level = CuriosityLevel.MEDIUM
        else:
            curiosity_level = CuriosityLevel.LOW
        
        # Extract curiosity opportunities from metadata
        opportunities = []
        for intention, goal in curiosity_goals[:3]:  # Top 3
            if "curiosity_type" in goal.metadata:
                opportunities.append(
                    CuriosityOpportunity(
                        theme=goal.title,
                        description=goal.description or "",
                        intensity=goal.metadata.get("curiosity_score", 0.5),
                        signal_type=goal.metadata.get("curiosity_type", "unknown")
                    )
                )
        
        return CuriosityStatusResponse(
            user_id=user_id,
            curiosity_level=curiosity_level,
            curiosity_opportunities=opportunities,
            curiosity_goals_active=len(curiosity_goals),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get curiosity status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Value Profile Endpoints
# ============================================================================

@router.get("/profile", response_model=ValueProfileResponse)
async def get_value_profile(
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    Get user value profile - curiosity settings, proactive level, sensitive areas.
    """
    try:
        user_id = user["user_uuid"]
        profile = service._get_or_create_profile(user_id)
        
        return ValueProfileResponse(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            curiosity_intensity=profile.curiosity_intensity,
            proactive_behavior_level=profile.proactive_behavior_level,
            sensitive_life_areas=profile.sensitive_life_areas,
            allowed_curiosity_domains=profile.allowed_curiosity_domains
        )
        
    except Exception as e:
        logger.error(f"Failed to get value profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile", response_model=ValueProfileResponse)
async def update_value_profile(
    request: UpdateValueProfileRequest,
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    Update user value profile settings.
    """
    try:
        user_id = user["user_uuid"]
        profile = service._get_or_create_profile(user_id)
        
        # Apply updates
        if request.curiosity_intensity is not None:
            profile.curiosity_intensity = request.curiosity_intensity
        
        if request.proactive_behavior_level is not None:
            profile.proactive_behavior_level = request.proactive_behavior_level
        
        if request.add_sensitive_areas:
            for area in request.add_sensitive_areas:
                if area not in profile.sensitive_life_areas:
                    profile.sensitive_life_areas.append(area)
        
        if request.remove_sensitive_areas:
            profile.sensitive_life_areas = [
                area for area in profile.sensitive_life_areas
                if area not in request.remove_sensitive_areas
            ]
        
        # Save to database
        service.db.execute(
            """
            UPDATE ethics_value_profiles 
            SET curiosity_intensity = ?, 
                proactive_behavior_level = ?,
                sensitive_life_areas = ?,
                updated_at = ?
            WHERE profile_id = ?
            """,
            (
                profile.curiosity_intensity,
                profile.proactive_behavior_level.value,
                json.dumps(profile.sensitive_life_areas),
                datetime.utcnow().isoformat(),
                profile.profile_id
            )
        )
        service.db.commit()
        
        return ValueProfileResponse(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            curiosity_intensity=profile.curiosity_intensity,
            proactive_behavior_level=profile.proactive_behavior_level,
            sensitive_life_areas=profile.sensitive_life_areas,
            allowed_curiosity_domains=profile.allowed_curiosity_domains
        )
        
    except Exception as e:
        logger.error(f"Failed to update value profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Policy Endpoints
# ============================================================================

@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)],
    target_type: Optional[str] = Query(None, description="Filter by target type")
):
    """
    List policy rules - what's allowed, warned, or blocked.
    """
    try:
        query = "SELECT * FROM ethics_policy_rules WHERE enabled = 1"
        params = []
        
        if target_type:
            query += " AND target_type = ?"
            params.append(target_type)
        
        query += " ORDER BY priority ASC"
        
        cursor = service.db.execute(query, tuple(params))
        policies = cursor.fetchall()
        
        policy_list = [
            PolicyRuleResponse(
                rule_id=p[0],
                rule_name=p[1],
                target_type=p[2],
                effect=PolicyEffect(p[4]),
                scope=p[8],
                priority=p[6],
                conditions=json.loads(p[3]) if p[3] and isinstance(p[3], str) else (p[3] if p[3] else {}),
                user_message=p[5],
                enabled=bool(p[7])
            )
            for p in policies
        ]
        
        return PolicyListResponse(
            policies=policy_list,
            total=len(policy_list)
        )
        
    except Exception as e:
        logger.error(f"Failed to list policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Consent Endpoints
# ============================================================================

@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    request: ConsentRequest,
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    Grant or deny consent for a specific action.
    """
    try:
        user_id = user["user_uuid"]
        consent_id = f"consent-{user_id}-{datetime.utcnow().timestamp()}"
        
        service.db.execute(
            """
            INSERT INTO consent_records (consent_id, user_id, consent_scope, decision, granted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (consent_id, user_id, json.dumps(request.scope), request.decision, datetime.utcnow().isoformat())
        )
        service.db.commit()
        
        return ConsentResponse(
            consent_id=consent_id,
            user_id=user_id,
            scope=request.scope,
            decision=request.decision,
            granted_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to grant consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent", response_model=ConsentListResponse)
async def list_consents(
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    List user's consents.
    """
    try:
        user_id = user["user_uuid"]
        
        cursor = service.db.execute(
            "SELECT consent_id, user_id, consent_scope, decision, granted_at FROM consent_records WHERE user_id = ? ORDER BY granted_at DESC",
            (user_id,)
        )
        consents = cursor.fetchall()
        
        consent_list = [
            ConsentResponse(
                consent_id=c[0],
                user_id=c[1],
                scope=json.loads(c[2]) if c[2] else {},
                decision=c[3],
                granted_at=datetime.fromisoformat(c[4]) if c[4] else datetime.utcnow()
            )
            for c in consents
        ]
        
        return ConsentListResponse(
            consents=consent_list,
            total=len(consent_list)
        )
        
    except Exception as e:
        logger.error(f"Failed to list consents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/consent/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    consent_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    Revoke a consent.
    """
    try:
        user_id = user["user_uuid"]
        
        service.db.execute(
            "UPDATE consent_records SET decision = ? WHERE consent_id = ? AND user_id = ?",
            ("denied", consent_id, user_id)
        )
        service.db.commit()
        
    except Exception as e:
        logger.error(f"Failed to revoke consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Combined State Endpoint
# ============================================================================

@router.get("/state", response_model=AgencyStateResponse)
async def get_agency_state(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    service: Annotated[ValuesEthicsService, Depends(get_values_ethics_service)]
):
    """
    Get complete agency state - intentions, curiosity, profile, and pending consents.
    
    This is a convenience endpoint that combines multiple agency metrics.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get all components in parallel
        intention_set_task = get_intention_set(user, engine, limit=10)
        curiosity_task = get_curiosity_status(user, engine)
        profile_task = get_value_profile(user, service)
        
        intention_set, curiosity_status, value_profile = await asyncio.gather(
            intention_set_task,
            curiosity_task,
            profile_task
        )
        
        # Get pending consent actions (goals/signals that need consent)
        # This would require querying for blocked actions - placeholder for now
        consent_required_actions = []
        
        return AgencyStateResponse(
            user_id=user_id,
            intention_set=intention_set,
            curiosity_status=curiosity_status,
            value_profile=value_profile,
            consent_required_actions=consent_required_actions,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get agency state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
