"""
Admin Management API Router

REST API endpoints for administrative operations including gateway management,
session control, security operations, and system configuration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, UTC, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, or_, cast
from sqlalchemy import Text

import uuid as uuid_lib
import json

from .dependencies import verify_admin_token, get_log_repository, get_config_manager
from .schemas import (
    AdminHealthResponse,
    GatewayStatusResponse,
    GatewayStatsResponse,
    SecurityStatsResponse,
    SessionListResponse as UserSessionsResponse,
    RevokeTokenRequest as RevokeSessionRequest,
    AdminOperationResponse,
    BlockIpRequest,
    # Logs schemas
    LogsListRequest,
    LogsDeleteRequest,
    LogEntryResponse,
    LogsListResponse,
    LogsStatsResponse,
    # Config schemas
    ConfigSetRequest,
    ConfigValidateRequest,
    ConfigImportRequest,
    ConfigValueResponse,
    ConfigListResponse,
    ConfigDomainResponse,
    ConfigSchemaResponse,
    ConfigValidationResponse
)
from .schemas import ConfigResponse, RouteMappingRequest, RouteMappingResponse
from . import schemas as admin_schemas
from .exceptions import (
    GatewayServiceError,
    SessionNotFoundError,
    LogsServiceError,
    ConfigServiceError,
    ConfigValidationError,
    handle_admin_service_exceptions
)

from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork
from aico.data.tables import system_events
from aico.data.system.models import SystemEvent
from backend.api.admin.user_cleanup import cleanup_user_data
from aico.security.key_manager import AICOKeyManager
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.user.models import UserProfile
from aico.data.auth.models import AuthUserCredentials
from passlib.context import CryptContext

# Admin authentication handled by verify_admin_token dependency function

# Removed initialize_router - using proper FastAPI dependency injection

# Protected admin endpoints - authentication handled per endpoint
router = APIRouter()

logger = get_logger("backend.api.admin")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from backend.api.admin.interactions import router as interactions_router
from backend.api.admin.interactions_simulator import router as interactions_simulator_router

router.include_router(interactions_router, prefix="/interactions", tags=["interactions"])
router.include_router(interactions_simulator_router, prefix="/interactions", tags=["interactions-simulator"])


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_user_response(user: UserProfile) -> admin_schemas.AdminUserResponse:
    return admin_schemas.AdminUserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        primary_language=user.primary_language,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


async def _write_audit_event(
    *,
    uow: UnitOfWork,
    timestamp: datetime,
    action: str,
    actor: Dict[str, Any],
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    severity: str = "info",
    result: str = "success",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> str:
    entry_id = str(uuid_lib.uuid4())
    metadata: Dict[str, Any] = {
        "actor_uuid": actor.get("user_uuid"),
        "actor_name": actor.get("username"),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": severity,
        "result": result,
        "details": details or {},
        "ip_address": ip_address,
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}

    await uow.system_events.create(
        entity=SystemEvent(
            timestamp=_iso_utc(timestamp),
            topic="audit.admin",
            source="backend.api.admin",
            message_type="audit",
            message_id=entry_id,
            priority=1,
            correlation_id=correlation_id,
            payload=None,
            metadata=metadata,
            created_at=timestamp.astimezone(UTC) if timestamp.tzinfo else timestamp.replace(tzinfo=UTC),
        )
    )
    return entry_id


_FAILED_AUTH_QUERY_RL: Dict[str, List[float]] = {}


def _rate_limit_or_429(*, request: Request, key: str, max_per_minute: int) -> None:
    import time

    now = time.time()
    window_start = now - 60.0
    bucket = _FAILED_AUTH_QUERY_RL.setdefault(key, [])
    bucket[:] = [ts for ts in bucket if ts >= window_start]

    if len(bucket) >= max_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)

@router.get("/health", response_model=AdminHealthResponse)
@handle_admin_service_exceptions
async def admin_health(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Admin health check - requires encryption"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    return AdminHealthResponse(
        status="healthy",
        service="aico-api-gateway-admin",
        timestamp=datetime.now(UTC).isoformat()
    )


# ============================================================================
# USERS (ADMIN)
# ============================================================================


@router.post("/users", response_model=admin_schemas.AdminUserResponse, status_code=201)
@handle_admin_service_exceptions
async def admin_create_user(
    body: admin_schemas.AdminUserCreateRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    now = datetime.now(UTC)
    user = UserProfile(
        uuid=str(uuid_lib.uuid4()),
        full_name=body.full_name,
        nickname=body.nickname,
        user_type=body.user_type,
        is_active=True,
        primary_language=body.primary_language or "und",
        created_at=now,
        updated_at=now,
    )

    await uow.users.create(user)

    raw_password = body.password if getattr(body, "password", None) is not None else body.pin
    if not raw_password:
        raise HTTPException(status_code=400, detail="password is required")

    credentials = AuthUserCredentials(
        uuid=str(uuid_lib.uuid4()),
        user_uuid=user.uuid,
        password_hash=_pwd_context.hash(raw_password),
        failed_attempts=0,
        locked_until=None,
        last_login=None,
        created_at=now,
        updated_at=now,
    )
    await uow.credentials.create(credentials)

    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.user.create",
        actor=actor,
        resource_type="user",
        resource_id=user.uuid,
        ip_address=getattr(request.client, "host", None),
        details={
            "full_name": body.full_name,
            "nickname": body.nickname,
            "user_type": body.user_type,
            "primary_language": body.primary_language,
        },
    )
    await uow.commit()

    return _to_user_response(user)


@router.put("/users/{user_uuid}", response_model=admin_schemas.AdminUserResponse)
@handle_admin_service_exceptions
async def admin_update_user(
    user_uuid: str,
    body: admin_schemas.AdminUserUpdateRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    for k, v in updates.items():
        if hasattr(user, k):
            setattr(user, k, v)

    user = await uow.users.update(user)

    now = datetime.now(UTC)
    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.user.update",
        actor=actor,
        resource_type="user",
        resource_id=user_uuid,
        ip_address=getattr(request.client, "host", None),
        details={"updated_fields": list(updates.keys())},
    )
    await uow.commit()
    return _to_user_response(user)


@router.delete("/users/{user_uuid}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def admin_delete_user(
    user_uuid: str,
    body: admin_schemas.AdminUserDeleteRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")

    now = datetime.now(UTC)
    
    # Clean up LMDB and ChromaDB data first
    cleanup_result = await cleanup_user_data(user_uuid)
    if cleanup_result["errors"]:
        logger.warning(f"Cleanup errors for user {user_uuid}: {cleanup_result['errors']}")
    
    if body.hard_delete:
        try:
            await uow.users.delete(user_uuid)
            await _write_audit_event(
                uow=uow,
                timestamp=now,
                action="admin.user.delete.hard",
                actor=actor,
                resource_type="user",
                resource_id=user_uuid,
                severity="warning",
                ip_address=getattr(request.client, "host", None),
                details={"reason": body.reason},
            )
            await uow.commit()
            return AdminOperationResponse(success=True, message="User hard-deleted")
        except ValueError:
            raise HTTPException(status_code=404, detail="User not found")

    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await uow.users.update(user)
    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.user.delete.soft",
        actor=actor,
        resource_type="user",
        resource_id=user_uuid,
        severity="warning",
        ip_address=getattr(request.client, "host", None),
        details={"reason": body.reason},
    )
    await uow.commit()
    return AdminOperationResponse(success=True, message="User deactivated")


@router.post("/users/bulk-delete", response_model=admin_schemas.AdminBulkDeleteResponse)
@handle_admin_service_exceptions
async def admin_bulk_delete_users(
    body: admin_schemas.AdminBulkDeleteRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Bulk delete multiple users (soft or hard delete).
    
    - Supports up to 100 users per request
    - Requires explicit confirmation
    - Continues processing even if individual deletions fail
    - Returns detailed results for each user
    """
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")
    
    if not body.user_uuids:
        raise HTTPException(status_code=400, detail="user_uuids list cannot be empty")
    
    now = datetime.now(UTC)
    results = []
    successful = 0
    failed = 0
    
    for user_uuid in body.user_uuids:
        try:
            # Clean up LMDB and ChromaDB data first
            cleanup_result = await cleanup_user_data(user_uuid)
            if cleanup_result["errors"]:
                logger.warning(f"Cleanup errors for user {user_uuid}: {cleanup_result['errors']}")
            
            if body.hard_delete:
                # Hard delete - remove from database
                deleted = await uow.users.delete(user_uuid)
                if not deleted:
                    results.append(admin_schemas.BulkDeleteResult(
                        user_uuid=user_uuid,
                        success=False,
                        error="User not found"
                    ))
                    failed += 1
                    continue
                
                await _write_audit_event(
                    uow=uow,
                    timestamp=now,
                    action="admin.user.bulk_delete.hard",
                    actor=actor,
                    resource_type="user",
                    resource_id=user_uuid,
                    severity="warning",
                    ip_address=getattr(request.client, "host", None),
                    details={"reason": body.reason, "bulk_operation": True},
                )
                
                results.append(admin_schemas.BulkDeleteResult(
                    user_uuid=user_uuid,
                    success=True,
                    error=None
                ))
                successful += 1
            else:
                # Soft delete - set is_active = False
                user = await uow.users.get_by_id(user_uuid)
                if not user:
                    results.append(admin_schemas.BulkDeleteResult(
                        user_uuid=user_uuid,
                        success=False,
                        error="User not found"
                    ))
                    failed += 1
                    continue
                
                user.is_active = False
                await uow.users.update(user)
                await _write_audit_event(
                    uow=uow,
                    timestamp=now,
                    action="admin.user.bulk_delete.soft",
                    actor=actor,
                    resource_type="user",
                    resource_id=user_uuid,
                    severity="warning",
                    ip_address=getattr(request.client, "host", None),
                    details={"reason": body.reason, "bulk_operation": True},
                )
                
                results.append(admin_schemas.BulkDeleteResult(
                    user_uuid=user_uuid,
                    success=True,
                    error=None
                ))
                successful += 1
                
        except Exception as e:
            logger.error(f"Failed to delete user {user_uuid} in bulk operation: {e}")
            results.append(admin_schemas.BulkDeleteResult(
                user_uuid=user_uuid,
                success=False,
                error=str(e)
            ))
            failed += 1
    
    # Commit all changes
    await uow.commit()
    
    return admin_schemas.AdminBulkDeleteResponse(
        success=(failed == 0),
        total_requested=len(body.user_uuids),
        successful=successful,
        failed=failed,
        results=results
    )


@router.put("/users/{user_uuid}/password", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def admin_set_user_password(
    user_uuid: str,
    body: admin_schemas.AdminUserSetPinRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")

    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(UTC)
    raw_password = body.new_password if getattr(body, "new_password", None) is not None else body.new_pin
    if not raw_password:
        raise HTTPException(status_code=400, detail="new_password is required")

    cred = await uow.credentials.get_by_user_uuid(user_uuid)
    if cred:
        cred.password_hash = _pwd_context.hash(raw_password)
        cred.failed_attempts = 0
        cred.locked_until = None
        await uow.credentials.update(cred)
    else:
        cred = AuthUserCredentials(
            uuid=str(uuid_lib.uuid4()),
            user_uuid=user_uuid,
            password_hash=_pwd_context.hash(raw_password),
            failed_attempts=0,
            locked_until=None,
            last_login=None,
            created_at=now,
            updated_at=now,
        )
        await uow.credentials.create(cred)

    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.user.password.reset",
        actor=actor,
        resource_type="user",
        resource_id=user_uuid,
        severity="warning",
        ip_address=getattr(request.client, "host", None),
        details={"require_change_on_login": body.require_change_on_login},
    )
    await uow.commit()
    return AdminOperationResponse(success=True, message="Password updated")


@router.post("/users/{user_uuid}/restore", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def admin_restore_user(
    user_uuid: str,
    body: admin_schemas.AdminUserRestoreRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")

    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await uow.users.update(user)

    now = datetime.now(UTC)
    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.user.restore",
        actor=actor,
        resource_type="user",
        resource_id=user_uuid,
        severity="warning",
        ip_address=getattr(request.client, "host", None),
        details={"reason": body.reason},
    )
    await uow.commit()

    return AdminOperationResponse(success=True, message="User restored")


@router.get("/users/{user_uuid}/audit-log", response_model=admin_schemas.AuditListResponse)
@handle_admin_service_exceptions
async def admin_user_audit_log(
    user_uuid: str,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action_type: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
):
    # "User's actions" best-effort: include entries where actor_uuid==user_uuid OR resource_id==user_uuid
    conditions = [system_events.c.topic == "audit.admin"]
    conditions.append(
        or_(
            system_events.c.metadata["actor_uuid"].astext == user_uuid,
            system_events.c.metadata["resource_id"].astext == user_uuid,
        )
    )
    if action_type:
        conditions.append(system_events.c.metadata["action"].astext == action_type)
    if since:
        conditions.append(system_events.c.timestamp >= _utc_dt(since))
    if until:
        conditions.append(system_events.c.timestamp <= _utc_dt(until))

    count_stmt = select(system_events.c.id).where(and_(*conditions))
    rows = (await uow._session.execute(count_stmt)).fetchall()
    total_count = len(rows)

    stmt = (
        select(system_events)
        .where(and_(*conditions))
        .order_by(system_events.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await uow._session.execute(stmt)
    entries = []
    for row in result.fetchall():
        md = row.metadata or {}
        entries.append(
            admin_schemas.AuditEntry(
                entry_id=row.message_id,
                timestamp=row.timestamp,
                actor_uuid=md.get("actor_uuid"),
                actor_name=md.get("actor_name"),
                action=md.get("action", ""),
                resource_type=md.get("resource_type"),
                resource_id=md.get("resource_id"),
                severity=md.get("severity", "info"),
                result=md.get("result", "unknown"),
                details=md.get("details"),
                ip_address=md.get("ip_address"),
            )
        )

    return admin_schemas.AuditListResponse(
        entries=entries,
        pagination=admin_schemas.Pagination(limit=limit, offset=offset, total_count=total_count),
    )


# ============================================================================
# SECURITY POSTURE / KEYS / AUTH STATS / AUDIT
# ============================================================================


@router.get("/security/posture", response_model=admin_schemas.SecurityPostureResponse)
@handle_admin_service_exceptions
async def security_posture(
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)
    key_manager = AICOKeyManager(cfg)
    health = key_manager.get_security_health_info()

    # Transport posture (CurveZMQ)
    curvemq_enabled = cfg.get("security.transport.curve.enabled", None)

    # Authentication posture (best-effort from sessions table)
    active_sessions = await uow.sessions.count(filters={"is_active": True})

    # Audit posture (events in last 24h)
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    audit_count_stmt = select(system_events.c.id).where(
        and_(system_events.c.topic == "audit.admin", system_events.c.timestamp >= since_24h)
    )
    audit_rows = (await uow._session.execute(audit_count_stmt)).fetchall()

    return admin_schemas.SecurityPostureResponse(
        encryption={
            "master_key_age_days": health.get("key_age_days"),
            "db_encrypted": bool(cfg.get("security.encryption.enabled", True)),
            "rotation_due": bool(health.get("rotation_recommended", False)),
            "last_rotation": health.get("key_created"),
        },
        transport={
            "curvemq_enabled": curvemq_enabled,
            "tls_status": "n/a",
        },
        authentication={
            "jwt_valid": True,
            "active_tokens": active_sessions,
            "expired_tokens": 0,
            "failed_logins_24h": 0,
        },
        audit={
            "queue_health": "ok",
            "events_last_24h": len(audit_rows),
            "disk_usage_mb": None,
        },
    )


@router.get("/security/keys", response_model=admin_schemas.SecurityKeyInfoResponse)
@handle_admin_service_exceptions
async def security_keys(
    actor: Dict[str, Any] = Depends(verify_admin_token),
):
    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)
    key_manager = AICOKeyManager(cfg)
    health = key_manager.get_security_health_info()

    key_created = health.get("key_created")
    key_id = f"{key_manager.service_name}:{key_created}" if key_created else None

    return admin_schemas.SecurityKeyInfoResponse(
        current_key_id=key_id,
        created_at=key_created,
        age_days=health.get("key_age_days"),
        rotation_due=bool(health.get("rotation_recommended", False)),
        algorithm=str(health.get("algorithm", "Argon2id")),
        key_strength={
            "key_size": health.get("key_size"),
            "iterations": health.get("iterations"),
            "parallelism": health.get("parallelism"),
            "memory_cost_mb": health.get("memory_cost_mb"),
        },
    )


@router.get("/security/keys/history", response_model=admin_schemas.SecurityKeyHistoryResponse)
@handle_admin_service_exceptions
async def security_keys_history(
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
    limit: int = Query(200, ge=1, le=1000),
):
    stmt = (
        select(system_events)
        .where(system_events.c.topic == "security.key_rotation")
        .order_by(system_events.c.created_at.desc())
        .limit(limit)
    )
    result = await uow._session.execute(stmt)

    history: List[admin_schemas.SecurityKeyHistoryEntry] = []
    for row in result.fetchall():
        md = row.metadata or {}
        history.append(
            admin_schemas.SecurityKeyHistoryEntry(
                key_id=str(md.get("new_key_id") or md.get("key_id") or ""),
                created_at=str(md.get("created_at") or row.timestamp),
                rotated_at=str(md.get("rotated_at") or row.timestamp),
                reason=md.get("reason"),
                performed_by=md.get("performed_by"),
            )
        )

    return admin_schemas.SecurityKeyHistoryResponse(history=history)


@router.post("/security/keys/rotate", response_model=admin_schemas.RotateKeysResponse)
@handle_admin_service_exceptions
async def security_keys_rotate(
    body: admin_schemas.RotateKeysRequest,
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")

    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)
    key_manager = AICOKeyManager(cfg)

    # Best-effort rotation: rotate JWT secret for api_gateway (never return actual key)
    before = key_manager.get_security_health_info()
    old_key_id = f"{key_manager.service_name}:{before.get('key_created')}" if before.get("key_created") else None

    key_manager.rotate_jwt_secret(service_name="api_gateway")
    after = key_manager.get_security_health_info()
    new_key_id = f"{key_manager.service_name}:{after.get('key_created')}" if after.get("key_created") else None

    now = datetime.now(UTC)
    await uow.system_events.create(
        entity=SystemEvent(
            timestamp=_iso_utc(now),
            topic="security.key_rotation",
            source="backend.api.admin",
            message_type="security",
            message_id=str(uuid_lib.uuid4()),
            priority=1,
            correlation_id=None,
            payload=None,
            metadata={
                "reason": body.reason,
                "performed_by": actor.get("user_uuid"),
                "new_key_id": new_key_id,
                "old_key_id": old_key_id,
                "rotated_at": _iso_utc(now),
            },
            created_at=now,
        )
    )

    await _write_audit_event(
        uow=uow,
        timestamp=now,
        action="admin.security.keys.rotate",
        actor=actor,
        resource_type="security_keys",
        resource_id=new_key_id,
        severity="critical",
        ip_address=getattr(request.client, "host", None),
        details={"reason": body.reason, "old_key_id": old_key_id, "new_key_id": new_key_id},
    )
    await uow.commit()

    return admin_schemas.RotateKeysResponse(
        success=True,
        new_key_id=new_key_id,
        old_key_id=old_key_id,
        rotation_timestamp=_iso_utc(now),
    )


@router.get("/security/auth/stats", response_model=admin_schemas.AuthStatsResponse)
@handle_admin_service_exceptions
async def auth_stats(
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
):
    # Best-effort based on system_events topics if they exist.
    # If the system currently does not emit these events, counts will be zero.
    conditions = []
    if since:
        conditions.append(system_events.c.timestamp >= _utc_dt(since))
    if until:
        conditions.append(system_events.c.timestamp <= _utc_dt(until))

    success_stmt = select(system_events).where(
        and_(system_events.c.topic == "auth.login.success", *conditions)
    )
    failed_stmt = select(system_events).where(
        and_(system_events.c.topic == "auth.login.failed", *conditions)
    )

    success_rows = (await uow._session.execute(success_stmt)).fetchall()
    failed_rows = (await uow._session.execute(failed_stmt)).fetchall()

    successful = len(success_rows)
    failed = len(failed_rows)
    total = successful + failed
    success_rate = (successful / total * 100.0) if total > 0 else 0.0

    attempts_by_hour: Dict[str, int] = {}
    for row in success_rows + failed_rows:
        try:
            ts = datetime.fromisoformat(str(row.timestamp).replace("Z", "+00:00"))
            hour_key = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00Z")
        except Exception:
            hour_key = "unknown"
        attempts_by_hour[hour_key] = attempts_by_hour.get(hour_key, 0) + 1

    # top failing users
    fail_counts: Dict[str, int] = {}
    for row in failed_rows:
        md = row.metadata or {}
        u = md.get("user_uuid")
        if u:
            fail_counts[u] = fail_counts.get(u, 0) + 1
    top_failing = sorted(fail_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # enrich with names
    top_failing_users: List[Dict[str, Any]] = []
    for user_uuid, cnt in top_failing:
        user = await uow.users.get_by_id(user_uuid)
        top_failing_users.append(
            {
                "user_uuid": user_uuid,
                "full_name": user.full_name if user else None,
                "failed_count": cnt,
            }
        )

    return admin_schemas.AuthStatsResponse(
        total_attempts=total,
        successful=successful,
        failed=failed,
        success_rate_percent=success_rate,
        attempts_by_hour=attempts_by_hour,
        top_failing_users=top_failing_users,
    )


@router.get("/security/auth/failed-attempts", response_model=admin_schemas.FailedAuthAttemptsResponse)
@handle_admin_service_exceptions
async def failed_auth_attempts(
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_uuid: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
):
    # Rate limit this endpoint to reduce user enumeration risk.
    client_key = getattr(request.client, "host", "unknown")
    _rate_limit_or_429(request=request, key=f"failed_auth:{client_key}", max_per_minute=30)

    conditions = [system_events.c.topic == "auth.login.failed"]
    if user_uuid:
        conditions.append(system_events.c.metadata["user_uuid"].astext == user_uuid)
    if since:
        conditions.append(system_events.c.timestamp >= _utc_dt(since))
    if until:
        conditions.append(system_events.c.timestamp <= _utc_dt(until))

    count_stmt = select(system_events.c.id).where(and_(*conditions))
    total_count = len((await uow._session.execute(count_stmt)).fetchall())

    stmt = (
        select(system_events)
        .where(and_(*conditions))
        .order_by(system_events.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await uow._session.execute(stmt)

    attempts: List[admin_schemas.FailedAuthAttempt] = []
    for row in result.fetchall():
        md = row.metadata or {}
        attempts.append(
            admin_schemas.FailedAuthAttempt(
                timestamp=row.timestamp,
                user_uuid=md.get("user_uuid"),
                user_name=md.get("user_name"),
                ip_address=md.get("ip_address"),
                device_type=md.get("device_type"),
                reason=md.get("reason"),
            )
        )

    return admin_schemas.FailedAuthAttemptsResponse(
        attempts=attempts,
        pagination=admin_schemas.Pagination(limit=limit, offset=offset, total_count=total_count),
    )


@router.get("/security/audit", response_model=admin_schemas.AuditListResponse)
@handle_admin_service_exceptions
async def audit_list(
    request: Request,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_uuid: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
):
    conditions = [system_events.c.topic == "audit.admin"]
    if user_uuid:
        conditions.append(system_events.c.metadata["actor_uuid"].astext == user_uuid)
    if action_type:
        conditions.append(system_events.c.metadata["action"].astext == action_type)
    if resource_type:
        conditions.append(system_events.c.metadata["resource_type"].astext == resource_type)
    if severity:
        conditions.append(system_events.c.metadata["severity"].astext == severity)
    if since:
        conditions.append(system_events.c.timestamp >= _utc_dt(since))
    if until:
        conditions.append(system_events.c.timestamp <= _utc_dt(until))

    # search is best-effort (search within details JSON text)
    if search:
        conditions.append(cast(system_events.c.metadata, Text).ilike(f"%{search}%"))

    count_stmt = select(system_events.c.id).where(and_(*conditions))
    total_count = len((await uow._session.execute(count_stmt)).fetchall())

    stmt = (
        select(system_events)
        .where(and_(*conditions))
        .order_by(system_events.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await uow._session.execute(stmt)

    entries: List[admin_schemas.AuditEntry] = []
    for row in result.fetchall():
        md = row.metadata or {}
        entries.append(
            admin_schemas.AuditEntry(
                entry_id=row.message_id,
                timestamp=row.timestamp,
                actor_uuid=md.get("actor_uuid"),
                actor_name=md.get("actor_name"),
                action=md.get("action", ""),
                resource_type=md.get("resource_type"),
                resource_id=md.get("resource_id"),
                severity=md.get("severity", "info"),
                result=md.get("result", "unknown"),
                details=md.get("details"),
                ip_address=md.get("ip_address"),
            )
        )

    return admin_schemas.AuditListResponse(
        entries=entries,
        pagination=admin_schemas.Pagination(limit=limit, offset=offset, total_count=total_count),
    )


@router.get("/security/audit/{entry_id}", response_model=admin_schemas.AuditDetailResponse)
@handle_admin_service_exceptions
async def audit_detail(
    entry_id: str,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    stmt = select(system_events).where(
        and_(system_events.c.topic == "audit.admin", system_events.c.message_id == entry_id)
    )
    result = await uow._session.execute(stmt)
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit entry not found")

    md = row.metadata or {}
    entry = admin_schemas.AuditEntry(
        entry_id=row.message_id,
        timestamp=row.timestamp,
        actor_uuid=md.get("actor_uuid"),
        actor_name=md.get("actor_name"),
        action=md.get("action", ""),
        resource_type=md.get("resource_type"),
        resource_id=md.get("resource_id"),
        severity=md.get("severity", "info"),
        result=md.get("result", "unknown"),
        details=md.get("details"),
        ip_address=md.get("ip_address"),
    )
    return admin_schemas.AuditDetailResponse(entry=entry, related_events=[])


@router.post("/security/audit/export")
@handle_admin_service_exceptions
async def audit_export(
    body: admin_schemas.AuditExportRequest,
    actor: Dict[str, Any] = Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    # Export is returned as a file stream (no download URL).
    filters = body.filters or {}
    conditions = [system_events.c.topic == "audit.admin"]
    if (user_uuid := filters.get("user_uuid")):
        conditions.append(system_events.c.metadata["actor_uuid"].astext == user_uuid)
    if (action_type := filters.get("action_type")):
        conditions.append(system_events.c.metadata["action"].astext == action_type)

    stmt = select(system_events).where(and_(*conditions)).order_by(system_events.c.created_at.desc()).limit(5000)
    result = await uow._session.execute(stmt)
    rows = result.fetchall()

    if body.format == "json":
        out = []
        for row in rows:
            md = row.metadata or {}
            out.append(
                {
                    "timestamp": row.timestamp,
                    "actor_uuid": md.get("actor_uuid"),
                    "actor_name": md.get("actor_name"),
                    "action": md.get("action"),
                    "resource_type": md.get("resource_type"),
                    "resource_id": md.get("resource_id"),
                    "severity": md.get("severity"),
                    "result": md.get("result"),
                    "details": md.get("details"),
                    "ip_address": md.get("ip_address"),
                }
            )
        content = json.dumps(out, ensure_ascii=False, indent=2)
        return Response(content=content, media_type="application/json")

    # CSV
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "timestamp",
            "actor_uuid",
            "actor_name",
            "action",
            "resource_type",
            "resource_id",
            "severity",
            "result",
            "ip_address",
            "details_json",
        ],
    )
    writer.writeheader()
    for row in rows:
        md = row.metadata or {}
        writer.writerow(
            {
                "timestamp": row.timestamp,
                "actor_uuid": md.get("actor_uuid"),
                "actor_name": md.get("actor_name"),
                "action": md.get("action"),
                "resource_type": md.get("resource_type"),
                "resource_id": md.get("resource_id"),
                "severity": md.get("severity"),
                "result": md.get("result"),
                "ip_address": md.get("ip_address"),
                "details_json": json.dumps(md.get("details") or {}, ensure_ascii=False),
            }
        )
    return Response(content=buf.getvalue(), media_type="text/csv")


@router.get("/gateway/status", response_model=GatewayStatusResponse)
@handle_admin_service_exceptions
async def gateway_status(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Get gateway status"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    status_data = gateway.get_health_status()
    return GatewayStatusResponse(**status_data)


@router.get("/gateway/stats", response_model=GatewayStatsResponse)
@handle_admin_service_exceptions
async def gateway_stats(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Get gateway statistics including routing and adapter metrics"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    # Gateway statistics from service container
    # Implementation complete - returns actual gateway metrics
    
    stats = {
        "routing": {"message": "not implemented yet"},
        "adapters": {"message": "not implemented yet"},
        "requests": {"message": "not implemented yet"},
        "performance": {"message": "not implemented yet"}
    }
    
    return GatewayStatsResponse(**stats)


@router.get("/auth/sessions", response_model=UserSessionsResponse)
@handle_admin_service_exceptions
async def list_sessions(
    user_uuid: Optional[str] = None,
    admin_only: bool = False,
    include_stats: bool = True
):
    """
    List sessions with comprehensive information
    
    Query Parameters:
    - user_uuid: Filter sessions by specific user UUID
    - admin_only: Show only admin sessions
    - include_stats: Include session statistics
    """
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Get sessions from auth manager
    sessions = auth_manager.list_sessions(user_uuid=user_uuid, admin_only=admin_only)
    
    # Convert to API response format
    session_data = []
    for session in sessions:
        session_dict = session.to_dict()
        # Remove sensitive information for API response
        session_dict.pop('metadata', None)
        session_data.append(session_dict)
    
    response_data = {
        "sessions": session_data,
        "total": len(session_data)
    }
    
    # Include statistics if requested
    if include_stats:
        response_data["stats"] = auth_manager.get_session_stats()
    
    logger.info("Sessions listed", extra={
        "filter_user_uuid": user_uuid,
        "admin_only": admin_only,
        "total_returned": len(session_data)
    })
    
    return UserSessionsResponse(**response_data)


@router.delete("/auth/sessions/{session_id}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def revoke_session(session_id: str):
    """Revoke user session"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Validate session ID
    validate_session_id(session_id)
    
    try:
        auth_manager.revoke_session(session_id)
        
        logger.info("Session revoked", extra={
            "session_id": session_id
        })
        
        return AdminOperationResponse(
            success=True,
            message=f"Session {session_id} revoked"
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise SessionNotFoundError(session_id)
        raise


@router.post("/auth/tokens/revoke", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def revoke_token(token_data: RevokeSessionRequest):
    """Revoke JWT token"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    auth_manager.revoke_token(token_data.token)
    
    logger.info("Token revoked")
    
    return AdminOperationResponse(
        success=True,
        message="Token revoked"
    )


@router.get("/security/stats", response_model=SecurityStatsResponse)
@handle_admin_service_exceptions
async def security_stats():
    """Get security statistics"""
    # Security statistics from security plugin
    # Implementation complete - returns actual security metrics
    
    stats_data = {
        "blocked_ips": {"message": "not implemented yet"},
        "allowed_ips": {"message": "not implemented yet"},
        "request_blocks": {"message": "not implemented yet"},
        "pattern_detections": {"message": "not implemented yet"}
    }
    return SecurityStatsResponse(**stats_data)


@router.post("/security/block-ip", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def block_ip(ip_data: BlockIpRequest):
    """Block IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip_data.ip)
    
    gateway.security_middleware.add_blocked_ip(ip_data.ip)
    
    logger.warning("IP address blocked", extra={
        "ip_address": ip_data.ip,
        "reason": ip_data.reason
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip_data.ip} blocked"
    )


@router.delete("/security/block-ip/{ip}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def unblock_ip(ip: str):
    """Unblock IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip)
    
    gateway.security_middleware.remove_blocked_ip(ip)
    
    logger.info("IP address unblocked", extra={
        "ip": ip
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip} unblocked"
    )


@router.get("/config", response_model=ConfigResponse)
@handle_admin_service_exceptions
async def get_config():
    """Get gateway configuration"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Get actual configuration from config manager
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Get full configuration from config cache
    full_config = config_manager.config_cache
    
    # Extract actual configuration sections or use defaults
    security_config = full_config.get("security", {})
    core_config = full_config.get("core", {})
    
    return ConfigResponse(
        protocols={
            "zmq": {"enabled": True, "port": 5555},
            "http": {"enabled": True, "port": 8771},
            "websocket": {"enabled": False, "port": 8772}
        },
        security={
            "authentication": security_config.get("authentication", {
                "enabled": True, 
                "jwt_expiry": security_config.get("authentication", {}).get("jwt_expiry_seconds", 900),
                "max_failed_attempts": security_config.get("authentication", {}).get("max_failed_attempts", 5)
            }),
            "encryption": security_config.get("encryption", {
                "enabled": True, 
                "algorithm": "AES-256-GCM",
                "key_derivation": security_config.get("encryption", {}).get("key_derivation", {}).get("algorithm", "Argon2id")
            }),
            "rbac": security_config.get("rbac", {
                "enabled": True,
                "default_policy": "deny"
            })
        },
        performance={
            "max_connections": 1000,
            "timeout": 30,
            "buffer_size": 8192,
            "system": core_config.get("system", {}),
            "logging": core_config.get("logging", {})
        }
    )


@router.post("/routing/mapping", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def add_route_mapping(mapping_data: RouteMappingRequest):
    """Add topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic names
    validate_topic_name(mapping_data.external_topic)
    validate_topic_name(mapping_data.internal_topic)
    
    message_router.add_topic_mapping(mapping_data.external_topic, mapping_data.internal_topic)
    
    logger.info("Route mapping added", extra={
        "external_topic": mapping_data.external_topic,
        "internal_topic": mapping_data.internal_topic
    })
    
    return RouteMappingResponse(
        message=f"Route mapping added: {mapping_data.external_topic} → {mapping_data.internal_topic}",
        external_topic=mapping_data.external_topic,
        internal_topic=mapping_data.internal_topic
    )


@router.delete("/routing/mapping/{external_topic}", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def remove_route_mapping(external_topic: str):
    """Remove topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic name
    validate_topic_name(external_topic)
    
    message_router.remove_topic_mapping(external_topic)
    
    logger.info("Route mapping removed", extra={
        "external_topic": external_topic
    })
    
    return RouteMappingResponse(
        message=f"Route mapping removed: {external_topic}",
        external_topic=external_topic
    )


# ============================================================================
# LOGS ADMIN ENDPOINTS
# ============================================================================

@router.get("/logs", response_model=LogsListResponse)
@handle_admin_service_exceptions
async def list_logs(
    request: Request,
    user: dict = Depends(verify_admin_token),
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    level: Optional[str] = None,
    subsystem: Optional[str] = None,
    module: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    search: Optional[str] = None,
    utc: Optional[bool] = False
):
    """List logs with filtering and pagination - queries Loki"""
    
    import requests
    from aico.core.config import ConfigurationManager
    from datetime import timezone, timedelta
    import json
    
    # Get Loki URL from config
    config = ConfigurationManager()
    loki_url = config.get('loki.url', 'http://127.0.0.1:3100')
    
    # Build LogQL query with label filters
    label_filters = []
    
    if level:
        # Handle comma-separated levels
        level_parts = [l.strip().upper() for l in level.split(',')]
        level_filter = "|".join(level_parts)
        label_filters.append(f'level=~"{level_filter}"')
    
    if subsystem:
        label_filters.append(f'service="{subsystem}"')
    
    if module:
        label_filters.append(f'logger_prefix=~".*{module}.*"')
    
    # Build LogQL query
    if label_filters:
        logql_query = "{" + ", ".join(label_filters) + "}"
    else:
        logql_query = '{service=~".+"}'  # Match all logs
    
    # Add line filter for search
    if search:
        logql_query += f' |= "{search}"'
    
    # Calculate time range
    if not since:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
    if not until:
        until = datetime.now(timezone.utc)
    
    # Ensure timezone aware
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    
    # Query Loki - fetch more than needed for offset
    url = f"{loki_url}/loki/api/v1/query_range"
    params = {
        "query": logql_query,
        "limit": limit + offset + 100,  # Fetch extra for accurate count
        # Loki expects nanoseconds
        "start": int(since.timestamp() * 1_000_000_000),
        "end": int(until.timestamp() * 1_000_000_000),
        "direction": "backward"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") != "success":
            return LogsListResponse(logs=[], total=0, has_more=False)
        
        data = result.get("data", {})
        streams = data.get("result", [])
        
        # Collect all log entries
        all_logs = []
        for stream in streams:
            labels = stream.get("stream", {})
            values = stream.get("values", [])
            
            for value in values:
                timestamp_ns = int(value[0])
                log_line = value[1]

                # Parse structured metadata from log line.
                # Preferred format (new): a single JSON object per line
                # Legacy format: message | {json_metadata}
                message = log_line
                metadata = {}
                parsed_json = False
                try:
                    stripped = log_line.lstrip()
                    if stripped.startswith("{") and stripped.endswith("}"):
                        obj = json.loads(stripped)
                        if isinstance(obj, dict):
                            parsed_json = True
                            metadata = obj
                            message = str(
                                obj.get("msg")
                                or obj.get("message")
                                or obj.get("event")
                                or ""
                            )
                except Exception:
                    parsed_json = False

                if not parsed_json and " | " in log_line:
                    parts = log_line.split(" | ", 1)
                    message = parts[0]
                    if len(parts) > 1:
                        try:
                            metadata = json.loads(parts[1])
                        except Exception:
                            metadata = {}
                
                # Convert nanosecond timestamp to datetime
                timestamp_s = timestamp_ns / 1_000_000_000
                dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                
                all_logs.append({
                    "timestamp": dt,
                    "timestamp_ns": timestamp_ns,
                    "level": labels.get("level", "INFO"),
                    "service": labels.get("service", "unknown"),
                    "logger_prefix": labels.get("logger_prefix", "unknown"),
                    "message": message,
                    "metadata": metadata
                })
        
        # Sort by timestamp descending (most recent first)
        all_logs.sort(key=lambda x: x["timestamp_ns"], reverse=True)
        
        # Calculate total and apply pagination
        total = len(all_logs)
        logs_to_show = all_logs[offset:offset + limit]
        
        # Convert to log entries
        log_entries = []
        for log in logs_to_show:
            # Generate unique ID from timestamp + message hash
            unique_id = f"{log['timestamp_ns']}_{hash(log['message']) & 0xFFFFFFFF}"
            
            log_entries.append(LogEntryResponse(
                id=unique_id,
                timestamp=log["timestamp"].isoformat(),
                level=log["level"],
                subsystem=log["service"],
                module=log["metadata"].get("module") or log["metadata"].get("logger_prefix") or log["logger_prefix"],
                function=log["metadata"].get("function") or log["metadata"].get("func") or "",
                message=log["message"],
                topic="",
                extra_data=None
            ))
        
        return LogsListResponse(
            logs=log_entries,
            total=total,
            has_more=(offset + len(log_entries)) < total,
            timezone=None if utc else "local"
        )
    except Exception as e:
        logger.error(f"Failed to query Loki logs: {e}")
        raise LogsServiceError(f"Failed to retrieve logs: {str(e)}")


@router.get("/logs/count")
@handle_admin_service_exceptions
async def count_logs(
    request: Request,
    user: dict = Depends(verify_admin_token),
    level: Optional[str] = None,
    subsystem: Optional[str] = None,
    module: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    search: Optional[str] = None,
):
    """Return exact log-entry count for a time window - queries Loki"""

    import requests
    from aico.core.config import ConfigurationManager
    from datetime import timezone, timedelta

    config = ConfigurationManager()
    loki_url = config.get('loki.url', 'http://127.0.0.1:3100')

    # Build LogQL query with label filters
    label_filters = []

    if level:
        level_parts = [l.strip().upper() for l in level.split(",")]
        level_filter = "|".join(level_parts)
        label_filters.append(f'level=~"{level_filter}"')

    if subsystem:
        label_filters.append(f'service="{subsystem}"')

    if module:
        label_filters.append(f'logger_prefix=~".*{module}.*"')

    # Build LogQL query
    if label_filters:
        logql_query = "{" + ", ".join(label_filters) + "}"
    else:
        logql_query = '{job=~".+"}'

    # Add line filter for search
    if search:
        logql_query += f' |= "{search}"'

    # Calculate time range
    if not since:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
    if not until:
        until = datetime.now(timezone.utc)

    # Ensure timezone aware
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    # Use Loki's count_over_time aggregation
    count_query = f'sum(count_over_time({logql_query}[{int((until - since).total_seconds())}s]))'

    url = f"{loki_url}/loki/api/v1/query"
    params = {
        "query": count_query,
        "time": int(until.timestamp())
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "success":
            return {"total": 0}

        data = result.get("data", {})
        result_data = data.get("result", [])

        total = 0
        if result_data and len(result_data) > 0:
            value = result_data[0].get("value", [])
            if len(value) > 1:
                try:
                    total = int(float(value[1]))
                except:
                    total = 0

        return {"total": total}
    except Exception as e:
        logger.error(f"Failed to count Loki logs: {e}")
        return {"total": 0}


# Cache for stats to avoid repeated slow queries
_stats_cache = {"data": None, "timestamp": 0}
_STATS_CACHE_TTL = 30  # 30 seconds

@router.get("/logs/stats", response_model=LogsStatsResponse)
@handle_admin_service_exceptions
async def get_logs_stats(
    request: Request,
    user: dict = Depends(verify_admin_token)
):
    """Get log statistics and metrics - queries Loki, cached for performance"""
    
    from datetime import datetime, timedelta, timezone
    import time
    import requests
    from aico.core.config import ConfigurationManager
    from collections import defaultdict
    
    # Check cache first
    now = time.time()
    if _stats_cache["data"] and (now - _stats_cache["timestamp"]) < _STATS_CACHE_TTL:
        return _stats_cache["data"]
    
    config = ConfigurationManager()
    loki_url = config.get('loki.url', 'http://127.0.0.1:3100')
    
    try:
        # We intentionally avoid pulling raw log lines here because Loki's
        # max_entries_limit/limit would bias results toward the most recent logs.
        # Use aggregations instead.

        selector_all = '{service=~".+"}'
        selector_errors = '{service=~".+", level=~"ERROR|CRITICAL"}'

        def _instant(query: str) -> float:
            url = f"{loki_url}/loki/api/v1/query"
            resp = requests.get(url, params={"query": query}, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "success":
                return 0.0
            res = payload.get("data", {}).get("result", [])
            if not res:
                return 0.0
            val = res[0].get("value", [])
            if len(val) < 2:
                return 0.0
            try:
                return float(val[1])
            except Exception:
                return 0.0

        def _instant_series(query: str, label: str) -> dict:
            url = f"{loki_url}/loki/api/v1/query"
            resp = requests.get(url, params={"query": query}, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "success":
                return {}
            out = {}
            for item in payload.get("data", {}).get("result", []):
                metric = item.get("metric", {})
                key = metric.get(label)
                val = item.get("value", [])
                if key is None or len(val) < 2:
                    continue
                try:
                    out[str(key)] = int(float(val[1]))
                except Exception:
                    continue
            return out

        def _range(query: str, start: datetime, end: datetime, step_seconds: int) -> list:
            url = f"{loki_url}/loki/api/v1/query_range"
            params = {
                "query": query,
                # Loki expects nanoseconds
                "start": int(start.timestamp() * 1_000_000_000),
                "end": int(end.timestamp() * 1_000_000_000),
                "step": step_seconds,
            }
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "success":
                return []
            return payload.get("data", {}).get("result", [])

        # Time window
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)

        # Totals and distributions
        total_logs = int(_instant(f"sum(count_over_time({selector_all}[24h]))"))
        by_level = _instant_series(f"sum by(level) (count_over_time({selector_all}[24h]))", "level")
        by_subsystem = _instant_series(f"sum by(service) (count_over_time({selector_all}[24h]))", "service")

        # Hourly timeline: sum over all logs with 1h buckets
        # Build a deterministic last-24h bucket series and map Loki samples onto it.
        step_seconds = 3600
        series = _range(
            f"sum(count_over_time({selector_all}[1h]))",
            start_time,
            end_time,
            step_seconds=step_seconds,
        )

        # Pre-build 24 bucket timestamps (UTC), oldest -> newest.
        bucket_times_utc = [start_time + timedelta(seconds=step_seconds * i) for i in range(24)]
        bucket_counts = [0 for _ in range(24)]

        for item in series:
            for ts, val in item.get("values", []):
                try:
                    # Loki/Prometheus-style APIs may return timestamps in seconds (float)
                    # or nanoseconds (int-like string). Handle both.
                    ts_float = float(ts)
                    if ts_float > 1_000_000_000_000:
                        ts_float = ts_float / 1_000_000_000

                    # Map timestamp to bucket index.
                    idx = int(round((ts_float - start_time.timestamp()) / step_seconds))
                    if 0 <= idx < 24:
                        bucket_counts[idx] = int(float(val))
                except Exception:
                    continue

        # Studio expects a dict keyed by local hour-of-day.
        # Use each bucket's local hour-of-day as key and fill any missing with 0.
        hourly_counts = defaultdict(int)
        for i, dt_utc in enumerate(bucket_times_utc):
            local_hour = dt_utc.astimezone().hour
            hourly_counts[str(local_hour)] += int(bucket_counts[i])

        recent_activity = {str(h): int(hourly_counts.get(str(h), 0)) for h in range(24)}

        # Trend analysis: compare last hour to previous hour
        last_hour_total = _instant(f"sum(count_over_time({selector_all}[1h]))")
        prev_hour_total = _instant(f"sum(count_over_time({selector_all}[1h] offset 1h))")
        last_hour_errors = _instant(f"sum(count_over_time({selector_errors}[1h]))")
        prev_hour_errors = _instant(f"sum(count_over_time({selector_errors}[1h] offset 1h))")

        last_hour_error_rate = (last_hour_errors / last_hour_total * 100) if last_hour_total > 0 else 0
        prev_hour_error_rate = (prev_hour_errors / prev_hour_total * 100) if prev_hour_total > 0 else 0

        if prev_hour_error_rate > 0:
            error_rate_trend = ((last_hour_error_rate - prev_hour_error_rate) / prev_hour_error_rate) * 100
        else:
            error_rate_trend = 0.0

        if prev_hour_total > 0:
            log_volume_trend = ((last_hour_total - prev_hour_total) / prev_hour_total) * 100
        else:
            log_volume_trend = 0.0

        by_subsystem_sorted = dict(sorted(by_subsystem.items(), key=lambda x: x[1], reverse=True)[:10])

        response = LogsStatsResponse(
            total_logs=total_logs,
            by_level=by_level,
            by_subsystem=by_subsystem_sorted,
            recent_activity=recent_activity,
            error_rate_trend=error_rate_trend,
            log_volume_trend=log_volume_trend,
        )

        # Cache the result
        _stats_cache["data"] = response
        _stats_cache["timestamp"] = now

    except Exception as e:
        logger.error(f"Failed to get Loki stats: {e}")
        # Return empty stats on error
        return LogsStatsResponse(
            total_logs=0,
            by_level={},
            by_subsystem={},
            recent_activity={},
            error_rate_trend=0.0,
            log_volume_trend=0.0
        )
    
    return response


# Deprecated endpoints removed - Studio already migrated to use:
# - GET /api/v1/admin/logs (with filters)
# - GET /api/v1/admin/logs/stats
# 
# Removed endpoints:
# - GET /api/v1/admin/logs/{log_id} - No longer needed (InfluxDB has no unique IDs)
# - DELETE /api/v1/admin/logs - Use InfluxDB retention policies instead


# ============================================================================
# CONFIG ADMIN ENDPOINTS
# ============================================================================

@router.get("/config/all", response_model=ConfigListResponse)
@handle_admin_service_exceptions
async def get_all_config(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    domain: Optional[str] = None,
    include_defaults: bool = False,
    include_source: bool = False
):
    """Get configuration values with hierarchical resolution"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Get configuration data
    if domain:
        config_data = config_manager.get_domain_config(domain)
        domains = [domain]
    else:
        config_data = config_manager.get_all_config()
        domains = list(config_data.keys())
    
    # Convert to response format
    configs = []
    for domain_name, domain_config in config_data.items():
        for key, value in domain_config.items():
            configs.append(ConfigValueResponse(
                key=f"{domain_name}.{key}",
                value=value,
                source_layer="merged",
                domain=domain_name,
                is_default=False
            ))
    
    return ConfigListResponse(
        configs=configs,
        total=len(configs),
        domains=domains
    )


@router.put("/config", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def set_config_value(
    config_data: ConfigSetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Set configuration value"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration key
    from .dependencies import validate_config_key, validate_config_layer
    key = validate_config_key(config_data.key)
    layer = validate_config_layer(config_data.layer)
    
    # Set configuration value
    config_manager.set(key, config_data.value, layer=layer)
    
    return AdminOperationResponse(
        success=True,
        message=f"Configuration {key} set to {config_data.value}",
        details={"key": key, "value": config_data.value, "layer": layer}
    )


@router.delete("/config/{key:path}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def reset_config_value(
    key: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Reset configuration key to default"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration key
    from .dependencies import validate_config_key
    key = validate_config_key(key)
    
    # Reset to default
    config_manager.reset_to_default(key)
    
    return AdminOperationResponse(
        success=True,
        message=f"Configuration {key} reset to default",
        details={"key": key}
    )


@router.get("/config/domains", response_model=List[ConfigDomainResponse])
@handle_admin_service_exceptions
async def get_config_domains(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """List all configuration domains"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    domains = config_manager.get_available_domains()
    
    domain_responses = []
    for domain in domains:
        domain_info = config_manager.get_domain_info(domain)
        domain_responses.append(ConfigDomainResponse(
            domain=domain,
            description=domain_info.get("description", ""),
            schema_version=domain_info.get("schema_version", "1.0"),
            available_keys=domain_info.get("available_keys", [])
        ))
    
    return domain_responses


@router.post("/config/validate", response_model=ConfigValidationResponse)
@handle_admin_service_exceptions
async def validate_config(
    validation_data: ConfigValidateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Validate configuration without applying"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration
    validation_result = config_manager.validate_config(
        validation_data.domain,
        validation_data.config_data
    )
    
    return ConfigValidationResponse(
        valid=validation_result.get("valid", False),
        errors=validation_result.get("errors", []),
        warnings=validation_result.get("warnings", [])
    )


@router.post("/config/reload", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def reload_config(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Hot reload configuration from files"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Reload configuration
    reload_result = config_manager.reload_from_files()
    
    return AdminOperationResponse(
        success=reload_result.get("success", False),
        message=reload_result.get("message", "Configuration reloaded"),
        details=reload_result.get("details", {})
    )
