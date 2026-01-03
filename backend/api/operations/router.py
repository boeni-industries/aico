"""
Operations API Router

REST API endpoints for operations monitoring, database metrics, and active sessions.
"""

import os
import sqlite3
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta

from aico.core.logging import get_logger
from backend.api.operations.schemas import (
    DatabaseStatsResponse, DatabaseMetrics,
    ActiveSessionsResponse, UserSession
)
from backend.api.system.dependencies import get_current_user, get_db_connection

logger = get_logger("backend", "api.operations")

router = APIRouter()


def get_file_size(path: str) -> int:
    """Get file size in bytes, return 0 if file doesn't exist"""
    try:
        if os.path.exists(path):
            return os.path.getsize(path)
    except Exception as e:
        logger.warning(f"Failed to get file size for {path}: {e}")
    return 0


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


@router.get("/databases", response_model=DatabaseStatsResponse)
async def get_database_stats(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> DatabaseStatsResponse:
    """
    Get database statistics for all databases (LibSQL, ChromaDB, LMDB).
    
    Returns metrics including size, table/collection counts, and health status.
    """
    try:
        databases = []
        
        # LibSQL Database
        try:
            from aico.core.paths import get_default_database_path
            db_path = get_default_database_path()
            db_size = get_file_size(str(db_path))
            
            # Get table count
            table_count = 0
            try:
                result = db_connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()
                table_count = result[0] if result else 0
            except Exception as e:
                logger.warning(f"Failed to get LibSQL table count: {e}")
            
            # Get WAL size
            wal_path = f"{db_path}-wal"
            wal_size = get_file_size(wal_path)
            
            databases.append(DatabaseMetrics(
                name="LibSQL",
                type="libsql",
                size_bytes=db_size,
                status="healthy" if db_size > 0 else "degraded",
                location=str(db_path),
                table_count=table_count,
                connection_count=1,  # At least one (current connection)
                wal_size_bytes=wal_size,
            ))
        except Exception as e:
            logger.error(f"Failed to get LibSQL metrics: {e}")
            databases.append(DatabaseMetrics(
                name="LibSQL",
                type="libsql",
                size_bytes=0,
                status="critical",
                location="unknown",
            ))
        
        # ChromaDB
        try:
            from aico.core.paths import AICOPaths
            chroma_path = AICOPaths.get_data_directory() / "data" / "memory" / "semantic"
            
            # Get directory size
            chroma_size = 0
            if os.path.exists(str(chroma_path)):
                for dirpath, dirnames, filenames in os.walk(str(chroma_path)):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        chroma_size += get_file_size(filepath)
            
            # Get collection count
            collection_count = 0
            document_count = 0
            chroma_error = None
            try:
                # Try to get ChromaDB client from service container
                from backend.core.lifecycle_manager import get_service_container
                container = get_service_container(request)
                if container:
                    chroma_client = container.get_service("chromadb_client")
                    if chroma_client:
                        collections = chroma_client.list_collections()
                        collection_count = len(collections)
                        for collection in collections:
                            document_count += collection.count()
                    else:
                        chroma_error = "ChromaDB client not available in service container"
                        logger.error("ChromaDB client not found in service container")
                else:
                    chroma_error = "Service container not available"
                    logger.error("Service container not available for ChromaDB stats")
            except Exception as e:
                chroma_error = f"Failed to query ChromaDB: {str(e)}"
                logger.exception(f"Could not get ChromaDB stats: {e}")
            
            # Determine status and error details
            if chroma_size == 0 and not os.path.exists(str(chroma_path)):
                status = "degraded"
                error_details = "ChromaDB directory does not exist"
                logger.error(f"ChromaDB directory does not exist: {chroma_path}")
            elif chroma_size == 0:
                status = "degraded"
                error_details = "ChromaDB directory is empty"
                logger.error(f"ChromaDB directory is empty: {chroma_path}")
            elif chroma_error:
                status = "degraded"
                error_details = chroma_error
            else:
                status = "healthy"
                error_details = None
            
            databases.append(DatabaseMetrics(
                name="ChromaDB",
                type="chromadb",
                size_bytes=chroma_size,
                status=status,
                location=str(chroma_path),
                error_details=error_details,
                collection_count=collection_count,
                document_count=document_count,
                index_size_bytes=chroma_size,  # Approximate
            ))
        except Exception as e:
            logger.error(f"Failed to get ChromaDB metrics: {e}")
            databases.append(DatabaseMetrics(
                name="ChromaDB",
                type="chromadb",
                size_bytes=0,
                status="critical",
                location="unknown",
                error_details=f"Critical error: {str(e)}",
            ))
        
        # LMDB
        try:
            lmdb_path = AICOPaths.get_data_directory() / "data" / "memory" / "working"
            
            # Get directory size
            lmdb_size = 0
            if os.path.exists(str(lmdb_path)):
                for dirpath, dirnames, filenames in os.walk(str(lmdb_path)):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        lmdb_size += get_file_size(filepath)
            
            # Get database and key counts
            db_count = 0
            key_count = 0
            map_size = 0
            lmdb_error = None
            try:
                from aico.ai import ai_registry
                memory_manager = ai_registry.get("memory")
                if memory_manager and hasattr(memory_manager, '_working_store'):
                    working_store = memory_manager._working_store
                    db_count = len(working_store.dbs)
                    map_size = working_store.env.info()['map_size']
                    
                    # Count keys across all databases
                    for db_name, db in working_store.dbs.items():
                        with working_store.env.begin(db=db) as txn:
                            key_count += txn.stat()['entries']
                else:
                    lmdb_error = "Memory manager not available or missing working store"
                    logger.error("Memory manager not available or missing working store for LMDB stats")
            except Exception as e:
                lmdb_error = f"Failed to query LMDB: {str(e)}"
                logger.exception(f"Could not get LMDB stats: {e}")
            
            # Determine status and error details
            if lmdb_size == 0 and not os.path.exists(str(lmdb_path)):
                status = "degraded"
                error_details = "LMDB directory does not exist"
                logger.error(f"LMDB directory does not exist: {lmdb_path}")
            elif lmdb_size == 0:
                status = "degraded"
                error_details = "LMDB directory is empty"
                logger.error(f"LMDB directory is empty: {lmdb_path}")
            elif lmdb_error:
                status = "degraded"
                error_details = lmdb_error
            else:
                status = "healthy"
                error_details = None
            
            databases.append(DatabaseMetrics(
                name="LMDB",
                type="lmdb",
                size_bytes=lmdb_size,
                status=status,
                location=str(lmdb_path),
                error_details=error_details,
                database_count=db_count,
                key_count=key_count,
                map_size_bytes=map_size,
            ))
        except Exception as e:
            logger.error(f"Failed to get LMDB metrics: {e}")
            databases.append(DatabaseMetrics(
                name="LMDB",
                type="lmdb",
                size_bytes=0,
                status="critical",
                location="unknown",
                error_details=f"Critical error: {str(e)}",
            ))
        
        return DatabaseStatsResponse(databases=databases)
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve database statistics: {str(e)}"
        )


@router.get("/sessions", response_model=ActiveSessionsResponse)
async def get_active_sessions(
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> ActiveSessionsResponse:
    """
    Get active user sessions.
    
    Returns list of users with active sessions and their last activity.
    """
    try:
        sessions = []
        
        # Query auth_sessions and user_profiles tables for active sessions
        try:
            # Get active sessions (last activity within 1 hour)
            cutoff_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            
            result = db_connection.execute(
                """
                SELECT 
                    p.uuid,
                    p.full_name,
                    p.nickname,
                    COUNT(DISTINCT s.uuid) as session_count,
                    MAX(s.created_at) as last_activity
                FROM user_profiles p
                LEFT JOIN auth_sessions s ON p.uuid = s.user_uuid
                WHERE s.is_active = 1 
                  AND s.created_at > ?
                GROUP BY p.uuid, p.full_name, p.nickname
                ORDER BY last_activity DESC
                """,
                [cutoff_time]
            ).fetchall()
            
            for row in result:
                user_uuid, full_name, nickname, session_count, last_activity = row
                
                # Format last activity
                try:
                    activity_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    time_diff = datetime.utcnow() - activity_time
                    
                    if time_diff.total_seconds() < 60:
                        activity_str = "Active now"
                    elif time_diff.total_seconds() < 3600:
                        minutes = int(time_diff.total_seconds() / 60)
                        activity_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        hours = int(time_diff.total_seconds() / 3600)
                        activity_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
                except:
                    activity_str = last_activity
                
                sessions.append(UserSession(
                    user_uuid=user_uuid,
                    full_name=full_name,
                    nickname=nickname,
                    session_count=session_count,
                    last_activity=activity_str,
                ))
        except Exception as e:
            logger.warning(f"Failed to query user sessions: {e}")
            # Fallback: return current user from JWT token
            sessions.append(UserSession(
                user_uuid=user.get("user_uuid", "unknown"),
                full_name=user.get("full_name", "Current User"),
                nickname=user.get("nickname"),
                session_count=1,
                last_activity="Active now",
            ))
        
        return ActiveSessionsResponse(
            sessions=sessions,
            total_sessions=sum(s.session_count for s in sessions)
        )
        
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active sessions: {str(e)}"
        )
