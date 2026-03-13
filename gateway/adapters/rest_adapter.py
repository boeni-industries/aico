"""
REST Adapter for AICO API Gateway

Infrastructure-focused FastAPI adapter providing:
- Protocol-level HTTP/REST interface
- CORS middleware
- Security middleware
- Request logging
- Gateway status and metrics endpoints
- Domain router mounting capabilities

Business logic endpoints are handled by domain-specific routers in backend/api/
"""

import asyncio
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Depends, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger

# Import version from VERSIONS file
from aico.core.version import get_backend_version
__version__ = get_backend_version()
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata
from aico.security.key_manager import AICOKeyManager

from ..middleware.rate_limiter import RateLimiter
from ..middleware.validator import MessageValidator
from ..middleware.security import SecurityMiddleware
from ..middleware.encryption import EncryptionMiddleware


class RESTAdapter:
    """
    REST API adapter using FastAPI
    
    Provides HTTP/JSON interface to AICO message bus with:
    - RESTful endpoints
    - OpenAPI documentation
    - CORS support
    - Authentication/authorization
    - Rate limiting
    """
    
    def __init__(self, config: Dict[str, Any], auth_manager: Optional[Any] = None,
                 authz_manager: Optional[Any] = None, message_router: Optional[Any] = None,
                 rate_limiter: Optional[RateLimiter] = None, validator: Optional[MessageValidator] = None,
                 security_middleware: Optional[SecurityMiddleware] = None, key_manager: Optional[AICOKeyManager] = None):
        
        self.logger = get_logger("gateway.adapters.rest")
        self.config = config
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        self.message_router = message_router
        self.rate_limiter = rate_limiter
        self.validator = validator
        self.security_middleware = security_middleware
        self.key_manager = key_manager
        
        # Initialize encryption middleware
        self.encryption_middleware = EncryptionMiddleware(None, key_manager)
        
        # FastAPI app
        self.app = FastAPI(
            title="AICO API Gateway",
            description="Unified API Gateway for AICO AI Companion",
            version=__version__,
            docs_url=f"{config.get('prefix', '/api/v1')}/docs",
            redoc_url=f"{config.get('prefix', '/api/v1')}/redoc"
        )
        
        # Store encryption middleware in app state for access by endpoints
        self.app.state.encryption_middleware = self.encryption_middleware
        
        # Configure CORS
        self._setup_cors()
        
        # Setup routes
        self._setup_routes()
        
        # Setup middleware (including encryption)
        self._setup_middleware()
        
        # Server instance
        self.server = None
        
        self.logger.info("REST adapter initialized", extra={
            "port": config.get("port", 8771),
            "prefix": config.get("prefix", "/api/v1")
        })
    
    def _setup_cors(self):
        """Configure CORS middleware"""
        # CORS is always enabled for Studio React app - following AICO security paradigm
        cors_origins = self.config.get(
            "cors_origins",
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3002",
                "http://127.0.0.1:3002",
            ],
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"]
        )
    
    def _setup_middleware(self):
        """Setup middleware stack"""

        # Add encryption middleware (first in chain for request processing)
        # Using pure ASGI middleware to avoid Content-Length calculation bugs
        if self.encryption_middleware and self.key_manager:
            self.app.add_middleware(self.encryption_middleware.__class__, key_manager=self.key_manager)
        
        # Add security middleware (if available)
        if self.security_middleware:
            self.app.add_middleware(
                BaseHTTPMiddleware,
                dispatch=self.security_middleware.dispatch
            )
        
        # Add rate limiting middleware (if available)
        if self.rate_limiter:
            self.app.add_middleware(
                BaseHTTPMiddleware,
                dispatch=self.rate_limiter.dispatch
            )
        
        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            """Request logging middleware"""
            import time
            start_time = time.time()
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            status_code = int(getattr(response, "status_code", 0) or 0)
            path = request.url.path
            query = request.url.query
            path_with_query = f"{path}?{query}" if query else path
            ms = int(process_time * 1000)

            # Suppress expected noise and only log actionable issues.
            # - 404: browsers/Studio probing endpoints
            # - 401/403: Studio not logged in yet / token expired (handled client-side)
            if status_code in (401, 403, 404):
                return response

            if status_code >= 500:
                self.logger.error(f"REST {request.method} {path_with_query} -> {status_code} ({ms}ms)")
            elif process_time > 1.0:
                self.logger.warning(f"REST {request.method} {path_with_query} -> {status_code} SLOW ({ms}ms)")
            
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        prefix = self.config.get("prefix", "/api/v1")
        
        # Health check
        @self.app.get(f"{prefix}/health")
        async def health_check():
            """Health check endpoint"""
            from aico.core.version import get_backend_version

            return {
                "status": "healthy",
                "service": "aico-api-gateway",
                "version": get_backend_version(),
            }

        @self.app.post(f"{prefix}/handshake")
        async def handshake(request: Request):
            middleware = getattr(request.app.state, "encryption_middleware", None)
            if middleware is None:
                raise HTTPException(
                    status_code=500,
                    detail="Encryption middleware not initialized",
                )
            if not getattr(middleware, "enabled", False):
                return {
                    "status": "encryption_disabled",
                    "message": "Transport encryption is disabled",
                }
            return await middleware._handle_handshake(request)

        # ------------------------------------------------------------------
        # Studio API endpoints (gateway→core NATS proxies)
        # ------------------------------------------------------------------
        import uuid as uuid_lib
        from datetime import datetime, timedelta, timezone

        from gateway.api.dependencies import get_current_user, get_auth_manager
        from gateway.api.admin.router import router as admin_router
        from gateway.api.agency.router_gateway import router as agency_router
        from gateway.api.ams.router import router as ams_router
        from gateway.api.conversation.router import router as conversation_router
        from gateway.api.interactions.router import router as interactions_router
        from gateway.api.operations.router import router as operations_router
        from gateway.api.system.router_gateway import router as system_router
        from aico.common.postgres_dependencies import get_uow
        from aico.data.auth.credentials_models import AuthUserCredentials
        from aico.data.uow import UnitOfWork
        from aico.services.user_service import UserService

        self.app.include_router(conversation_router, prefix=f"{prefix}/conversation")
        self.app.include_router(interactions_router, prefix=f"{prefix}/interactions")
        self.app.include_router(operations_router, prefix=prefix)
        self.app.include_router(admin_router, prefix=prefix)
        self.app.include_router(agency_router, prefix=prefix)
        self.app.include_router(ams_router, prefix=prefix)
        self.app.include_router(system_router, prefix=prefix)

        def _serialize_user(user: Any) -> Dict[str, Any]:
            return {
                "uuid": getattr(user, "user_uuid", None) or getattr(user, "uuid", None),
                "full_name": getattr(user, "full_name", None) or getattr(user, "name", None) or "",
                "nickname": getattr(user, "nickname", None),
                "user_type": str(getattr(user, "user_type", "user")),
                "is_active": bool(getattr(user, "is_active", True)),
                "primary_language": getattr(user, "primary_language", None),
                "created_at": getattr(user, "created_at", None),
                "updated_at": getattr(user, "updated_at", None),
            }

        def _iso_or_none(value: Any) -> str | None:
            if value is None:
                return None
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        def _session_is_currently_active(session: Any, now: datetime) -> bool:
            expires_at = getattr(session, "expires_at", None)
            return bool(getattr(session, "is_active", False)) and bool(expires_at and expires_at > now)

        def _format_session_time_remaining(expires_at: Any, now: datetime) -> str:
            if expires_at is None:
                return "Expired"

            remaining = expires_at - now
            total_seconds = int(remaining.total_seconds())
            if total_seconds <= 0:
                return "Expired"

            days, rem = divmod(total_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, _ = divmod(rem, 60)

            if days > 0:
                return f"{days}d {hours}h"
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"

        @self.app.post(f"{prefix}/users/authenticate")
        async def users_authenticate(request: Request):
            auth_manager = get_auth_manager(request)
            body = await request.json()
            user_uuid = (body or {}).get("user_uuid")
            password = (body or {}).get("password") or (body or {}).get("pin")
            device_uuid = (body or {}).get("device_uuid") or "studio"

            client_info = {
                "remote_addr": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }

            result = await auth_manager.authenticate(
                {"user_uuid": user_uuid, "password": password, "device_uuid": device_uuid},
                client_info,
            )

            if not result.success or not result.user or not result.token:
                return {"success": False, "error": result.error or "Authentication failed"}

            # NOTE: refresh_token is currently the same token. Refresh rotates JWT via /users/refresh.
            return {
                "success": True,
                "user": _serialize_user(result.user),
                "jwt_token": result.token,
                "refresh_token": result.token,
                "last_login": None,
            }

        @self.app.post(f"{prefix}/users/refresh")
        async def users_refresh(request: Request):
            auth_manager = get_auth_manager(request)
            body = await request.json()
            refresh_token = (body or {}).get("refresh_token")
            if not refresh_token:
                return {"success": False, "error": "Missing refresh_token"}

            new_token = await auth_manager.refresh_token(refresh_token)
            if not new_token:
                return {"success": False, "error": "Token refresh failed"}

            return {"success": True, "jwt_token": new_token, "refresh_token": new_token}

        @self.app.get(f"{prefix}/users/{{user_uuid}}")
        async def users_get_profile(
            user_uuid: str,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            user_service = UserService(uow)
            user = await user_service.get_user(user_uuid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return _serialize_user(user)

        @self.app.get(f"{prefix}/kg/stats")
        async def kg_stats(user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_kg_stats(str(user.get("user_uuid") or user.get("user_id")))

        @self.app.get(f"{prefix}/kg/nodes")
        async def kg_nodes(
            limit: int = Query(100),
            offset: int = Query(0),
            user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_kg_nodes(
                str(user.get("user_uuid") or user.get("user_id")),
                limit=int(limit),
                offset=int(offset),
            )

        @self.app.get(f"{prefix}/kg/edges")
        async def kg_edges(
            limit: int = Query(100),
            offset: int = Query(0),
            user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_kg_edges(
                str(user.get("user_uuid") or user.get("user_id")),
                limit=int(limit),
                offset=int(offset),
            )

        @self.app.post(f"{prefix}/kg/query")
        async def kg_query(
            payload: Dict[str, Any],
            user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            query = (payload or {}).get("query")
            fmt = (payload or {}).get("format") or "dict"
            return await get_gateway_nats_client().request_kg_query(
                user_id=str(user.get("user_uuid") or user.get("user_id")),
                query=query,
                format=fmt,
            )

        @self.app.get(f"{prefix}/kg/query-templates")
        async def kg_query_templates(user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_kg_query_templates(str(user.get("user_uuid") or user.get("user_id")))

        @self.app.put(f"{prefix}/kg/query-templates")
        async def kg_query_templates_update(
            payload: Dict[str, Any],
            user: Dict[str, Any] = Depends(get_current_user),
        ):
            templates = (payload or {}).get("templates") or []
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_update_kg_query_templates(
                str(user.get("user_uuid") or user.get("user_id")),
                templates,
            )

        @self.app.get(f"{prefix}/memory/working/stats")
        async def memory_working_stats(_user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_working_memory_stats()

        @self.app.get(f"{prefix}/memory/semantic/stats")
        async def memory_semantic_stats(_user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_semantic_memory_stats()

        @self.app.get(f"{prefix}/memory-album")
        async def memory_album(
            category: str | None = Query(None),
            favorites_only: bool = Query(False),
            limit: int = Query(50),
            offset: int = Query(0),
            user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_memory_album(
                user_uuid=str(user.get("user_uuid") or user.get("user_id")),
                category=category,
                favorites_only=bool(favorites_only),
                limit=int(limit),
                offset=int(offset),
            )

        @self.app.get(f"{prefix}/scheduler/status")
        async def scheduler_status(_user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_status()

        @self.app.get(f"{prefix}/scheduler/tasks")
        async def scheduler_tasks(
            enabled_only: bool = Query(False),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_tasks(enabled_only=bool(enabled_only))

        @self.app.get(f"{prefix}/scheduler/expected-runs-today")
        async def scheduler_expected_runs_today(_user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_expected_runs_today()

        @self.app.get(f"{prefix}/scheduler/executions")
        async def scheduler_executions(
            start_time: str = Query(...),
            end_time: str = Query(...),
            limit: int = Query(200),
            cursor_started_at: str | None = Query(None),
            cursor_execution_id: str | None = Query(None),
            task_id: str | None = Query(None),
            status: str | None = Query(None),
            include_acknowledged: bool = Query(True),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_executions_list(
                start_time=start_time,
                end_time=end_time,
                limit=int(limit),
                cursor_started_at=cursor_started_at,
                cursor_execution_id=cursor_execution_id,
                task_id=task_id,
                status=status,
                include_acknowledged=bool(include_acknowledged),
            )

        @self.app.get(f"{prefix}/scheduler/executions/{{execution_id}}")
        async def scheduler_execution_detail(
            execution_id: str,
            start_time: str | None = Query(None),
            end_time: str | None = Query(None),
            bucket: str = Query("hour"),
            task_id: str | None = Query(None),
            limit: int = Query(100),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client

            if execution_id == "stats":
                return await get_gateway_nats_client().request_scheduler_executions_stats(
                    start_time=str(start_time or ""),
                    end_time=str(end_time or ""),
                    bucket=bucket,
                    task_id=task_id,
                )

            if execution_id == "unacknowledged-failures":
                return await get_gateway_nats_client().request_scheduler_unacknowledged_failures(
                    task_id=task_id,
                    limit=int(limit),
                )

            return await get_gateway_nats_client().request_scheduler_execution_get(execution_id)

        @self.app.get(f"{prefix}/scheduler/executions/stats")
        async def scheduler_execution_stats(
            start_time: str = Query(...),
            end_time: str = Query(...),
            bucket: str = Query("hour"),
            task_id: str | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_executions_stats(
                start_time=start_time,
                end_time=end_time,
                bucket=bucket,
                task_id=task_id,
            )

        @self.app.get(f"{prefix}/scheduler/executions/unacknowledged-failures")
        async def scheduler_unacknowledged_failures(
            task_id: str | None = Query(None),
            limit: int = Query(100),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_unacknowledged_failures(
                task_id=task_id,
                limit=int(limit),
            )

        @self.app.post(f"{prefix}/scheduler/executions/{{execution_id}}/acknowledge")
        async def scheduler_acknowledge_execution(
            execution_id: str,
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_acknowledge_execution(execution_id)

        @self.app.post(f"{prefix}/scheduler/executions/acknowledge-all")
        async def scheduler_acknowledge_all_executions(
            task_id: str | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_acknowledge_all_failed(task_id=task_id)

        @self.app.get(f"{prefix}/scheduler/runs")
        async def scheduler_runs(
            start_time: str = Query(...),
            end_time: str = Query(...),
            limit: int = Query(200),
            offset: int = Query(0),
            task_id: str | None = Query(None),
            state: str | None = Query(None),
            tenant_id: str | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_runs_list(
                start_time=start_time,
                end_time=end_time,
                limit=int(limit),
                offset=int(offset),
                task_id=task_id,
                state=state,
                tenant_id=tenant_id,
            )

        @self.app.get(f"{prefix}/scheduler/runs/{{run_id}}")
        async def scheduler_run_detail(
            run_id: str,
            start_time: str | None = Query(None),
            end_time: str | None = Query(None),
            bucket: str = Query("hour"),
            task_id: str | None = Query(None),
            tenant_id: str | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client

            if run_id == "stats":
                return await get_gateway_nats_client().request_scheduler_runs_stats(
                    start_time=str(start_time or ""),
                    end_time=str(end_time or ""),
                    bucket=bucket,
                    task_id=task_id,
                    tenant_id=tenant_id,
                )

            return await get_gateway_nats_client().request_scheduler_run_get(run_id)

        @self.app.get(f"{prefix}/scheduler/runs/stats")
        async def scheduler_runs_stats(
            start_time: str = Query(...),
            end_time: str = Query(...),
            bucket: str = Query("hour"),
            task_id: str | None = Query(None),
            tenant_id: str | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_scheduler_runs_stats(
                start_time=start_time,
                end_time=end_time,
                bucket=bucket,
                task_id=task_id,
                tenant_id=tenant_id,
            )

        @self.app.get(f"{prefix}/emotion/history")
        async def emotion_history(
            limit: int = Query(200),
            hours: int | None = Query(None),
            days: int | None = Query(None),
            _user: Dict[str, Any] = Depends(get_current_user),
        ):
            from gateway.core.nats_client import get_gateway_nats_client
            # Studio passes hours/days; core currently supports hours.
            effective_hours = hours
            if effective_hours is None and days is not None:
                effective_hours = int(days) * 24
            return await get_gateway_nats_client().request_emotion_history(limit=int(limit), hours=int(effective_hours) if effective_hours is not None else 24)

        @self.app.get(f"{prefix}/health/detailed")
        async def health_detailed(_user: Dict[str, Any] = Depends(get_current_user)):
            from gateway.core.nats_client import get_gateway_nats_client
            return await get_gateway_nats_client().request_health_detailed()

        @self.app.get(f"{prefix}/users-sessions/users")
        async def users_sessions_users(_user: Dict[str, Any] = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)):
            users = await uow.users.list(limit=10000)
            sessions = await uow.sessions.list(limit=10000)
            now = datetime.now(timezone.utc)

            active_session_counts: Dict[str, int] = {}
            total_session_counts: Dict[str, int] = {}
            last_activity_by_user: Dict[str, Any] = {}

            for session in sessions:
                user_uuid = getattr(session, "user_uuid", None)
                if not user_uuid:
                    continue
                total_session_counts[user_uuid] = total_session_counts.get(user_uuid, 0) + 1
                if _session_is_currently_active(session, now):
                    active_session_counts[user_uuid] = active_session_counts.get(user_uuid, 0) + 1

                created_at = getattr(session, "created_at", None)
                if created_at is not None:
                    previous = last_activity_by_user.get(user_uuid)
                    if previous is None or created_at > previous:
                        last_activity_by_user[user_uuid] = created_at

            response_users = []
            active_users = 0
            for user in users:
                user_uuid = getattr(user, "uuid", None)
                active_count = int(active_session_counts.get(user_uuid, 0))
                total_count = int(total_session_counts.get(user_uuid, 0))
                if active_count > 0:
                    active_users += 1

                response_users.append(
                    {
                        **_serialize_user(user),
                        "created_at": _iso_or_none(getattr(user, "created_at", None)),
                        "updated_at": _iso_or_none(getattr(user, "updated_at", None)),
                        "active_session_count": active_count,
                        "total_session_count": total_count,
                        "last_activity": _iso_or_none(last_activity_by_user.get(user_uuid)),
                    }
                )

            return {
                "users": response_users,
                "total_users": len(response_users),
                "active_users": active_users,
            }

        @self.app.get(f"{prefix}/users-sessions/sessions")
        async def users_sessions_sessions(_user: Dict[str, Any] = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)):
            sessions = await uow.sessions.list(limit=10000)
            users = await uow.users.list(limit=10000)
            users_by_uuid = {getattr(user, "uuid", None): user for user in users}
            now = datetime.now(timezone.utc)

            response_sessions = []
            active_sessions = 0
            for session in sessions:
                user_uuid = getattr(session, "user_uuid", None)
                user = users_by_uuid.get(user_uuid)
                expires_at = getattr(session, "expires_at", None)
                is_active = _session_is_currently_active(session, now)
                if is_active:
                    active_sessions += 1

                response_sessions.append(
                    {
                        "uuid": getattr(session, "uuid", None),
                        "user_uuid": user_uuid,
                        "device_uuid": getattr(session, "device_uuid", None),
                        "session_type": getattr(session, "session_type", None) or "web",
                        "expires_at": _iso_or_none(expires_at),
                        "created_at": _iso_or_none(getattr(session, "created_at", None)),
                        "is_active": is_active,
                        "time_remaining": _format_session_time_remaining(expires_at, now),
                        "user_full_name": getattr(user, "full_name", None) or "Unknown User",
                        "user_nickname": getattr(user, "nickname", None),
                        "user_type": str(getattr(user, "user_type", "user")) if user else "user",
                        "device_name": getattr(session, "device_uuid", None),
                        "device_type": None,
                    }
                )

            return {
                "sessions": response_sessions,
                "total_sessions": len(response_sessions),
                "active_sessions": active_sessions,
            }

        @self.app.get(f"{prefix}/users-sessions/statistics")
        async def users_sessions_statistics(_user: Dict[str, Any] = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)):
            sessions = await uow.sessions.list(limit=10000)
            users = await uow.users.list(limit=10000)
            users_by_uuid = {getattr(user, "uuid", None): user for user in users}
            now = datetime.now(timezone.utc)

            active_sessions = 0
            expired_sessions = 0
            sessions_by_type: Dict[str, int] = {}
            sessions_by_device_type: Dict[str, int] = {}
            recent_activity = []

            for session in sessions:
                session_type = getattr(session, "session_type", None) or "web"
                sessions_by_type[session_type] = sessions_by_type.get(session_type, 0) + 1

                device_type = "unknown"
                sessions_by_device_type[device_type] = sessions_by_device_type.get(device_type, 0) + 1

                is_active = _session_is_currently_active(session, now)
                if is_active:
                    active_sessions += 1
                else:
                    expired_sessions += 1

                user = users_by_uuid.get(getattr(session, "user_uuid", None))
                recent_activity.append(
                    {
                        "session_uuid": getattr(session, "uuid", None),
                        "created_at": _iso_or_none(getattr(session, "created_at", None)),
                        "user_name": getattr(user, "full_name", None) or "Unknown User",
                        "session_type": session_type,
                        "device_type": device_type,
                    }
                )

            recent_activity.sort(key=lambda item: item.get("created_at") or "", reverse=True)

            return {
                "statistics": {
                    "total_sessions": len(sessions),
                    "active_sessions": active_sessions,
                    "expired_sessions": expired_sessions,
                    "sessions_by_type": sessions_by_type,
                    "sessions_by_device_type": sessions_by_device_type,
                    "average_session_duration": 0,
                },
                "recent_activity": recent_activity[:20],
            }

        @self.app.get(f"{prefix}/users-sessions/users/{{user_uuid}}")
        async def users_sessions_user_detail(
            user_uuid: str,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            user = await uow.users.get_by_id(user_uuid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            credentials = await uow.credentials.get_by_user_uuid(user_uuid)
            sessions = await uow.sessions.list(filters={"user_uuid": user_uuid}, limit=10000)
            now = datetime.now(timezone.utc)

            active_sessions = []
            expired_sessions = 0
            for session in sessions:
                expires_at = getattr(session, "expires_at", None)
                is_currently_active = _session_is_currently_active(session, now)
                session_payload = {
                    "uuid": getattr(session, "uuid", None),
                    "user_uuid": getattr(session, "user_uuid", None),
                    "device_uuid": getattr(session, "device_uuid", None),
                    "session_type": getattr(session, "session_type", None) or "web",
                    "expires_at": _iso_or_none(expires_at),
                    "created_at": _iso_or_none(getattr(session, "created_at", None)),
                    "is_active": is_currently_active,
                    "time_remaining": _format_session_time_remaining(expires_at, now),
                }
                if is_currently_active:
                    active_sessions.append(session_payload)
                else:
                    expired_sessions += 1

            device_ids = sorted({getattr(session, "device_uuid", None) for session in sessions if getattr(session, "device_uuid", None)})
            devices = [
                {
                    "uuid": device_id,
                    "device_name": device_id,
                    "device_type": "unknown",
                    "platform": "unknown",
                    "last_seen": max(
                        (
                            _iso_or_none(getattr(session, "created_at", None))
                            for session in sessions
                            if getattr(session, "device_uuid", None) == device_id
                        ),
                        default=None,
                    ),
                    "is_active": any(
                        _session_is_currently_active(session, now)
                        for session in sessions
                        if getattr(session, "device_uuid", None) == device_id
                    ),
                }
                for device_id in device_ids
            ]

            return {
                "user": {
                    **_serialize_user(user),
                    "created_at": _iso_or_none(getattr(user, "created_at", None)),
                    "updated_at": _iso_or_none(getattr(user, "updated_at", None)),
                },
                "credentials": {
                    "has_pin": bool(getattr(credentials, "password_hash", None)),
                    "failed_attempts": int(getattr(credentials, "failed_attempts", 0) or 0),
                    "is_locked": bool(getattr(credentials, "locked_until", None) and getattr(credentials, "locked_until", None) > now),
                    "locked_until": _iso_or_none(getattr(credentials, "locked_until", None)),
                    "last_login": _iso_or_none(getattr(credentials, "last_login", None)),
                } if credentials else None,
                "active_sessions": active_sessions,
                "devices": devices,
                "statistics": {
                    "total_sessions": len(sessions),
                    "active_sessions": len(active_sessions),
                    "expired_sessions": expired_sessions,
                    "registered_devices": len(devices),
                },
            }

        @self.app.post(f"{prefix}/users-sessions/sessions/{{session_uuid}}/revoke")
        async def users_sessions_revoke_session(
            session_uuid: str,
            request: Request,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            _body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
            existing = await uow.sessions.get_by_id(session_uuid)
            if not existing:
                raise HTTPException(status_code=404, detail="Session not found")

            revoked = await uow.sessions.invalidate_session(session_uuid)
            await uow.commit()
            if not revoked:
                raise HTTPException(status_code=404, detail="Session not found")

            return {"success": True, "message": f"Session {session_uuid} revoked"}

        @self.app.post(f"{prefix}/users-sessions/users/{{user_uuid}}/revoke-all-sessions")
        async def users_sessions_revoke_all_sessions(
            user_uuid: str,
            request: Request,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            _body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
            user = await uow.users.get_by_id(user_uuid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            revoked_count = await uow.sessions.invalidate_all_user_sessions(user_uuid)
            await uow.commit()
            return {
                "success": True,
                "message": "All sessions revoked successfully",
                "revoked_count": int(revoked_count),
            }

        @self.app.post(f"{prefix}/users-sessions/users/{{user_uuid}}/lock")
        async def users_sessions_lock_user(
            user_uuid: str,
            request: Request,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
            user = await uow.users.get_by_id(user_uuid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            lock = bool((body or {}).get("lock", True))
            duration_hours = int((body or {}).get("duration_hours") or 24)
            credentials = await uow.credentials.get_by_user_uuid(user_uuid)
            now = datetime.now(timezone.utc)
            if not credentials:
                credentials = await uow.credentials.create(
                    AuthUserCredentials(
                        uuid=str(uuid_lib.uuid4()),
                        user_uuid=user_uuid,
                        password_hash="",
                        failed_attempts=0,
                        locked_until=None,
                        last_login=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

            if lock:
                locked_until = now + timedelta(hours=duration_hours)
                await uow.credentials.lock_account(user_uuid, locked_until)
            else:
                await uow.credentials.unlock_account(user_uuid)

            await uow.commit()
            return {
                "success": True,
                "message": f"User {'locked' if lock else 'unlocked'} successfully",
                "locked": lock,
            }

        @self.app.post(f"{prefix}/users-sessions/users/{{user_uuid}}/cleanup-sessions")
        async def users_sessions_cleanup_sessions(
            user_uuid: str,
            _user: Dict[str, Any] = Depends(get_current_user),
            uow: UnitOfWork = Depends(get_uow),
        ):
            user = await uow.users.get_by_id(user_uuid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            sessions = await uow.sessions.list(filters={"user_uuid": user_uuid}, limit=10000)
            now = datetime.now(timezone.utc)
            deleted_count = 0
            for session in sessions:
                if (not bool(getattr(session, "is_active", False))) or (getattr(session, "expires_at", now) <= now):
                    deleted = await uow.sessions.delete(getattr(session, "uuid", ""))
                    if deleted:
                        deleted_count += 1

            await uow.commit()
            return {
                "success": True,
                "message": "Expired sessions cleaned up successfully",
                "deleted_count": deleted_count,
            }
        
        # Gateway infrastructure endpoints only
        @self.app.get(f"{prefix}/gateway/status")
        async def gateway_status():
            """Gateway infrastructure status"""
            return {
                "status": "healthy",
                "service": "aico-api-gateway",
                "adapters": ["rest", "websocket", "zeromq"],
                "version": __version__
            }
        
        @self.app.get(f"{prefix}/gateway/metrics")
        async def gateway_metrics():
            """Gateway performance metrics"""
            return {
                "requests_processed": getattr(self, '_requests_processed', 0),
                "active_connections": getattr(self, '_active_connections', 0),
                "uptime": getattr(self, '_uptime', 0)
            }
        
        # Scheduler task trigger endpoint
        @self.app.post(f"{prefix}/scheduler/tasks/{{task_id}}/trigger")
        async def trigger_scheduler_task(task_id: str):
            """Manually trigger a scheduler task to run immediately"""
            try:
                from gateway.core.nats_client import get_gateway_nats_client

                result = await get_gateway_nats_client().request_scheduler_task_trigger(task_id)

                if result.get("success"):
                    return {
                        "success": True,
                        "message": f"Task '{task_id}' triggered successfully",
                        "task_id": task_id
                    }

                return {
                    "success": False,
                    "message": result.get("error", "Failed to trigger task"),
                    "task_id": task_id
                }

            except Exception as e:
                self.logger.error(f"Error triggering task {task_id}: {e}")
                return {
                    "success": False,
                    "message": f"Error triggering task: {str(e)}",
                    "task_id": task_id
                }
        
    
    def mount_router(self, router: APIRouter, prefix: str = "", tags: Optional[list] = None):
        """Mount a domain router to the FastAPI app"""
        self.app.include_router(router, prefix=prefix, tags=tags)
        self.logger.info("Router mounted", extra={
            "prefix": prefix,
            "tags": tags or []
        })
    
    async def start(self) -> None:
        """Start REST adapter (integrates with main FastAPI app)"""
        try:
            port = self.config.get("port", 8771)
            host = self.config.get("host", "0.0.0.0")
            
            # REST adapter now integrates with main FastAPI app - no separate server needed
            # The main FastAPI server handles all REST endpoints
            self.running = True
            self.logger.info(f"REST adapter started for {host}:{port} (using main FastAPI app)")
            
        except Exception as e:
            self.logger.error(f"Failed to start REST adapter: {e}")
            self.running = False
            raise
    
    async def stop(self) -> None:
        """Stop REST adapter (no separate server to stop)"""
        # REST adapter now integrates with main FastAPI app - no separate server to stop
        self.running = False
        self.logger.info("REST adapter stopped")
    
    def is_running(self) -> bool:
        """Check if adapter is running"""
        return self.running
    
    def get_app(self) -> FastAPI:
        """Get FastAPI app instance"""
        return self.app


def create_rest_adapter(config_manager) -> FastAPI:
    """Create and configure REST adapter app"""
    from aico.core.bus import MessageBusBroker
    from aico.security.key_manager import AICOKeyManager
    from ..middleware.auth import AuthenticationManager
    from ..middleware.authz import AuthorizationManager
    from ..middleware.message_router import MessageRouter
    from ..middleware.rate_limiter import RateLimiter
    from ..middleware.validator import MessageValidator
    from ..middleware.security import SecurityMiddleware
    
    # Get configuration
    api_gateway_config = config_manager.get("api_gateway", {})
    
    # Create required components
    key_manager = AICOKeyManager(config_manager)
    auth_manager = AuthenticationManager(config_manager)
    authz_manager = AuthorizationManager(config_manager)
    message_router = MessageRouter(api_gateway_config)
    rate_limiter = RateLimiter(config_manager)
    validator = MessageValidator()
    security_middleware = SecurityMiddleware(config_manager)
    
    # Create REST adapter with all dependencies
    rest_adapter = RESTAdapter(
        config=api_gateway_config,
        auth_manager=auth_manager,
        authz_manager=authz_manager,
        message_router=message_router,
        rate_limiter=rate_limiter,
        validator=validator,
        security_middleware=security_middleware,
        key_manager=key_manager
    )
    
    return rest_adapter.get_app()
