"""
Users & Sessions API Router

REST API endpoints for user and session management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta

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
from backend.api.system.dependencies import get_current_user, get_db_connection

logger = get_logger("backend", "api.users_sessions")

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
    db_connection: Annotated[object, Depends(get_db_connection)],
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
        # Build query with filters
        query = """
            SELECT 
                p.uuid,
                p.full_name,
                p.nickname,
                p.user_type,
                p.is_active,
                p.primary_language,
                p.created_at,
                p.updated_at,
                COUNT(DISTINCT CASE WHEN s.is_active = 1 AND s.expires_at > datetime('now') THEN s.uuid END) as active_session_count,
                COUNT(DISTINCT s.uuid) as total_session_count,
                MAX(s.created_at) as last_activity,
                c.failed_attempts,
                c.locked_until,
                c.last_login
            FROM user_profiles p
            LEFT JOIN auth_sessions s ON p.uuid = s.user_uuid
            LEFT JOIN auth_user_credentials c ON p.uuid = c.user_uuid
            WHERE 1=1
        """
        params = []
        
        if user_type:
            query += " AND p.user_type = ?"
            params.append(user_type)
        
        if is_active is not None:
            query += " AND p.is_active = ?"
            params.append(1 if is_active else 0)
        
        query += " GROUP BY p.uuid, p.full_name, p.nickname, p.user_type, p.is_active, p.primary_language, p.created_at, p.updated_at, c.failed_attempts, c.locked_until, c.last_login"
        
        if has_sessions is not None:
            if has_sessions:
                query += " HAVING active_session_count > 0"
            else:
                query += " HAVING active_session_count = 0"
        
        query += " ORDER BY last_activity DESC NULLS LAST"
        
        result = db_connection.execute(query, params).fetchall()
        
        users = []
        active_users_count = 0
        
        for row in result:
            (uuid, full_name, nickname, user_type_val, is_active_val, primary_language, 
             created_at, updated_at, active_session_count, total_session_count, last_activity,
             failed_attempts, locked_until, last_login) = row
            
            if active_session_count > 0:
                active_users_count += 1
            
            # Build credentials info
            credentials = None
            if failed_attempts is not None:
                credentials = UserCredentials(
                    has_pin=True,
                    failed_attempts=failed_attempts or 0,
                    is_locked=locked_until is not None and datetime.fromisoformat(locked_until.replace('Z', '+00:00')) > datetime.utcnow() if locked_until else False,
                    locked_until=locked_until,
                    last_login=last_login
                )
            
            users.append(UserWithSessions(
                uuid=uuid,
                full_name=full_name,
                nickname=nickname,
                user_type=user_type_val,
                is_active=bool(is_active_val),
                primary_language=primary_language,
                created_at=created_at,
                updated_at=updated_at,
                active_session_count=active_session_count,
                total_session_count=total_session_count,
                last_activity=format_last_activity(last_activity) if last_activity else None,
                credentials=credentials
            ))
        
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
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> UserDetailResponse:
    """
    Get detailed information for a specific user.
    
    Path Parameters:
    - user_uuid: User UUID
    """
    try:
        # Get user profile
        user_result = db_connection.execute(
            """
            SELECT uuid, full_name, nickname, user_type, is_active, 
                   primary_language, created_at, updated_at
            FROM user_profiles
            WHERE uuid = ?
            """,
            [user_uuid]
        ).fetchone()
        
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_uuid} not found"
            )
        
        user_profile = UserProfile(
            uuid=user_result[0],
            full_name=user_result[1],
            nickname=user_result[2],
            user_type=user_result[3],
            is_active=bool(user_result[4]),
            primary_language=user_result[5],
            created_at=user_result[6],
            updated_at=user_result[7]
        )
        
        # Get credentials info
        credentials = None
        cred_result = db_connection.execute(
            """
            SELECT failed_attempts, locked_until, last_login
            FROM auth_user_credentials
            WHERE user_uuid = ?
            """,
            [user_uuid]
        ).fetchone()
        
        if cred_result:
            failed_attempts, locked_until, last_login = cred_result
            credentials = UserCredentials(
                has_pin=True,
                failed_attempts=failed_attempts or 0,
                is_locked=locked_until is not None and datetime.fromisoformat(locked_until.replace('Z', '+00:00')) > datetime.utcnow() if locked_until else False,
                locked_until=locked_until,
                last_login=last_login
            )
        
        # Get active sessions
        sessions_result = db_connection.execute(
            """
            SELECT uuid, user_uuid, device_uuid, session_type, 
                   expires_at, created_at, is_active
            FROM auth_sessions
            WHERE user_uuid = ? 
              AND is_active = 1 
              AND expires_at > datetime('now')
            ORDER BY created_at DESC
            """,
            [user_uuid]
        ).fetchall()
        
        active_sessions = []
        for sess_row in sessions_result:
            active_sessions.append(SessionDetail(
                uuid=sess_row[0],
                user_uuid=sess_row[1],
                device_uuid=sess_row[2],
                session_type=sess_row[3],
                expires_at=sess_row[4],
                created_at=sess_row[5],
                is_active=bool(sess_row[6]),
                time_remaining=format_time_remaining(sess_row[4])
            ))
        
        # Get devices
        devices_result = db_connection.execute(
            """
            SELECT DISTINCT d.uuid, d.device_name, d.device_type, d.platform, 
                   d.last_seen, d.is_active
            FROM auth_devices d
            JOIN auth_sessions s ON d.uuid = s.device_uuid
            WHERE s.user_uuid = ?
            ORDER BY d.last_seen DESC
            """,
            [user_uuid]
        ).fetchall()
        
        devices = []
        for dev_row in devices_result:
            devices.append(DeviceInfo(
                uuid=dev_row[0],
                device_name=dev_row[1],
                device_type=dev_row[2],
                platform=dev_row[3],
                last_seen=dev_row[4],
                is_active=bool(dev_row[5])
            ))
        
        # Calculate statistics
        stats_result = db_connection.execute(
            """
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN is_active = 1 AND expires_at > datetime('now') THEN 1 END) as active_sessions,
                COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired_sessions
            FROM auth_sessions
            WHERE user_uuid = ?
            """,
            [user_uuid]
        ).fetchone()
        
        statistics = {
            "total_sessions": stats_result[0],
            "active_sessions": stats_result[1],
            "expired_sessions": stats_result[2],
            "registered_devices": len(devices)
        }
        
        return UserDetailResponse(
            user=user_profile,
            credentials=credentials,
            active_sessions=active_sessions,
            devices=devices,
            statistics=statistics
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
    db_connection: Annotated[object, Depends(get_db_connection)],
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
        # Build query with filters
        query = """
            SELECT 
                s.uuid,
                s.user_uuid,
                s.device_uuid,
                s.session_type,
                s.expires_at,
                s.created_at,
                s.is_active,
                p.full_name,
                p.nickname,
                p.user_type,
                d.device_name,
                d.device_type
            FROM auth_sessions s
            JOIN user_profiles p ON s.user_uuid = p.uuid
            LEFT JOIN auth_devices d ON s.device_uuid = d.uuid
            WHERE 1=1
        """
        params = []
        
        if user_uuid:
            query += " AND s.user_uuid = ?"
            params.append(user_uuid)
        
        if session_type:
            query += " AND s.session_type = ?"
            params.append(session_type)
        
        if is_active is not None:
            if is_active:
                query += " AND s.is_active = 1 AND s.expires_at > datetime('now')"
            else:
                query += " AND (s.is_active = 0 OR s.expires_at <= datetime('now'))"
        
        if device_type:
            query += " AND d.device_type = ?"
            params.append(device_type)
        
        query += " ORDER BY s.created_at DESC LIMIT 1000"
        
        result = db_connection.execute(query, params).fetchall()
        
        sessions = []
        active_count = 0
        
        for row in result:
            (sess_uuid, user_uuid_val, device_uuid, session_type_val, expires_at, 
             created_at, is_active_val, full_name, nickname, user_type_val, 
             device_name, device_type_val) = row
            
            # Check if session is truly active
            is_truly_active = bool(is_active_val) and datetime.fromisoformat(expires_at.replace('Z', '+00:00')) > datetime.utcnow()
            
            if is_truly_active:
                active_count += 1
            
            sessions.append(SessionWithUser(
                uuid=sess_uuid,
                user_uuid=user_uuid_val,
                device_uuid=device_uuid,
                session_type=session_type_val,
                expires_at=expires_at,
                created_at=created_at,
                is_active=is_truly_active,
                time_remaining=format_time_remaining(expires_at),
                user_full_name=full_name,
                user_nickname=nickname,
                user_type=user_type_val,
                device_name=device_name,
                device_type=device_type_val
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
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> SessionStatsResponse:
    """
    Get session statistics and analytics.
    """
    try:
        # Get overall statistics
        stats_result = db_connection.execute(
            """
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN is_active = 1 AND expires_at > datetime('now') THEN 1 END) as active_sessions,
                COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired_sessions
            FROM auth_sessions
            """
        ).fetchone()
        
        # Get sessions by type
        type_result = db_connection.execute(
            """
            SELECT session_type, COUNT(*) as count
            FROM auth_sessions
            WHERE is_active = 1 AND expires_at > datetime('now')
            GROUP BY session_type
            """
        ).fetchall()
        
        sessions_by_type = {row[0]: row[1] for row in type_result}
        
        # Get sessions by device type
        device_result = db_connection.execute(
            """
            SELECT d.device_type, COUNT(DISTINCT s.uuid) as count
            FROM auth_sessions s
            LEFT JOIN auth_devices d ON s.device_uuid = d.uuid
            WHERE s.is_active = 1 AND s.expires_at > datetime('now')
            GROUP BY d.device_type
            """
        ).fetchall()
        
        sessions_by_device_type = {row[0] or 'unknown': row[1] for row in device_result}
        
        # Get recent activity (last 10 sessions)
        activity_result = db_connection.execute(
            """
            SELECT 
                s.uuid,
                s.created_at,
                p.full_name,
                s.session_type,
                d.device_type
            FROM auth_sessions s
            JOIN user_profiles p ON s.user_uuid = p.uuid
            LEFT JOIN auth_devices d ON s.device_uuid = d.uuid
            ORDER BY s.created_at DESC
            LIMIT 10
            """
        ).fetchall()
        
        recent_activity = []
        for row in activity_result:
            recent_activity.append({
                "session_uuid": row[0],
                "created_at": row[1],
                "user_name": row[2],
                "session_type": row[3],
                "device_type": row[4] or 'unknown'
            })
        
        statistics = SessionStatistics(
            total_sessions=stats_result[0],
            active_sessions=stats_result[1],
            expired_sessions=stats_result[2],
            sessions_by_type=sessions_by_type,
            sessions_by_device_type=sessions_by_device_type,
            average_session_duration=None  # Could be calculated if we track session end times
        )
        
        return SessionStatsResponse(
            statistics=statistics,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Failed to get session statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session statistics: {str(e)}"
        )
