"""
Gateway operations endpoints - proxy to core via NATS.

Gateway is HTTP termination only. All operations business logic lives in core.
These endpoints validate auth and proxy requests to core via NATS request/reply.
"""

from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.scheduler.dependencies import require_admin_access
from backend.api.errors import raise_api_error
from aico.core.logging import get_logger

router = APIRouter(prefix="/operations", tags=["operations"])

logger = get_logger("backend.api.operations.router_gateway")


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
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
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
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

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
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

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
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
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

        if services_count == 0 or connections_count == 0:
            fallback = {
                "services": [
                    {
                        "id": "aico-studio",
                        "name": "AICO-Studio",
                        "type": "studio",
                        "tier": "enterprise",
                        "status": "healthy",
                        "version": "0.5.2",
                        "host": "localhost",
                        "port": 3002,
                        "uptime": "External",
                    },
                    {
                        "id": "gateway",
                        "name": "Gateway (API Access)",
                        "type": "gateway",
                        "status": "healthy",
                        "version": "0.5.2",
                        "host": "localhost",
                        "port": 8771,
                        "uptime": "n/a",
                    },
                    {
                        "id": "core",
                        "name": "Core",
                        "type": "backend",
                        "status": "healthy",
                        "version": "0.5.2",
                        "host": "aico-core",
                        "uptime": "n/a",
                    },
                    {
                        "id": "modelservice",
                        "name": "Model Service",
                        "type": "modelservice",
                        "status": "healthy",
                        "version": "0.5.2",
                        "host": "aico-modelservice",
                        "uptime": "n/a",
                    },
                    {
                        "id": "nats",
                        "name": "NATS",
                        "type": "bus",
                        "status": "healthy",
                        "version": "2.10",
                        "host": "aico-nats",
                        "port": 4222,
                        "uptime": "n/a",
                    },
                    {
                        "id": "postgres",
                        "name": "PostgreSQL",
                        "type": "database",
                        "status": "healthy",
                        "version": "16",
                        "host": "aico-postgres",
                        "port": 5432,
                        "uptime": "n/a",
                    },
                    {
                        "id": "loki",
                        "name": "Loki (Logs)",
                        "type": "logs",
                        "status": "healthy",
                        "version": "3.6.7",
                        "host": "aico-loki",
                        "port": 3100,
                        "uptime": "n/a",
                    },
                    {
                        "id": "tempo",
                        "name": "Tempo (Traces)",
                        "type": "traces",
                        "status": "healthy",
                        "version": "2.10",
                        "host": "aico-tempo",
                        "port": 3200,
                        "uptime": "n/a",
                    },
                    {
                        "id": "otel-collector",
                        "name": "OTel Collector",
                        "type": "telemetry",
                        "status": "healthy",
                        "version": "latest",
                        "host": "aico-otel-collector",
                        "port": 4317,
                        "uptime": "n/a",
                    },
                    {
                        "id": "grafana",
                        "name": "Grafana",
                        "type": "dashboard",
                        "status": "healthy",
                        "version": "12.4",
                        "host": "aico-grafana",
                        "port": 3000,
                        "uptime": "n/a",
                    },
                    {
                        "id": "prometheus",
                        "name": "Prometheus",
                        "type": "metrics",
                        "status": "healthy",
                        "version": "v3",
                        "host": "aico-prometheus",
                        "port": 9090,
                        "uptime": "n/a",
                    },
                ],
                "connections": [
                    {"from": "aico-studio", "to": "gateway", "protocol": "HTTP (API)", "port": 8771, "status": "active"},
                    {"from": "gateway", "to": "nats", "protocol": "NATS", "port": 4222, "status": "active"},
                    {"from": "nats", "to": "core", "protocol": "NATS", "port": 4222, "status": "active"},
                    {"from": "core", "to": "postgres", "protocol": "PostgreSQL", "port": 5432, "status": "active"},
                    {"from": "core", "to": "nats", "protocol": "NATS", "port": 4222, "status": "active"},
                    {"from": "core", "to": "modelservice", "protocol": "HTTP", "status": "active"},
                    {"from": "gateway", "to": "otel-collector", "protocol": "OTLP/gRPC", "port": 4317, "status": "active"},
                    {"from": "core", "to": "otel-collector", "protocol": "OTLP/gRPC", "port": 4317, "status": "active"},
                    {"from": "modelservice", "to": "otel-collector", "protocol": "OTLP/gRPC", "port": 4317, "status": "active"},
                    {"from": "otel-collector", "to": "tempo", "protocol": "OTLP/gRPC", "port": 4317, "status": "active"},
                    {"from": "grafana", "to": "loki", "protocol": "HTTP", "port": 3100, "status": "active"},
                    {"from": "grafana", "to": "tempo", "protocol": "HTTP", "port": 3200, "status": "active"},
                    {"from": "grafana", "to": "prometheus", "protocol": "HTTP", "port": 9090, "status": "active"},
                ],
                "deployment_type": deployment_type,
            }
            logger.warning(
                "[OPERATIONS_TOPOLOGY] falling back to gateway topology services=%s connections=%s",
                len(fallback["services"]),
                len(fallback["connections"]),
            )
            return OperationsTopologyResponse(**fallback)

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
    _auth: bool = Depends(require_admin_access)
):
    """
    Create a new backup set.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
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
    _auth: bool = Depends(require_admin_access)
):
    """
    Get backup sets information.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_backup_sets()
        
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
    Get backup set status and manifest.
    
    Gateway directly calls core function for simple data retrieval.
    """
    try:
        from backend.api.operations.backup_sets import get_backup_set_status_async as core_status_async

        return await core_status_async(backup_id)
        
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
    Download a backup set as tar.gz archive.
    
    File downloads can't use NATS request/reply, so gateway directly calls core function.
    """
    try:
        from backend.api.operations.backup_sets import download_backup_set as core_download
        
        return core_download(backup_id)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_DOWNLOAD_BACKUP_FAILED",
            message=f"Failed to download backup: {str(e)}",
        )


@router.delete("/backup-sets/{backup_id}")
async def delete_backup_set(
    backup_id: str,
    _auth: bool = Depends(require_admin_access)
):
    """Delete a backup set and its remote archive (gateway direct call)."""
    try:
        from backend.api.operations.backup_sets import delete_backup_set_async as core_delete_async

        return await core_delete_async(backup_id)
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_DELETE_BACKUP_FAILED",
            message=f"Failed to delete backup: {str(e)}",
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
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        data = await nats_client.request_operations_restore_backup(request)
        return data
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="OPERATIONS_RESTORE_BACKUP_FAILED",
            message=f"Failed to restore backup: {str(e)}",
        )
