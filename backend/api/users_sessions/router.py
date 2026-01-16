"""
Users & Sessions API Router

REST API endpoints for user and session management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from datetime import datetime, timedelta, timezone
import logging
from aico.core.logging import get_logger
from backend.api.users_sessions.schemas import (
    UsersListResponse,
    SessionsListResponse,
    UserDetailResponse,
    SessionStatsResponse,
    UserProfile,
    UserWithSessions,
    SessionWithUser,
    SessionDetail,
    UserCredentials,
    DeviceInfo,
    SessionStatistics,
)
from pydantic import BaseModel
from backend.api.system.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

logger = get_logger("backend.api.users_sessions")

router = APIRouter()


def format_time_remaining(expires_at: str) -> str:
    """Format time remaining until expiration"""
    try:
        expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        time_diff = expiry_time - datetime.utcnow()
        
        if time_diff.total_seconds() < 0:
            return "Expired"
        elif time_diff.total_seconds() < 60:
            return f"{int(time_diff.total_seconds())}s"
        elif time_diff.total_seconds() < 3600:
            minutes = int(time_diff.total_seconds() / 60)
            return f"{minutes}m"
        elif time_diff.total_seconds() < 86400:
            hours = int(time_diff.total_seconds() / 3600)
            return f"{hours}h"
        else:
            days = int(time_diff.total_seconds() / 86400)
            return f"{days}d"
    except:
        return "Unknown"


def format_last_activity(timestamp: str) -> str:
    """Format last activity timestamp"""
    try:
        activity_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_diff = datetime.utcnow() - activity_time
        
        if time_diff.total_seconds() < 60:
            return "Active now"
        elif time_diff.total_seconds() < 3600:
            minutes = int(time_diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif time_diff.total_seconds() < 86400:
            hours = int(time_diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = int(time_diff.total_seconds() / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
    except:
        return timestamp


@router.get("/users", response_model=UsersListResponse)
async def get_users(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user_type: Optional[str] = Query(None, description="Filter by user type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_sessions: Optional[bool] = Query(None, description="Filter users with active sessions"),
) -> UsersListResponse:
    """
    Get list of users with session information.
    
    Query Parameters:
    - user_type: Filter by user type (person, system, admin)
    - is_active: Filter by active status
    - has_sessions: Filter users with active sessions
    """
    try:
        # Get all users from repository
        filters = {}
        if user_type:
            filters["user_type"] = user_type
        if is_active is not None:
            filters["is_active"] = is_active
        
        all_users = await uow.users.list(filters=filters, limit=10000)
        
        # Get all active sessions
        all_sessions = await uow.sessions.list(filters={"is_active": True}, limit=10000)
        
        # Group sessions by user
        sessions_by_user = {}
        for session in all_sessions:
            if session.user_uuid not in sessions_by_user:
                sessions_by_user[session.user_uuid] = []
            sessions_by_user[session.user_uuid].append(session)
        
        # Build result
        users = []
        active_users_count = 0
        
        for user_profile in all_users:
            user_sessions = sessions_by_user.get(user_profile.uuid, [])
            session_count = len(user_sessions)
            
            # Apply has_sessions filter
            if has_sessions and session_count == 0:
                continue
            
            if session_count > 0:
                active_users_count += 1
            
            # Get last activity from sessions
            last_activity = None
            if user_sessions:
                latest_session = max(user_sessions, key=lambda s: s.created_at if s.created_at else datetime.min)
                last_activity = latest_session.created_at
            
            users.append(UserWithSessions(
                uuid=user_profile.uuid,
                full_name=user_profile.full_name,
                nickname=user_profile.nickname,
                user_type=user_profile.user_type,
                is_active=user_profile.is_active,
                primary_language=user_profile.primary_language,
                created_at=user_profile.created_at.isoformat() if hasattr(user_profile.created_at, 'isoformat') else user_profile.created_at,
                updated_at=user_profile.updated_at.isoformat() if hasattr(user_profile.updated_at, 'isoformat') else user_profile.updated_at,
                active_session_count=session_count,
                total_session_count=len(user_sessions),
                last_activity=format_last_activity(last_activity.isoformat() if hasattr(last_activity, 'isoformat') else str(last_activity)) if last_activity else "Never"
            ))
        
        # Sort by last activity
        users.sort(key=lambda u: u.last_activity if u.last_activity != "Never" else "", reverse=True)
        
        return UsersListResponse(
            users=users,
            total_users=len(users),
            active_users=active_users_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get users list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


@router.get("/users/{user_uuid}", response_model=UserDetailResponse)
async def get_user_detail(
    user_uuid: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserDetailResponse:
    """
    Get detailed information for a specific user.
    
    Path Parameters:
    - user_uuid: User UUID
    """
    try:
        # Get user profile
        user_profile = await uow.users.get_by_id(user_uuid)
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_uuid} not found"
            )
        
        profile_response = UserProfile(
            uuid=user_profile.uuid,
            full_name=user_profile.full_name,
            nickname=user_profile.nickname,
            user_type=user_profile.user_type,
            is_active=user_profile.is_active,
            primary_language=user_profile.primary_language,
            created_at=user_profile.created_at.isoformat() if hasattr(user_profile.created_at, 'isoformat') else user_profile.created_at,
            updated_at=user_profile.updated_at.isoformat() if hasattr(user_profile.updated_at, 'isoformat') else user_profile.updated_at
        )
        
        # Get credentials info
        credentials = None
        cred_list = await uow.credentials.list(filters={"user_uuid": user_uuid}, limit=1)
        
        if cred_list:
            cred = cred_list[0]
            credentials = UserCredentials(
                failed_attempts=cred.failed_attempts,
                locked_until=cred.locked_until.isoformat() if hasattr(cred.locked_until, 'isoformat') else cred.locked_until if cred.locked_until else None,
                last_login=cred.last_login.isoformat() if hasattr(cred.last_login, 'isoformat') else cred.last_login if cred.last_login else None
            )
        
        # Get all sessions (active and expired)
        all_sessions = await uow.sessions.list(filters={"user_uuid": user_uuid}, limit=200)
        all_sessions.sort(key=lambda s: s.created_at if s.created_at else datetime.min, reverse=True)
        
        active_sessions = []
        for sess in all_sessions:
            active_sessions.append(SessionDetail(
                uuid=sess.uuid,
                user_uuid=sess.user_uuid,
                device_uuid=sess.device_uuid,
                session_type=sess.session_type,
                expires_at=sess.expires_at.isoformat() if hasattr(sess.expires_at, 'isoformat') else sess.expires_at,
                created_at=sess.created_at.isoformat() if hasattr(sess.created_at, 'isoformat') else sess.created_at,
                is_active=sess.is_active
            ))
        
        # Get devices for this user's sessions
        device_uuids = set(s.device_uuid for s in all_sessions if s.device_uuid)
        devices = []
        
        if device_uuids:
            all_devices = await uow.devices.list(limit=1000)
            user_devices = [d for d in all_devices if d.uuid in device_uuids]
            user_devices.sort(key=lambda d: d.last_seen if d.last_seen else datetime.min, reverse=True)
            
            for dev in user_devices:
                devices.append(DeviceInfo(
                    uuid=dev.uuid,
                    device_name=dev.device_name,
                    device_type=dev.device_type,
                    platform=dev.platform,
                    last_seen=dev.last_seen.isoformat() if hasattr(dev.last_seen, 'isoformat') else dev.last_seen,
                    is_active=dev.is_active
                ))
        
        # Calculate statistics
        statistics = {
            "total_sessions": len(all_sessions),
            "active_sessions": sum(1 for s in all_sessions if s.is_active),
            "revoked_sessions": sum(1 for s in all_sessions if not s.is_active),
            "total_devices": len(devices)
        }
        
        return UserDetailResponse(
            user=profile_response,
            credentials=credentials,
            sessions=active_sessions,
            devices=devices,
            statistics=SessionStatistics(**statistics)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user detail: {str(e)}"
        )


@router.get("/sessions", response_model=SessionsListResponse)
async def get_sessions(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user_uuid: Optional[str] = Query(None, description="Filter by user UUID"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
) -> SessionsListResponse:
    """
    Get list of sessions with user information.
    
    Query Parameters:
    - user_uuid: Filter by user UUID
    - session_type: Filter by session type
    - is_active: Filter by active status
    - device_type: Filter by device type
    """
    try:
        # Get all sessions from repository
        filters = {}
        if user_uuid:
            filters["user_uuid"] = user_uuid
        if session_type:
            filters["session_type"] = session_type
        if is_active is not None:
            filters["is_active"] = is_active
        
        all_sessions = await uow.sessions.list(filters=filters, limit=1000)
        all_sessions.sort(key=lambda s: s.created_at if s.created_at else datetime.min, reverse=True)
        
        # Get all users
        all_users = await uow.users.list(limit=10000)
        users_by_uuid = {u.uuid: u for u in all_users}
        
        # Get all devices if needed for device_type filter
        if device_type:
            all_devices = await uow.devices.list(limit=10000)
            devices_by_uuid = {d.uuid: d for d in all_devices}
            # Filter sessions by device type
            all_sessions = [s for s in all_sessions if s.device_uuid and s.device_uuid in devices_by_uuid and devices_by_uuid[s.device_uuid].device_type == device_type]
        
        # Get devices for device info
        all_devices = await uow.devices.list(limit=10000)
        devices_by_uuid = {d.uuid: d for d in all_devices}
        
        sessions = []
        active_count = 0
        
        for sess in all_sessions:
            user_info = users_by_uuid.get(sess.user_uuid)
            device_info = devices_by_uuid.get(sess.device_uuid) if sess.device_uuid else None
            
            # Check if session is truly active
            if isinstance(sess.expires_at, datetime):
                expires_dt = sess.expires_at if sess.expires_at.tzinfo else sess.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_dt = datetime.fromisoformat(str(sess.expires_at).replace('Z', '+00:00'))
            now_utc = datetime.now(timezone.utc)
            is_truly_active = sess.is_active and expires_dt > now_utc
            
            if is_truly_active:
                active_count += 1
            
            sessions.append(SessionWithUser(
                uuid=sess.uuid,
                user_uuid=sess.user_uuid,
                device_uuid=sess.device_uuid,
                session_type=sess.session_type,
                expires_at=sess.expires_at.isoformat() if hasattr(sess.expires_at, 'isoformat') else sess.expires_at,
                created_at=sess.created_at.isoformat() if hasattr(sess.created_at, 'isoformat') else sess.created_at,
                is_active=is_truly_active,
                time_remaining=format_time_remaining(sess.expires_at.isoformat() if hasattr(sess.expires_at, 'isoformat') else str(sess.expires_at)),
                user_full_name=user_info.full_name if user_info else "Unknown",
                user_nickname=user_info.nickname if user_info else "Unknown",
                user_type=user_info.user_type if user_info else "unknown",
                device_name=device_info.device_name if device_info else (sess.device_uuid or "Unknown"),
                device_type=device_info.device_type if device_info else "web"
            ))
        
        return SessionsListResponse(
            sessions=sessions,
            total_sessions=len(sessions),
            active_sessions=active_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get sessions list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )


@router.get("/statistics", response_model=SessionStatsResponse)
async def get_session_statistics(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> SessionStatsResponse:
    """
    Get session statistics and analytics.
    """
    try:
        # Get all sessions
        all_sessions = await uow.sessions.list(limit=10000)
        now = datetime.now(timezone.utc)
        
        # Calculate overall statistics
        total_sessions = len(all_sessions)
        active_sessions = sum(1 for s in all_sessions if s.is_active and s.expires_at and s.expires_at > now)
        expired_sessions = sum(1 for s in all_sessions if not s.is_active or (s.expires_at and s.expires_at <= now))
        
        # Get sessions by type (only active, non-expired)
        active_valid_sessions = [s for s in all_sessions if s.is_active and s.expires_at and s.expires_at > now]
        sessions_by_type = {}
        for session in active_valid_sessions:
            session_type = session.session_type or 'unknown'
            sessions_by_type[session_type] = sessions_by_type.get(session_type, 0) + 1
        
        # Get sessions by device type
        all_devices = await uow.devices.list(limit=10000)
        devices_by_uuid = {d.uuid: d for d in all_devices}
        
        sessions_by_device_type = {}
        for session in active_valid_sessions:
            if session.device_uuid and session.device_uuid in devices_by_uuid:
                device_type = devices_by_uuid[session.device_uuid].device_type or 'unknown'
            else:
                device_type = 'unknown'
            sessions_by_device_type[device_type] = sessions_by_device_type.get(device_type, 0) + 1
        
        # Get recent activity (last 10 sessions)
        sorted_sessions = sorted(all_sessions, key=lambda s: s.created_at if s.created_at else datetime.min, reverse=True)[:10]
        
        # Get users for recent sessions
        all_users = await uow.users.list(limit=10000)
        users_by_uuid = {u.uuid: u for u in all_users}
        
        recent_activity = []
        for session in sorted_sessions:
            user_info = users_by_uuid.get(session.user_uuid)
            device_info = devices_by_uuid.get(session.device_uuid) if session.device_uuid else None
            
            recent_activity.append({
                "session_uuid": session.uuid,
                "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
                "user_name": user_info.full_name if user_info else "Unknown",
                "session_type": session.session_type or "unknown",
                "device_type": device_info.device_type if device_info else 'unknown'
            })
        
        return SessionStatsResponse(
            statistics=SessionStatistics(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                expired_sessions=expired_sessions,
                sessions_by_type=sessions_by_type,
                sessions_by_device_type=sessions_by_device_type
            ),
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Failed to get session statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session statistics: {str(e)}"
        )


class RevokeSessionRequest(BaseModel):
    """Request to revoke a session"""
    reason: Optional[str] = None


class LockUserRequest(BaseModel):
    """Request to lock/unlock a user account"""
    lock: bool
    reason: Optional[str] = None
    duration_hours: Optional[int] = None  # How long to lock (None = indefinite)


@router.delete("/sessions/{session_uuid}", status_code=204)
async def revoke_session(
    session_uuid: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    request: RevokeSessionRequest = Body(default=RevokeSessionRequest()),
):
    """
    Revoke a session by marking it as inactive.
    
    This will immediately terminate the user's access for this session.
    """
    try:
        # Check if session exists
        session = await uow.sessions.get_by_id(session_uuid)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_uuid} not found"
            )
        
        session_user_uuid = session.user_uuid
        is_active = session.is_active
        
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is already inactive"
            )
        
        # Revoke the session
        session.is_active = False
        await uow.sessions.update(session)
        await uow.commit()
        
        logger.info(
            f"Session revoked: {session_uuid} for user {session_user_uuid} by {user.get('user_uuid')}",
            extra={
                "session_uuid": session_uuid,
                "user_uuid": session_user_uuid,
                "revoked_by": user.get('user_uuid'),
                "reason": request.reason
            }
        )
        
        return {
            "success": True,
            "message": "Session revoked successfully",
            "session_uuid": session_uuid
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke session: {str(e)}"
        )


@router.delete("/users/{user_uuid}/sessions", status_code=200)
async def revoke_all_user_sessions(
    user_uuid: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    request: RevokeSessionRequest = Body(default=RevokeSessionRequest()),
) -> dict:
    """
    Revoke all active sessions for a specific user.
    """
    try:
        # Check if user exists
        user_result = await uow.users.get_by_id(user_uuid)
        
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_uuid} not found"
            )
        
        # Get count of active sessions
        active_sessions = await uow.sessions.list(filters={"user_uuid": user_uuid, "is_active": True}, limit=10000)
        active_count = len(active_sessions)
        
        if active_count == 0:
            return {
                "success": True,
                "message": "No active sessions to revoke",
                "revoked_count": 0
            }
        
        # Revoke all active sessions
        for session in active_sessions:
            session.is_active = False
            await uow.sessions.update(session)
        await uow.commit()
        
        logger.info(
            f"All sessions revoked for user {user_uuid} by {user.get('user_uuid')}",
            extra={
                "user_uuid": user_uuid,
                "revoked_by": user.get('user_uuid'),
                "session_count": active_count,
                "reason": request.reason
            }
        )
        
        return {
            "success": True,
            "message": f"Revoked {active_count} session(s) successfully",
            "revoked_count": active_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke all sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke all sessions: {str(e)}"
        )


@router.delete("/users/{user_uuid}/sessions/expired", status_code=200)
async def cleanup_expired_sessions(
    user_uuid: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> dict:
    """
    Delete all expired sessions for a specific user.
    """
    try:
        # Check if user exists
        user_result = await uow.users.get_by_id(user_uuid)
        
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_uuid} not found"
            )
        
        # Get count of expired sessions
        all_sessions = await uow.sessions.list(filters={"user_uuid": user_uuid}, limit=10000)
        now = datetime.utcnow()
        expired_sessions = [
            s for s in all_sessions 
            if not s.is_active or (s.expires_at and s.expires_at <= now)
        ]
        expired_count = len(expired_sessions)
        
        if expired_count == 0:
            return {
                "success": True,
                "message": "No expired sessions to clean up",
                "deleted_count": 0
            }
        
        # Delete expired sessions
        for session in expired_sessions:
            await uow.sessions.delete(session.uuid)
        await uow.commit()
        
        logger.info(
            f"Cleaned up expired sessions for user {user_uuid} by {user.get('user_uuid')}",
            extra={
                "user_uuid": user_uuid,
                "cleaned_by": user.get('user_uuid'),
                "session_count": expired_count
            }
        )
        
        return {
            "success": True,
            "message": f"Deleted {expired_count} expired session(s)",
            "deleted_count": expired_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup expired sessions: {str(e)}"
        )


@router.post("/users/{user_uuid}/lock", status_code=200)
async def lock_unlock_user(
    user_uuid: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    request: LockUserRequest = Body(...),
) -> dict:
    """
    Lock or unlock a user account.
    """
    try:
        # Check if user exists
        user_result = await uow.users.get_by_id(user_uuid)
        
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_uuid} not found"
            )
        
        # Check if credentials exist
        cred_list = await uow.credentials.list(filters={"user_uuid": user_uuid}, limit=1)
        
        if not cred_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User credentials not found for {user_uuid}"
            )
        
        if request.lock:
            # Lock the account
            cred = cred_list[0]
            
            if request.duration_hours:
                # Lock for specific duration
                cred.locked_until = datetime.utcnow() + timedelta(hours=request.duration_hours)
            else:
                # Lock indefinitely (far future date)
                cred.locked_until = datetime.utcnow() + timedelta(days=365*10)
            
            await uow.credentials.update(cred)
            
            # Also revoke all active sessions
            active_sessions = await uow.sessions.list(filters={"user_uuid": user_uuid, "is_active": True}, limit=10000)
            for session in active_sessions:
                session.is_active = False
                await uow.sessions.update(session)
            
            locked_until = cred.locked_until.isoformat() if hasattr(cred.locked_until, 'isoformat') else str(cred.locked_until)
            
            message = f"User account locked until {locked_until}" if request.duration_hours else "User account locked indefinitely"
        else:
            # Unlock the account
            cred = cred_list[0]
            cred.locked_until = None
            cred.failed_attempts = 0
            await uow.credentials.update(cred)
            message = "User account unlocked successfully"
        
        await uow.commit()
        
        logger.info(
            f"User {'locked' if request.lock else 'unlocked'}: {user_uuid} by {user.get('user_uuid')}",
            extra={
                "user_uuid": user_uuid,
                "action": "lock" if request.lock else "unlock",
                "performed_by": user.get('user_uuid'),
                "reason": request.reason,
                "duration_hours": request.duration_hours if request.lock else None
            }
        )
        
        return {
            "success": True,
            "message": message,
            "locked": request.lock
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to lock/unlock user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lock/unlock user: {str(e)}"
        )
