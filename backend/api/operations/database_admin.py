"""
Database Administration Endpoints - Phase 1 Advanced Features

Provides advanced database management capabilities:
- Table browser with detailed metrics
- SQL query execution interface
- Storage growth trends and analytics
"""

import asyncio
import os
import re
import time
import shutil
import uuid
import json
from datetime import datetime, timedelta, UTC
from typing import Optional, List
from pathlib import Path

from fastapi import HTTPException, status
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths, get_default_database_path
from backend.api.operations.schemas import (
    DatabaseDetailsResponse, TableInfo, CollectionInfo,
    QueryRequest, QueryResult,
    StorageTrendResponse,
    SchemaMetadata,
)

logger = get_logger("backend.api.operations.database_admin")


def _resolve_postgres_connection_params() -> tuple[str, int, str, str, str]:
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    from aico.security.credential_provider import CredentialProvider

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_config = config.get("postgres", {})

    db_user = pg_config.get("user", "postgres")
    provider = CredentialProvider()
    db_password = provider.get("pg_password")
    if not db_password:
        try:
            key_manager = AICOKeyManager(config)
            db_password = key_manager.get_database_password("postgres", username=db_user)
        except Exception:
            db_password = None

    if not db_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to retrieve schema metadata: PostgreSQL password missing. "
                "Configure pg_password via Docker/Compose secrets."
            ),
        )

    host = os.environ.get("AICO_PG_HOST") or pg_config.get("host") or "127.0.0.1"
    port = int(pg_config.get("port", 5432))
    database = (
        os.environ.get("AICO_TEST_DB_NAME")
        or os.environ.get("AICO_POSTGRES_DATABASE")
        or pg_config.get("db_name")
        or pg_config.get("database")
        or "aico"
    )

    return host, port, database, db_user, db_password


# ============================================================================
# Database Details - Table/Collection Browser
# ============================================================================

async def get_postgresql_details() -> DatabaseDetailsResponse:
    """Get detailed information about PostgreSQL database tables"""
    try:
        import psycopg2

        host, port, database, db_user, db_password = _resolve_postgres_connection_params()
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=db_user,
            password=db_password,
            connect_timeout=5
        )
        
        tables = []
        
        with conn.cursor() as cur:
            # Get all user tables from aico_core schema
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_rows = cur.fetchall()
            
            for (table_name,) in table_rows:
                # Get row count
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "aico_core"."{table_name}"')
                    row_count = cur.fetchone()[0]
                except Exception as e:
                    logger.warning(f"Failed to get row count for table {table_name}: {e}")
                    row_count = 0
                
                # Get column count from PostgreSQL information_schema
                try:
                    cur.execute(
                        "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'aico_core' AND table_name = %s",
                        (table_name,)
                    )
                    column_count = cur.fetchone()[0]
                except Exception as e:
                    logger.warning(f"Failed to get column count for table {table_name}: {e}")
                    column_count = 0
                
                # Get table size
                try:
                    cur.execute(f"SELECT pg_total_relation_size('aico_core.{table_name}')")
                    size_bytes = cur.fetchone()[0]
                except Exception:
                    size_bytes = None
                
                tables.append(TableInfo(
                    name=table_name,
                    row_count=row_count,
                    columns=column_count,
                    size_bytes=size_bytes
                ))
        
        conn.close()
        
        return DatabaseDetailsResponse(
            database_type="postgresql",
            tables=tables
        )
    except Exception as e:
        logger.error(f"Failed to get PostgreSQL details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PostgreSQL details: {str(e)}"
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


async def get_schema_metadata() -> SchemaMetadata:
    """
    Get database schema metadata for autocomplete.
    Returns table names and their columns.
    """
    try:
        import psycopg2

        host, port, database, db_user, db_password = _resolve_postgres_connection_params()
        
        # Connect to PostgreSQL
        conn = await asyncio.to_thread(
            psycopg2.connect,
            host=host,
            port=port,
            database=database,
            user=db_user,
            password=db_password,
            connect_timeout=5
        )
        
        tables = []
        columns = {}
        
        with conn.cursor() as cur:
            # Get all user tables from aico_core schema
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_rows = cur.fetchall()
            
            for (table_name,) in table_rows:
                tables.append(table_name)
                
                # Get columns for this table from PostgreSQL information_schema
                try:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'aico_core' AND table_name = %s ORDER BY ordinal_position",
                        (table_name,)
                    )
                    col_rows = cur.fetchall()
                    columns[table_name] = [row[0] for row in col_rows]
                except Exception as e:
                    logger.warning(f"Failed to get columns for table {table_name}: {e}")
                    columns[table_name] = []
        
        conn.close()
        
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
            cleaned_pattern = pattern.replace("\\b", "").replace("\\s+", " ")
            return False, f"Forbidden operation detected: {cleaned_pattern}", False
    
    # Check for destructive patterns (require confirmation)
    is_destructive = False
    for pattern in DESTRUCTIVE_SQL_PATTERNS:
        if re.search(pattern, query_upper, re.IGNORECASE):
            is_destructive = True
            if not allow_destructive:
                return False, "Destructive operation detected. Enable 'Allow Modifications' to execute.", True
    
    # Validate it's a SELECT query if not destructive
    if not is_destructive and not query_upper.strip().startswith('SELECT'):
        # Allow SHOW queries for database inspection (PostgreSQL equivalent of PRAGMA)
        if not query_upper.strip().startswith('SHOW'):
            return False, "Only SELECT and SHOW queries are allowed in read-only mode", False
    
    return True, None, is_destructive


async def execute_sql_query(
    query: str,
    limit: int,
    uow,
    allow_destructive: bool = False
) -> QueryResult:
    """
    Execute a SQL query on PostgreSQL database.
    
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
        # Use regex to check for LIMIT as a word (not substring) to avoid false positives
        import re
        has_limit = bool(re.search(r'\bLIMIT\b', query_upper))
        if query_upper.startswith('SELECT') and not has_limit:
            query = f"{query.rstrip(';')} LIMIT {limit}"
        
        # Connect to PostgreSQL and execute query
        import psycopg2

        host, port, database, db_user, db_password = _resolve_postgres_connection_params()
        
        conn = await asyncio.to_thread(
            psycopg2.connect,
            host=host,
            port=port,
            database=database,
            user=db_user,
            password=db_password,
            connect_timeout=5
        )
        
        with conn.cursor() as cur:
            # Set search_path to aico_core schema so queries work without schema prefix
            cur.execute("SET search_path TO aico_core, public")
            cur.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cur.description] if cur.description else []
            
            # Fetch rows
            rows = cur.fetchall()
            
            # Convert rows to list of lists
            row_data = [list(row) for row in rows]
        
        conn.close()
        
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
        
        if database_name == "PostgreSQL":
            # For PostgreSQL, size will be queried from the database itself
            # This is a placeholder for trend data
            current_size = 0  # Will be replaced with actual PostgreSQL size query
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
        
        # Generate 7 days of simulated historical data
        # In production, replace with actual historical metrics
        now = datetime.now(UTC)
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
