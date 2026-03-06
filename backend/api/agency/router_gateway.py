"""
Agency Gateway Router - HTTP termination that proxies to core via NATS.

Provides Studio-facing agency endpoints in gateway mode.
"""

from typing import Annotated, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.dependencies import get_current_user
from backend.api_gateway.core.nats_client import get_gateway_nats_client, GatewayNATSClient
from backend.api.agency.models import (
    AgencyStateResponse,
    IntentionSetResponse,
    EventsListResponse,
    CuriosityStatusResponse,
    ValueProfileResponse,
    UpdateValueProfileRequest,
    PolicyListResponse,
    ConsentRequest,
    ConsentResponse,
    ConsentListResponse,
    GoalListResponse,
    GoalResponse,
    GoalDetailResponse,
    ReflectionRunsListResponse,
    LessonListResponse,
    SelfModelListResponse,
    SkillPerformanceResponse,
    ReflectionSummaryResponse,
)

router = APIRouter()


@router.get("/agency/state", response_model=AgencyStateResponse)
async def get_agency_state(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get complete agency state - intentions, curiosity, profile, and pending consents.
    
    Gateway proxy to core via NATS (agency.state).
    """
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Technical users are excluded from agency state
        if user.get("is_technical"):
            raise HTTPException(
                status_code=403,
                detail="Technical users are excluded from agency state"
            )
        
        # Proxy to core via NATS
        response_data = await nats_client.request_agency_state(user_id=user_id)
        
        # Check for errors in response
        if response_data.get("error"):
            error_code = response_data.get("error")
            message = response_data.get("message", "Unknown error")
            
            # Map known error codes to HTTP status codes
            if error_code == "AGENCY_ENGINE_NOT_INITIALIZED":
                raise HTTPException(status_code=503, detail=message)
            elif error_code == "AGENCY_STATE_FAILED":
                raise HTTPException(status_code=500, detail=message)
            else:
                raise HTTPException(status_code=500, detail=message)
        
        return AgencyStateResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agency state: {str(e)}"
        )


@router.get("/agency/intentions", response_model=IntentionSetResponse)
async def get_intention_set(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    limit: int = Query(10, ge=1, le=50),
):
    """Get active intention set. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_intentions(user_id=user_id, limit=limit)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to get intentions"))
        
        return IntentionSetResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get intention set: {str(e)}")


@router.get("/agency/events", response_model=EventsListResponse)
async def list_events(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List agency events. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_events(user_id=user_id, limit=limit, offset=offset)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list events"))
        
        return EventsListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")


@router.get("/agency/curiosity", response_model=CuriosityStatusResponse)
async def get_curiosity_status(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get curiosity status. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_curiosity(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to get curiosity status"))
        
        return CuriosityStatusResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get curiosity status: {str(e)}")


@router.get("/agency/profile", response_model=ValueProfileResponse)
async def get_value_profile(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get value profile. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_profile(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to get value profile"))
        
        return ValueProfileResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get value profile: {str(e)}")


@router.put("/agency/profile", response_model=ValueProfileResponse)
async def update_value_profile(
    request: UpdateValueProfileRequest,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Update value profile. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_profile_update(user_id=user_id, update_data=request.dict(exclude_unset=True))
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to update value profile"))
        
        return ValueProfileResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update value profile: {str(e)}")


@router.get("/agency/policies", response_model=PolicyListResponse)
async def list_policies(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """List policy rules. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_policies(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list policies"))
        
        return PolicyListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list policies: {str(e)}")


@router.post("/agency/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    request: ConsentRequest,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Grant consent. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_consent_grant(user_id=user_id, consent_data=request.dict())
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to grant consent"))
        
        return ConsentResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grant consent: {str(e)}")


@router.get("/agency/consent", response_model=ConsentListResponse)
async def list_consents(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """List consents. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_consents(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list consents"))
        
        return ConsentListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list consents: {str(e)}")


@router.delete("/agency/consent/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    consent_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Revoke consent. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_consent_revoke(user_id=user_id, consent_id=consent_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to revoke consent"))
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke consent: {str(e)}")


@router.get("/agency/goals", response_model=GoalListResponse)
async def list_goals(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    status: Optional[str] = None,
    origin: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
):
    """List goals. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_goals(
            user_id=user_id, status=status, origin=origin, priority=priority, limit=limit, page=page
        )
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list goals"))
        
        return GoalListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list goals: {str(e)}")


@router.get("/agency/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get goal details. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_goal(user_id=user_id, goal_id=goal_id)
        if response_data.get("error"):
            raise HTTPException(status_code=404 if "not found" in response_data.get("message", "").lower() else 500, detail=response_data.get("message", "Failed to get goal"))
        
        return GoalResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get goal: {str(e)}")


@router.get("/agency/goals/{goal_id}/plans", response_model=GoalDetailResponse)
async def get_goal_plans(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get goal plans. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_goal_plans(user_id=user_id, goal_id=goal_id)
        if response_data.get("error"):
            raise HTTPException(status_code=404 if "not found" in response_data.get("message", "").lower() else 500, detail=response_data.get("message", "Failed to get goal plans"))
        
        return GoalDetailResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get goal plans: {str(e)}")


@router.post("/agency/goals/{goal_id}/replan")
async def replan_goal(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Replan goal. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_goal_replan(user_id=user_id, goal_id=goal_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to replan goal"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to replan goal: {str(e)}")


@router.post("/agency/skills/list")
async def list_skills(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """List skills. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_skills_list(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list skills"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")


@router.post("/agency/skills/info")
async def get_skill_info(
    request: Dict[str, Any],
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get skill info. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_skill_info(user_id=user_id, skill_id=request.get("skill_id"))
        if response_data.get("error"):
            raise HTTPException(status_code=404 if "not found" in response_data.get("message", "").lower() else 500, detail=response_data.get("message", "Failed to get skill info"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get skill info: {str(e)}")


@router.post("/agency/skills/invoke")
async def invoke_skill(
    request: Dict[str, Any],
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Invoke skill. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_skill_invoke(user_id=user_id, skill_data=request)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to invoke skill"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invoke skill: {str(e)}")


@router.post("/agency/connectivity/scan")
async def connectivity_scan(
    request: Dict[str, Any],
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Run connectivity scan. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_connectivity_scan(user_id=user_id, scan_data=request)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to run connectivity scan"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run connectivity scan: {str(e)}")


@router.post("/agency/tools/list")
async def list_tools(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """List tools. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_tools_list(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list tools"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/agency/tools/info")
async def get_tool_info(
    request: Dict[str, Any],
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get tool info. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_tool_info(user_id=user_id, tool_id=request.get("tool_id"))
        if response_data.get("error"):
            raise HTTPException(status_code=404 if "not found" in response_data.get("message", "").lower() else 500, detail=response_data.get("message", "Failed to get tool info"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tool info: {str(e)}")


@router.post("/agency/tools/invoke")
async def invoke_tool(
    request: Dict[str, Any],
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Invoke tool. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_tool_invoke(user_id=user_id, tool_data=request)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to invoke tool"))
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invoke tool: {str(e)}")


@router.get("/agency/reflection/runs", response_model=ReflectionRunsListResponse)
async def list_reflection_runs(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    limit: int = Query(50, ge=1, le=200),
):
    """List reflection runs. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_reflection_runs(user_id=user_id, limit=limit)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list reflection runs"))
        
        return ReflectionRunsListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reflection runs: {str(e)}")


@router.get("/agency/reflection/lessons", response_model=LessonListResponse)
async def list_reflection_lessons(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    limit: int = Query(50, ge=1, le=200),
):
    """List reflection lessons. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_reflection_lessons(user_id=user_id, limit=limit)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list reflection lessons"))
        
        return LessonListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reflection lessons: {str(e)}")


@router.get("/agency/reflection/self-model", response_model=SelfModelListResponse)
async def list_self_model(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """List self-model. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_reflection_self_model(user_id=user_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to list self-model"))
        
        return SelfModelListResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list self-model: {str(e)}")


@router.get("/agency/reflection/skills/{skill_id}/performance", response_model=SkillPerformanceResponse)
async def get_skill_performance(
    skill_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
):
    """Get skill performance. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_skill_performance(user_id=user_id, skill_id=skill_id)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to get skill performance"))
        
        return SkillPerformanceResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get skill performance: {str(e)}")


@router.get("/agency/reflection/summary", response_model=ReflectionSummaryResponse)
async def get_reflection_summary(
    user: Annotated[dict, Depends(get_current_user)],
    nats_client: Annotated[GatewayNATSClient, Depends(get_gateway_nats_client)],
    days: int = Query(30, ge=1, le=365),
    recent_lessons_limit: int = Query(10, ge=1, le=100),
):
    """Get reflection summary. Gateway proxy to core via NATS."""
    try:
        user_id = user.get("user_uuid")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        response_data = await nats_client.request_agency_reflection_summary(user_id=user_id, window_days=days, recent_lessons_limit=recent_lessons_limit)
        if response_data.get("error"):
            raise HTTPException(status_code=500, detail=response_data.get("message", "Failed to get reflection summary"))
        
        return ReflectionSummaryResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reflection summary: {str(e)}")
