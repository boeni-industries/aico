"""
Gateway operations endpoints - proxy to core via NATS.

Gateway is HTTP termination only. All operations business logic lives in core.
These endpoints validate auth and proxy requests to core via NATS request/reply.
"""

from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from aico.common.errors import raise_api_error
from gateway.api.dependencies import get_current_user
from aico.core.logging import get_logger

router = APIRouter(prefix="/operations", tags=["operations"])

logger = get_logger("gateway.api.operations.router")


def require_admin_access(user: dict = Depends(get_current_user)) -> bool:
    roles = user.get("roles") or []
    permissions = user.get("permissions") or set()
    if isinstance(permissions, list):
        permissions = set(permissions)
    if "admin" in roles:
        return True
    if any(str(p).startswith("admin.") for p in permissions):
        return True
    raise_api_error(status_code=403, error_code="HTTP_403", message="Admin access required")


class OperationsDatabasesResponse(BaseModel):
    """Operations databases response."""
    databases: list


class OperationsTopologyResponse(BaseModel):
    """Operations topology response."""
    services: list
    connections: list
    deployment_type: str


class BackupSetsResponse(BaseModel):
    """Backup sets response."""
    backup_sets: list
    total_count: int


class PostgresSchemaResponse(BaseModel):
    tables: list
    columns: dict


class PostgresDetailsResponse(BaseModel):
    database_type: str
    tables: list | None = None


@router.get("/databases", response_model=OperationsDatabasesResponse)
async def get_databases(
    _auth: bool = Depends(require_admin_access)
):
    """
    Get database operations information.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_databases()
        
        return OperationsDatabasesResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_DATABASES_FAILED",
            message=f"Failed to retrieve database operations: {str(e)}",
        )


@router.get("/databases/postgresql/details", response_model=PostgresDetailsResponse)
async def get_postgresql_details(
    _auth: bool = Depends(require_admin_access)
):
    """Get PostgreSQL table details (gateway→core NATS proxy)."""
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_postgresql_details()
        return PostgresDetailsResponse(**data)
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_POSTGRES_DETAILS_FAILED",
            message=f"Failed to retrieve PostgreSQL details: {str(e)}",
        )


@router.get("/databases/postgresql/schema", response_model=PostgresSchemaResponse)
async def get_postgresql_schema(
    _auth: bool = Depends(require_admin_access)
):
    """Get PostgreSQL schema metadata for SQL autocomplete (gateway→core NATS proxy)."""
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_postgresql_schema()
        return PostgresSchemaResponse(**data)
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_POSTGRES_SCHEMA_FAILED",
            message=f"Failed to retrieve PostgreSQL schema metadata: {str(e)}",
        )


@router.get("/topology", response_model=OperationsTopologyResponse)
async def get_topology(
    _auth: bool = Depends(require_admin_access)
):
    """
    Get system topology information.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_topology()

        services = data.get("services") if isinstance(data, dict) else None
        connections = data.get("connections") if isinstance(data, dict) else None
        deployment_type = (data.get("deployment_type") if isinstance(data, dict) else None) or "docker-compose"

        services_count = len(services) if isinstance(services, list) else 0
        connections_count = len(connections) if isinstance(connections, list) else 0
        logger.info(
            "[OPERATIONS_TOPOLOGY] nats_result services=%s connections=%s deployment_type=%s",
            services_count,
            connections_count,
            deployment_type,
        )

        return OperationsTopologyResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_TOPOLOGY_FAILED",
            message=f"Failed to retrieve system topology: {str(e)}",
        )


@router.post("/backup-sets")
async def create_backup_set(
    request: Dict[str, Any],
    _auth: bool = Depends(require_admin_access),
    user: dict = Depends(get_current_user),
):
    """
    Create a new backup set.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        created_by = user.get("user_uuid") or user.get("user_id")
        if created_by:
            request = dict(request or {})
            request["created_by_user_uuid"] = str(created_by)
        data = await nats_client.request_operations_create_backup(request)
        
        return data
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_CREATE_BACKUP_FAILED",
            message=f"Failed to create backup: {str(e)}",
        )


@router.get("/backup-sets", response_model=BackupSetsResponse)
async def get_backup_sets(
    include_deleted: bool = Query(False),
    _auth: bool = Depends(require_admin_access),
    user: dict = Depends(get_current_user),
):
    """
    Get backup sets information.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_backup_sets_with_options(include_deleted=bool(include_deleted))
        
        return BackupSetsResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_BACKUP_SETS_FAILED",
            message=f"Failed to retrieve backup sets: {str(e)}",
        )


@router.get("/backup-sets/{backup_id}/status")
async def get_backup_set_status(
    backup_id: str,
    _auth: bool = Depends(require_admin_access)
):
    """
    Get backup set status and manifest (gateway→core NATS proxy).
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        return await nats_client.request_operations_backup_status(backup_id=str(backup_id))
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_BACKUP_STATUS_FAILED",
            message=f"Failed to get backup status: {str(e)}",
        )


@router.get("/backup-sets/{backup_id}/download")
async def download_backup_set(
    backup_id: str,
    _auth: bool = Depends(require_admin_access)
):
    """
    Download a backup set archive.
    
    Gateway returns a short-lived pre-signed artifact store URL produced by Core.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        return await nats_client.request_operations_backup_download_url(backup_id=str(backup_id), expires_seconds=300)
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_BACKUP_DOWNLOAD_FAILED",
            message=f"Failed to download backup: {str(e)}",
        )


@router.delete("/backup-sets/{backup_id}")
async def delete_backup_set(
    backup_id: str,
    _auth: bool = Depends(require_admin_access),
    user: dict = Depends(get_current_user),
):
    """Soft-delete a backup set and move its artifact to trash (gateway→core NATS proxy)."""
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        deleted_by = user.get("user_uuid") or user.get("user_id")
        return await nats_client.request_operations_delete_backup_set(
            backup_id=backup_id,
            deleted_by_user_uuid=str(deleted_by) if deleted_by else None,
        )
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_DELETE_BACKUP_FAILED",
            message=f"Failed to delete backup: {str(e)}",
        )


@router.delete("/backup-sets/{backup_id}/purge")
async def purge_backup_set(
    backup_id: str,
    _auth: bool = Depends(require_admin_access),
    _user: dict = Depends(get_current_user),
):
    """Purge a backup set tombstone and permanently delete the trashed artifact (gateway→core NATS proxy)."""
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        return await nats_client.request_operations_purge_backup_set(backup_id=backup_id)
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_PURGE_BACKUP_FAILED",
            message=f"Failed to purge backup: {str(e)}",
        )


@router.post("/backup-sets/restore")
async def restore_backup_set(
    request: Dict[str, Any],
    _auth: bool = Depends(require_admin_access)
):
    """
    Restore a backup set.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_restore_backup(request)
        return data
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_RESTORE_BACKUP_FAILED",
            message=f"Failed to restore backup: {str(e)}",
        )
