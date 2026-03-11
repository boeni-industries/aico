from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from sqlalchemy import and_, insert, select, update
from sqlalchemy.exc import DBAPIError

from aico.core.logging import get_logger
from aico.common.postgres_dependencies import get_uow_factory

from aico.data.tables import idempotency_requests


logger = get_logger("backend.api_gateway.middleware.idempotency")


_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _sha256_hex(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _is_protected_path(path: str) -> bool:
    # Minimal scoped protection: only endpoints where duplicated side effects matter.
    return (
        path.startswith("/api/v1/system/config/domain/")
        or path == "/api/v1/system/config/reload"
        or path == "/api/v1/system/config/import"
        or path.startswith("/api/v1/system/remediate/")
        or path.startswith("/api/v1/system/health/remediate/")
        or path == "/api/v1/system/health/actions/execute"
        or path.startswith("/api/v1/scheduler/")
        or path.startswith("/api/v1/operations/backup-sets")
        or path.startswith("/api/v1/admin/")
    )


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        ttl_seconds: int = 24 * 3600,
        max_body_bytes: int = 256 * 1024,
    ):
        super().__init__(app)
        self.ttl_seconds = int(ttl_seconds)
        self.max_body_bytes = int(max_body_bytes)
        self._uow_factory = get_uow_factory()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path

        if method not in _MUTATION_METHODS or not _is_protected_path(path):
            return await call_next(request)

        # Require authentication header for these endpoints anyway; scope idempotency by auth token hash.
        auth_header = request.headers.get("authorization", "")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "AUTH_REQUIRED",
                    "message": "Authorization header required",
                },
            )

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key or not str(idem_key).strip():
            return JSONResponse(
                status_code=400,
                content={
                    "error_code": "IDEMPOTENCY_KEY_REQUIRED",
                    "message": "Idempotency-Key header is required",
                },
            )
        idem_key = str(idem_key).strip()

        # Buffer request body so we can hash it and also forward to downstream.
        body_bytes = await request.body()
        if len(body_bytes) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error_code": "IDEMPOTENCY_BODY_TOO_LARGE",
                    "message": "Request body too large for idempotency protection",
                },
            )

        auth_hash = _sha256_hex(auth_header.encode("utf-8"))
        request_hash = _sha256_hex(body_bytes)
        now = datetime.now(timezone.utc)

        async with self._uow_factory() as uow:
            try:
                stmt = (
                    select(
                        idempotency_requests.c.request_hash,
                        idempotency_requests.c.status,
                        idempotency_requests.c.response_status_code,
                        idempotency_requests.c.response_body,
                    )
                    .where(
                        and_(
                            idempotency_requests.c.auth_hash == auth_hash,
                            idempotency_requests.c.idempotency_key == idem_key,
                            idempotency_requests.c.request_method == method,
                            idempotency_requests.c.request_path == path,
                            idempotency_requests.c.expires_at > now,
                        )
                    )
                )
                result = await uow._session.execute(stmt)
                row = result.first()
            except DBAPIError as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error_code": "IDEMPOTENCY_SCHEMA_MISSING",
                        "message": "Idempotency schema not installed (missing aico_core.idempotency_requests)",
                        "details": {"db_error": str(e.__class__.__name__)},
                    },
                )

            if row:
                if row.request_hash != request_hash:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "error_code": "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_REQUEST",
                            "message": "Idempotency-Key was already used for a different request payload",
                        },
                    )

                if row.status == "completed":
                    return JSONResponse(
                        status_code=int(row.response_status_code or 200),
                        content=row.response_body or {},
                    )

                return JSONResponse(
                    status_code=409,
                    content={
                        "error_code": "IDEMPOTENCY_IN_PROGRESS",
                        "message": "Request with same Idempotency-Key is still in progress",
                    },
                )

            await uow._session.execute(
                insert(idempotency_requests).values(
                    auth_hash=auth_hash,
                    idempotency_key=idem_key,
                    request_method=method,
                    request_path=path,
                    request_hash=request_hash,
                    status="in_progress",
                    created_at=now,
                    updated_at=now,
                    expires_at=now + timedelta(seconds=self.ttl_seconds),
                )
            )
            await uow._session.commit()

        # Rebuild request with buffered body for downstream.
        async def receive() -> dict:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        downstream_request = Request(request.scope, receive)

        response = await call_next(downstream_request)

        # Capture JSON response (best-effort). If it isn't JSON, still mark completed.
        response_body_bytes = b""
        async for chunk in response.body_iterator:
            response_body_bytes += chunk

        # Recreate response since we've consumed body_iterator
        headers = dict(response.headers)
        media_type = response.media_type
        status_code = int(response.status_code)

        parsed_body: Optional[object] = None
        content_type = headers.get("content-type", "")
        if response_body_bytes and "application/json" in content_type:
            try:
                parsed_body = json.loads(response_body_bytes.decode("utf-8"))
            except Exception:
                parsed_body = None

        async with self._uow_factory() as uow:
            await uow._session.execute(
                (
                    update(idempotency_requests)
                    .where(
                        and_(
                            idempotency_requests.c.auth_hash == auth_hash,
                            idempotency_requests.c.idempotency_key == idem_key,
                            idempotency_requests.c.request_method == method,
                            idempotency_requests.c.request_path == path,
                        )
                    )
                    .values(
                        status="completed",
                        response_status_code=status_code,
                        response_body=parsed_body,
                        updated_at=datetime.now(timezone.utc),
                    )
                ),
            )
            await uow._session.commit()

        return Response(
            content=response_body_bytes,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )
