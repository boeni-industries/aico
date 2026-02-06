"""
Database Administration Routes - Phase 1 Advanced Features

Router endpoints for advanced database management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Request, Body, UploadFile, File

from backend.api.system.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork
from backend.api.operations.schemas import (
    DatabaseDetailsResponse,
    QueryRequest, QueryResult,
    BackupSetCreateRequest, BackupSetCreateResponse,
    BackupSetListResponse, BackupSetStatusResponse,
    BackupSetUploadResponse,
    BackupSetRestoreRequest, BackupSetRestoreResponse,
    BackupSetDeleteResponse,
    BackupSetPruneRequest, BackupSetPruneResponse,
    StorageTrendResponse,
    LMDBBrowseRequest, LMDBBrowseResponse, LMDBKeyValueResponse,
    LMDBDeleteRequest, LMDBDeleteResponse, OrphanedEntriesResponse,
    ChromaDBSearchRequest, ChromaDBSearchResponse,
    ChromaDBDeleteRequest, ChromaDBDeleteResponse,
    ChromaDBBrowseResponse,
)
from backend.api.operations import database_admin
from backend.api.operations import backup_sets

router = APIRouter()


# ============================================================================
# Database Details - Table/Collection Browser
# ============================================================================

@router.get("/databases/{database_type}/details", response_model=DatabaseDetailsResponse)
async def get_database_details(
    database_type: str,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> DatabaseDetailsResponse:
    """
    Get detailed information about database tables/collections.
    
    - **postgresql**: Returns list of tables with row counts
    - **chromadb**: Returns list of collections with document counts
    - **lmdb**: Returns list of databases with key counts
    - **influxdb**: Returns basic database information
    """
    if database_type == "postgresql":
        return await database_admin.get_postgresql_details()
    elif database_type == "chromadb":
        return await database_admin.get_chromadb_details(request)
    elif database_type == "lmdb":
        return await database_admin.get_lmdb_details()
    elif database_type == "influxdb":
        return await database_admin.get_influxdb_details()
    else:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown database type: {database_type}"
        )


# ============================================================================
# SQL Query Execution
# ============================================================================

@router.post("/databases/postgresql/query", response_model=QueryResult)
async def execute_query(
    query_request: QueryRequest,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> QueryResult:
    """
    Execute a SQL query on PostgreSQL database.
    
    **Security**: Only SELECT queries are allowed.
    """
    return await database_admin.execute_sql_query(
        query_request.query,
        query_request.limit or 100,
        uow
    )


@router.post("/databases/influxdb/query", response_model=QueryResult)
async def execute_influx_query(
    query_request: QueryRequest,
    user: Annotated[dict, Depends(get_current_user)]
) -> QueryResult:
    """
    Execute a Flux query on InfluxDB.
    
    Returns time-series data from the configured InfluxDB instance.
    """
    return await database_admin.execute_influx_query(query_request.query)


# ============================================================================
# Storage Growth Trends
# ============================================================================

@router.get("/databases/{database_name}/trends", response_model=StorageTrendResponse)
async def get_database_trends(
    database_name: str,
    user: Annotated[dict, Depends(get_current_user)]
) -> StorageTrendResponse:
    """
    Get 7-day storage growth trends for a database.
    
    Returns historical data points and growth rate.
    """
    return await database_admin.get_storage_trends(database_name)


# ============================================================================
# Backup Sets (coordinated backups)
# ============================================================================


@router.post("/backup-sets", response_model=BackupSetCreateResponse)
async def create_backup_set(
    request: BackupSetCreateRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetCreateResponse:
    """Create a coordinated backup set (PostgreSQL + ChromaDB + LMDB + optional InfluxDB)."""
    return await backup_sets.create_backup_set(request)


@router.get("/backup-sets", response_model=BackupSetListResponse)
async def list_backup_sets(
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetListResponse:
    """List known backup sets."""
    return backup_sets.list_backup_sets()


@router.get("/backup-sets/{backup_id}/status", response_model=BackupSetStatusResponse)
async def get_backup_set_status(
    backup_id: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetStatusResponse:
    """Return backup set status and parsed manifest."""
    return backup_sets.get_backup_set_status(backup_id)


@router.get("/backup-sets/{backup_id}/download")
async def download_backup_set(
    backup_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Download a backup set as a tar.gz archive."""
    return backup_sets.download_backup_set(backup_id)


@router.delete("/backup-sets/{backup_id}", response_model=BackupSetDeleteResponse)
async def delete_backup_set(
    backup_id: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetDeleteResponse:
    """Delete a backup set (directory + tar.gz archive) and update the registry."""
    return backup_sets.delete_backup_set(backup_id)


@router.post("/backup-sets/prune", response_model=BackupSetPruneResponse)
async def prune_backup_sets(
    request: BackupSetPruneRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetPruneResponse:
    """Prune old backup sets based on retention policy (supports dry-run)."""
    return backup_sets.prune_backup_sets(request)


@router.post("/backup-sets/upload", response_model=BackupSetUploadResponse)
async def upload_backup_set(
    file: UploadFile = File(...),
    output_path: Optional[str] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
) -> BackupSetUploadResponse:
    """Upload/import a backup set archive."""
    return await backup_sets.upload_backup_set(file, output_path)


@router.post("/backup-sets/restore", response_model=BackupSetRestoreResponse)
async def restore_backup_set(
    request: BackupSetRestoreRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> BackupSetRestoreResponse:
    """Restore a backup set. Restores to postgres-shadow first and verifies before optionally restoring to primary."""
    return await backup_sets.restore_backup_set(request)


# ============================================================================
# LMDB Browsing
# ============================================================================

@router.post("/databases/lmdb/browse", response_model=LMDBBrowseResponse)
async def browse_lmdb_keys(
    browse_request: LMDBBrowseRequest,
    user: Annotated[dict, Depends(get_current_user)]
) -> LMDBBrowseResponse:
    """
    Browse LMDB keys with filtering and pagination.
    
    Supports filtering by:
    - Key prefix
    - User ID (searches in value JSON)
    - Pagination (limit/offset)
    """
    return await database_admin.browse_lmdb_keys(browse_request)


@router.get("/databases/lmdb/{database_name}/key/{key}", response_model=LMDBKeyValueResponse)
async def get_lmdb_key_value(
    database_name: str,
    key: str,
    user: Annotated[dict, Depends(get_current_user)]
) -> LMDBKeyValueResponse:
    """
    Get the full value for a specific LMDB key.
    
    Returns the complete JSON value for the key.
    """
    return await database_admin.get_lmdb_key_value(database_name, key)


# ============================================================================
# ChromaDB Browsing
# ============================================================================

@router.post("/databases/chromadb/search", response_model=ChromaDBSearchResponse)
async def search_chromadb(
    search_request: ChromaDBSearchRequest,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)]
) -> ChromaDBSearchResponse:
    """
    Search ChromaDB using semantic similarity.
    
    Supports:
    - Natural language queries
    - Filtering by user_id, conversation_id
    - Minimum similarity threshold
    - Result limit
    """
    return await database_admin.search_chromadb(search_request, request)


@router.delete("/databases/chromadb/documents", response_model=ChromaDBDeleteResponse)
async def delete_chromadb_documents(
    delete_request: ChromaDBDeleteRequest,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)]
) -> ChromaDBDeleteResponse:
    """
    Delete documents from ChromaDB collection.
    """
    return await database_admin.delete_chromadb_documents(delete_request, request)


@router.get("/databases/chromadb/collections/{collection_name}/browse", response_model=ChromaDBBrowseResponse)
async def browse_chromadb_collection(
    collection_name: str,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    limit: int = 100
) -> ChromaDBBrowseResponse:
    """
    Browse all documents in a ChromaDB collection.
    """
    return await database_admin.browse_chromadb_collection(collection_name, request, limit)


# ============================================================================
# LMDB Delete & Orphaned Entries
# ============================================================================

@router.delete("/databases/lmdb/keys", response_model=LMDBDeleteResponse)
async def delete_lmdb_keys(
    delete_request: LMDBDeleteRequest,
    user: Annotated[dict, Depends(get_current_user)]
) -> LMDBDeleteResponse:
    """
    Delete multiple keys from LMDB database.
    """
    return await database_admin.delete_lmdb_keys(delete_request)


@router.get("/databases/lmdb/{database_name}/orphaned", response_model=OrphanedEntriesResponse)
async def find_orphaned_entries(
    database_name: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> OrphanedEntriesResponse:
    """
    Find LMDB entries that reference non-existent users.
    
    This helps identify and clean up orphaned data from deleted users.
    """
    return await database_admin.find_orphaned_lmdb_entries(database_name, uow)
