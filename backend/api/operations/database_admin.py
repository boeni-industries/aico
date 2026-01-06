"""
Database Administration Endpoints - Phase 1 Advanced Features

Provides advanced database management capabilities:
- Table/Collection browser with detailed metrics
- SQL query execution interface
- Storage growth trends and analytics
- Backup creation, history, and restore
"""

import asyncio
import os
import re
import time
import shutil
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import HTTPException, status
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths, get_default_database_path
from backend.api.operations.schemas import (
    DatabaseDetailsResponse, TableInfo, CollectionInfo, LMDBDatabaseInfo,
    QueryResult, SchemaMetadata,
    BackupInfo, BackupResponse, BackupHistoryResponse, RestoreResponse,
    StorageTrendResponse, StorageDataPoint,
)

logger = get_logger("backend", "api.operations.database_admin")


# ============================================================================
# Database Details - Table/Collection Browser
# ============================================================================

async def get_libsql_details(db_connection) -> DatabaseDetailsResponse:
    """Get detailed information about LibSQL database tables"""
    try:
        tables = []
        
        # Get all user tables (exclude sqlite internal tables)
        result = db_connection.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        
        for (table_name,) in result:
            # Get row count
            try:
                count_result = db_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                row_count = count_result[0] if count_result else 0
            except Exception as e:
                logger.warning(f"Failed to get row count for table {table_name}: {e}")
                row_count = 0
            
            # Get column count
            try:
                col_result = db_connection.execute(f"PRAGMA table_info({table_name})").fetchall()
                column_count = len(col_result)
            except Exception as e:
                logger.warning(f"Failed to get column count for table {table_name}: {e}")
                column_count = 0
            
            tables.append(TableInfo(
                name=table_name,
                row_count=row_count,
                columns=column_count,
                size_bytes=None  # Would require page analysis
            ))
        
        return DatabaseDetailsResponse(
            database_type="libsql",
            tables=tables
        )
    except Exception as e:
        logger.error(f"Failed to get LibSQL details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LibSQL details: {str(e)}"
        )


async def get_chromadb_details(request) -> DatabaseDetailsResponse:
    """Get detailed information about ChromaDB collections"""
    try:
        collections = []
        
        # Try to get ChromaDB client from service container
        from backend.core.lifecycle_manager import get_service_container
        container = get_service_container(request)
        
        if container:
            chroma_client = container.get_service("chromadb_client")
            if chroma_client:
                chroma_collections = chroma_client.list_collections()
                
                for collection in chroma_collections:
                    # Get document count
                    doc_count = collection.count()
                    
                    # Get metadata
                    metadata = collection.metadata if hasattr(collection, 'metadata') else {}
                    
                    # Try to get embedding dimension from first document
                    dimension = None
                    if doc_count > 0:
                        try:
                            sample = collection.peek(1)
                            if sample and 'embeddings' in sample and sample['embeddings']:
                                dimension = len(sample['embeddings'][0])
                        except Exception:
                            pass
                    
                    collections.append(CollectionInfo(
                        name=collection.name,
                        document_count=doc_count,
                        metadata=metadata,
                        dimension=dimension
                    ))
        
        return DatabaseDetailsResponse(
            database_type="chromadb",
            collections=collections
        )
    except Exception as e:
        logger.error(f"Failed to get ChromaDB details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ChromaDB details: {str(e)}"
        )


async def get_lmdb_details() -> DatabaseDetailsResponse:
    """Get detailed information about LMDB databases"""
    try:
        databases = []
        
        # Try to get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if memory_manager and hasattr(memory_manager, '_working_store'):
            working_store = memory_manager._working_store
            
            for db_name, db in working_store.dbs.items():
                # Count keys in this database
                key_count = 0
                try:
                    with working_store.env.begin(db=db) as txn:
                        key_count = txn.stat()['entries']
                except Exception as e:
                    logger.warning(f"Failed to get key count for LMDB database {db_name}: {e}")
                
                databases.append(LMDBDatabaseInfo(
                    name=db_name,
                    key_count=key_count,
                    size_bytes=None  # Would require page analysis
                ))
        
        return DatabaseDetailsResponse(
            database_type="lmdb",
            databases=databases
        )
    except Exception as e:
        logger.error(f"Failed to get LMDB details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LMDB details: {str(e)}"
        )


# ============================================================================
# SQL Query Execution
# ============================================================================

# SQL Query Validation Patterns (adapted from GQL validator)
FORBIDDEN_SQL_PATTERNS = [
    r'\bDROP\s+TABLE\b',
    r'\bDROP\s+INDEX\b',
    r'\bDROP\s+VIEW\b',
    r'\bALTER\s+TABLE\b',
    r'\bTRUNCATE\b',
    r'\bCREATE\s+INDEX\b',
    r'\bCREATE\s+TABLE\b',
    r'\bCREATE\s+VIEW\b',
]

DESTRUCTIVE_SQL_PATTERNS = [
    r'\bDELETE\s+FROM\b',
    r'\bUPDATE\s+\w+\s+SET\b',
    r'\bINSERT\s+INTO\b',
    r'\bREPLACE\s+INTO\b',
]


async def get_schema_metadata(db_connection) -> SchemaMetadata:
    """
    Get database schema metadata for autocomplete.
    Returns table names and their columns.
    """
    try:
        tables = []
        columns = {}
        
        # Get all user tables
        result = await asyncio.to_thread(
            db_connection.execute,
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        table_rows = result.fetchall()
        
        for (table_name,) in table_rows:
            tables.append(table_name)
            
            # Get columns for this table
            try:
                col_result = await asyncio.to_thread(
                    db_connection.execute,
                    f"PRAGMA table_info({table_name})"
                )
                col_rows = col_result.fetchall()
                columns[table_name] = [row[1] for row in col_rows]  # row[1] is column name
            except Exception as e:
                logger.warning(f"Failed to get columns for table {table_name}: {e}")
                columns[table_name] = []
        
        return SchemaMetadata(tables=tables, columns=columns)
    except Exception as e:
        logger.error(f"Failed to get schema metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve schema metadata: {str(e)}"
        )


MAX_SQL_QUERY_LENGTH = 10000


def validate_sql_query(query: str, allow_destructive: bool = False) -> tuple[bool, Optional[str], bool]:
    """
    Validate SQL query for security and correctness.
    
    Returns:
        Tuple of (is_valid, error_message, is_destructive)
    """
    # Check query length
    if len(query) > MAX_SQL_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_SQL_QUERY_LENGTH} characters)", False
    
    # Check for empty query
    if not query.strip():
        return False, "Query cannot be empty", False
    
    query_upper = query.upper()
    
    # Check for forbidden patterns (always blocked)
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, query_upper, re.IGNORECASE):
            return False, f"Forbidden operation detected: {pattern.replace('\\b', '').replace('\\s+', ' ')}", False
    
    # Check for destructive patterns (require confirmation)
    is_destructive = False
    for pattern in DESTRUCTIVE_SQL_PATTERNS:
        if re.search(pattern, query_upper, re.IGNORECASE):
            is_destructive = True
            if not allow_destructive:
                return False, "Destructive operation detected. Enable 'Allow Modifications' to execute.", True
    
    # Validate it's a SELECT query if not destructive
    if not is_destructive and not query_upper.strip().startswith('SELECT'):
        # Allow PRAGMA queries for database inspection
        if not query_upper.strip().startswith('PRAGMA'):
            return False, "Only SELECT and PRAGMA queries are allowed in read-only mode", False
    
    return True, None, is_destructive


async def execute_sql_query(
    query: str,
    limit: int,
    db_connection,
    allow_destructive: bool = False
) -> QueryResult:
    """
    Execute a SQL query on LibSQL database.
    
    Security:
    - Validates query for forbidden operations
    - Detects destructive operations (DELETE, UPDATE, INSERT)
    - Requires explicit confirmation for destructive queries
    - Auto-adds LIMIT for SELECT queries
    """
    try:
        # Validate query
        is_valid, error_msg, is_destructive = validate_sql_query(query, allow_destructive)
        if not is_valid:
            logger.warning(f"SQL query validation failed: {error_msg}")
            return QueryResult(
                success=False,
                error=error_msg,
                columns=[],
                rows=[],
                row_count=0,
                is_destructive=is_destructive
            )
        
        query_upper = query.strip().upper()
        
        # Add LIMIT for SELECT queries if not present
        if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"
        
        # Execute query
        result = await asyncio.to_thread(
            db_connection.execute,
            query
        )
        
        rows = await asyncio.to_thread(result.fetchall)
        
        # Get column names
        columns = [desc[0] for desc in result.description] if result.description else []
        
        # Convert rows to list of lists
        row_data = [list(row) for row in rows]
        
        logger.info(f"SQL query executed successfully: {len(row_data)} rows returned")
        
        return QueryResult(
            success=True,
            error=None,
            columns=columns,
            rows=row_data,
            row_count=len(row_data),
            is_destructive=is_destructive
        )
        
    except Exception as e:
        logger.error(f"SQL query execution failed: {e}")
        return QueryResult(
            success=False,
            error=str(e),
            columns=[],
            rows=[],
            row_count=0,
            is_destructive=False
        )


# ============================================================================
# Storage Growth Trends
# ============================================================================

async def get_storage_trends(database_name: str) -> StorageTrendResponse:
    """Get 7-day storage growth trends for a database"""
    try:
        # For now, generate simulated 7-day trend data
        # In production, this would query a metrics database or time-series store
        
        current_size = 0
        data_points = []
        
        if database_name == "LibSQL":
            db_path = get_default_database_path()
            if os.path.exists(db_path):
                current_size = os.path.getsize(db_path)
        elif database_name == "ChromaDB":
            chroma_path = AICOPaths.get_data_directory() / "data" / "memory" / "semantic"
            if os.path.exists(chroma_path):
                for dirpath, dirnames, filenames in os.walk(chroma_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            current_size += os.path.getsize(filepath)
                        except Exception:
                            pass
        elif database_name == "LMDB":
            lmdb_path = AICOPaths.get_data_directory() / "data" / "memory" / "working"
            if os.path.exists(lmdb_path):
                for dirpath, dirnames, filenames in os.walk(lmdb_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            current_size += os.path.getsize(filepath)
                        except Exception:
                            pass
        
        # Generate 7 days of simulated historical data
        # In production, replace with actual historical metrics
        now = datetime.utcnow()
        for i in range(7, 0, -1):
            timestamp = (now - timedelta(days=i)).isoformat()
            # Simulate gradual growth (90-100% of current size)
            simulated_size = int(current_size * (0.90 + (i * 0.01)))
            data_points.append(StorageDataPoint(
                timestamp=timestamp,
                size_bytes=simulated_size
            ))
        
        # Add current data point
        data_points.append(StorageDataPoint(
            timestamp=now.isoformat(),
            size_bytes=current_size
        ))
        
        # Calculate growth rate (bytes per day)
        growth_rate = None
        if len(data_points) >= 2:
            size_diff = data_points[-1].size_bytes - data_points[0].size_bytes
            days_diff = 7
            growth_rate = size_diff / days_diff if days_diff > 0 else 0
        
        return StorageTrendResponse(
            database_name=database_name,
            data_points=data_points,
            current_size=current_size,
            growth_rate=growth_rate
        )
    except Exception as e:
        logger.error(f"Failed to get storage trends for {database_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage trends: {str(e)}"
        )


# ============================================================================
# Backup Management
# ============================================================================

def get_backup_directory() -> Path:
    """Get or create backup directory"""
    backup_dir = AICOPaths.get_data_directory() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_backup_metadata_file() -> Path:
    """Get backup metadata file path"""
    return get_backup_directory() / "backup_metadata.json"


def load_backup_metadata() -> dict:
    """Load backup metadata from file"""
    metadata_file = get_backup_metadata_file()
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            return {"backups": []}
    return {"backups": []}


def save_backup_metadata(metadata: dict):
    """Save backup metadata to file"""
    metadata_file = get_backup_metadata_file()
    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save backup metadata: {e}")


async def create_database_backup(database_name: str) -> BackupResponse:
    """Create a backup of the specified database"""
    try:
        backup_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        backup_dir = get_backup_directory()
        
        source_path = None
        backup_filename = None
        
        if database_name == "LibSQL":
            source_path = get_default_database_path()
            backup_filename = f"libsql_backup_{backup_id}.db"
        elif database_name == "ChromaDB":
            source_path = AICOPaths.get_data_directory() / "data" / "memory" / "semantic"
            backup_filename = f"chromadb_backup_{backup_id}.tar.gz"
        elif database_name == "LMDB":
            source_path = AICOPaths.get_data_directory() / "data" / "memory" / "working"
            backup_filename = f"lmdb_backup_{backup_id}.tar.gz"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown database: {database_name}"
            )
        
        if not os.path.exists(source_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database not found: {database_name}"
            )
        
        backup_path = backup_dir / backup_filename
        
        # Perform backup
        if database_name == "LibSQL":
            # Simple file copy for SQLite
            shutil.copy2(source_path, backup_path)
        else:
            # Create tar.gz for directory-based databases
            shutil.make_archive(
                str(backup_path).replace('.tar.gz', ''),
                'gztar',
                source_path
            )
        
        backup_size = os.path.getsize(backup_path)
        
        # Save backup metadata
        metadata = load_backup_metadata()
        backup_info = BackupInfo(
            id=backup_id,
            database_name=database_name,
            created_at=timestamp,
            size_bytes=backup_size,
            backup_path=str(backup_path),
            status="completed"
        )
        metadata["backups"].append(backup_info.model_dump())
        save_backup_metadata(metadata)
        
        return BackupResponse(
            success=True,
            backup_info=backup_info,
            message=f"Backup created successfully: {backup_filename}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create backup for {database_name}: {e}")
        return BackupResponse(
            success=False,
            backup_info=None,
            message=f"Backup failed: {str(e)}"
        )


async def get_backup_history(database_name: Optional[str] = None) -> BackupHistoryResponse:
    """Get backup history, optionally filtered by database"""
    try:
        metadata = load_backup_metadata()
        backups = metadata.get("backups", [])
        
        # Filter by database if specified
        if database_name:
            backups = [b for b in backups if b.get("database_name") == database_name]
        
        # Convert to BackupInfo objects
        backup_infos = [BackupInfo(**b) for b in backups]
        
        # Sort by created_at descending (newest first)
        backup_infos.sort(key=lambda x: x.created_at, reverse=True)
        
        return BackupHistoryResponse(
            backups=backup_infos,
            total_count=len(backup_infos)
        )
    except Exception as e:
        logger.error(f"Failed to get backup history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve backup history: {str(e)}"
        )


async def restore_from_backup(backup_id: str) -> RestoreResponse:
    """Restore a database from backup"""
    try:
        metadata = load_backup_metadata()
        backups = metadata.get("backups", [])
        
        # Find the backup
        backup = next((b for b in backups if b.get("id") == backup_id), None)
        if not backup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup not found: {backup_id}"
            )
        
        backup_path = Path(backup["backup_path"])
        if not backup_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup file not found: {backup_path}"
            )
        
        database_name = backup["database_name"]
        
        # Determine restore target
        if database_name == "LibSQL":
            target_path = get_default_database_path()
            # Create backup of current database before restore
            current_backup = f"{target_path}.pre_restore_{int(time.time())}"
            shutil.copy2(target_path, current_backup)
            # Restore
            shutil.copy2(backup_path, target_path)
        elif database_name in ["ChromaDB", "LMDB"]:
            # For directory-based databases, extract tar.gz
            if database_name == "ChromaDB":
                target_path = AICOPaths.get_data_directory() / "data" / "memory" / "semantic"
            else:
                target_path = AICOPaths.get_data_directory() / "data" / "memory" / "working"
            
            # Backup current directory
            current_backup = f"{target_path}.pre_restore_{int(time.time())}"
            shutil.copytree(target_path, current_backup)
            
            # Remove current directory and extract backup
            shutil.rmtree(target_path)
            shutil.unpack_archive(backup_path, target_path)
        
        return RestoreResponse(
            success=True,
            message=f"Database restored successfully from backup {backup_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore from backup {backup_id}: {e}")
        return RestoreResponse(
            success=False,
            message=f"Restore failed: {str(e)}"
        )
