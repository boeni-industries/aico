"""
Database Administration Routes - Phase 1 Advanced Features

Router endpoints for advanced database management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Request, Body

from backend.api.system.dependencies import get_current_user, get_db_connection
from backend.api.operations.schemas import (
    DatabaseDetailsResponse,
    QueryRequest, QueryResult,
    BackupResponse, BackupHistoryResponse, RestoreRequest, RestoreResponse,
    StorageTrendResponse,
    LMDBBrowseRequest, LMDBBrowseResponse, LMDBKeyValueResponse,
    ChromaDBSearchRequest, ChromaDBSearchResponse,
)
from backend.api.operations import database_admin

router = APIRouter()


# ============================================================================
# Database Details - Table/Collection Browser
# ============================================================================

@router.get("/databases/{database_type}/details", response_model=DatabaseDetailsResponse)
async def get_database_details(
    database_type: str,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> DatabaseDetailsResponse:
    """
    Get detailed information about database tables/collections.
    
    - **libsql**: Returns list of tables with row counts
    - **chromadb**: Returns list of collections with document counts
    - **lmdb**: Returns list of databases with key counts
    """
    if database_type == "libsql":
        return await database_admin.get_libsql_details(db_connection)
    elif database_type == "chromadb":
        return await database_admin.get_chromadb_details(request)
    elif database_type == "lmdb":
        return await database_admin.get_lmdb_details()
    else:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown database type: {database_type}"
        )


# ============================================================================
# SQL Query Execution
# ============================================================================

@router.post("/databases/libsql/query", response_model=QueryResult)
async def execute_query(
    query_request: QueryRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> QueryResult:
    """
    Execute a SQL query on LibSQL database.
    
    **Security**: Only SELECT queries are allowed.
    """
    return await database_admin.execute_sql_query(
        query_request.query,
        query_request.limit or 100,
        db_connection
    )


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
# Backup Management
# ============================================================================

@router.post("/databases/{database_name}/backup", response_model=BackupResponse)
async def create_backup(
    database_name: str,
    user: Annotated[dict, Depends(get_current_user)]
) -> BackupResponse:
    """
    Create a backup of the specified database.
    
    Supports: LibSQL, ChromaDB, LMDB
    """
    return await database_admin.create_database_backup(database_name)


@router.get("/databases/backups", response_model=BackupHistoryResponse)
async def get_backups(
    database_name: Optional[str] = None,
    user: Annotated[dict, Depends(get_current_user)] = None
) -> BackupHistoryResponse:
    """
    Get backup history, optionally filtered by database name.
    
    Returns list of backups sorted by creation date (newest first).
    """
    return await database_admin.get_backup_history(database_name)


@router.post("/databases/backups/restore", response_model=RestoreResponse)
async def restore_backup(
    restore_request: RestoreRequest,
    user: Annotated[dict, Depends(get_current_user)]
) -> RestoreResponse:
    """
    Restore a database from backup.
    
    **Warning**: This will replace the current database with the backup.
    A pre-restore backup of the current database will be created automatically.
    """
    return await database_admin.restore_from_backup(restore_request.backup_id)


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
