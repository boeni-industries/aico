"""Database Remediation Tools

Implements remediation tools for database maintenance including vacuum, archive,
delete, and compaction operations across PostgreSQL, ChromaDB, InfluxDB, and LMDB.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime, UTC, timedelta

from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.tools.database_remediation")


# ============================================================================
# PostgreSQL Remediation Tools
# ============================================================================

async def tool_db_postgres_get_table_sizes(session_factory: Any) -> Dict[str, Any]:
    """Get table and index sizes for PostgreSQL database.
    
    Returns size information for all tables to help identify disk pressure.
    
    Returns:
        Dict with ok, data (table sizes), and error fields
    """
    from aico.data.uow import UnitOfWork
    from datetime import datetime, UTC
    
    start = datetime.now(UTC)
    
    try:
        async with UnitOfWork(session_factory) as uow:
            # Query to get table sizes including indexes
            query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                    pg_total_relation_size(schemaname||'.'||tablename) AS total_bytes,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
                    pg_relation_size(schemaname||'.'||tablename) AS table_bytes,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                                   pg_relation_size(schemaname||'.'||tablename)) AS index_size,
                    (pg_total_relation_size(schemaname||'.'||tablename) - 
                     pg_relation_size(schemaname||'.'||tablename)) AS index_bytes
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 50;
            """
            
            result = await uow.session.execute(query)
            rows = result.fetchall()
            
            tables = []
            total_size_bytes = 0
            
            for row in rows:
                table_info = {
                    "schema": row[0],
                    "table": row[1],
                    "total_size": row[2],
                    "total_bytes": row[3],
                    "table_size": row[4],
                    "table_bytes": row[5],
                    "index_size": row[6],
                    "index_bytes": row[7],
                }
                tables.append(table_info)
                total_size_bytes += row[3]
            
            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error_message": None,
                    "details": {
                        "tables": tables,
                        "table_count": len(tables),
                        "total_size_bytes": total_size_bytes,
                        "total_size": _format_bytes(total_size_bytes),
                    }
                },
                "error": None,
            }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] Failed to get table sizes: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "table_sizes_failed", "message": str(exc)},
        }


async def tool_db_postgres_vacuum_analyze(
    session_factory: Any,
    table_name: Optional[str] = None,
    full: bool = False,
    analyze: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Run VACUUM and optionally ANALYZE on PostgreSQL tables.
    
    Args:
        session_factory: SQLAlchemy session factory
        table_name: Specific table to vacuum (None = all tables)
        full: Whether to run VACUUM FULL (more thorough but locks table)
        analyze: Whether to run ANALYZE after vacuum
        dry_run: If True, only report what would be done
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.uow import UnitOfWork
    from sqlalchemy import text
    
    start = datetime.now(UTC)
    
    try:
        if dry_run:
            # Dry run - just report what would be done
            action = "VACUUM FULL" if full else "VACUUM"
            if analyze:
                action += " ANALYZE"
            
            target = f"table '{table_name}'" if table_name else "all tables"
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": 0,
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "action": action,
                        "target": target,
                        "message": f"Would run: {action} on {target}",
                    }
                },
                "error": None,
            }
        
        # Actual execution
        # VACUUM must run outside transaction - use connection with AUTOCOMMIT
        async with session_factory() as session:
            # Get the raw DBAPI connection
            connection = await session.connection()
            dbapi_conn = await connection.get_raw_connection()
            
            # Unwrap to get actual asyncpg connection from AsyncAdapt wrapper
            if hasattr(dbapi_conn, 'driver_connection'):
                asyncpg_conn = dbapi_conn.driver_connection
            elif hasattr(dbapi_conn, '_connection'):
                asyncpg_conn = dbapi_conn._connection
            else:
                asyncpg_conn = dbapi_conn
            
            # Build VACUUM command with VERBOSE to get detailed output
            vacuum_cmd = "VACUUM"
            if full:
                vacuum_cmd += " FULL"
            vacuum_cmd += " VERBOSE"  # Add VERBOSE to get detailed output
            if analyze:
                vacuum_cmd += " ANALYZE"
            if table_name:
                vacuum_cmd += f" {table_name}"
            
            # Collect notices/messages from VACUUM execution
            notices = []
            
            def notice_receiver(connection, message):
                """Callback for asyncpg log messages - receives (connection, message) tuple"""
                notices.append(str(message))
            
            # Add log listener to capture PostgreSQL NOTICE messages
            asyncpg_conn.add_log_listener(notice_receiver)
            
            try:
                # Execute VACUUM directly on asyncpg connection
                # asyncpg connections are not in a transaction by default
                await asyncpg_conn.execute(vacuum_cmd)
            finally:
                # Remove log listener
                asyncpg_conn.remove_log_listener(notice_receiver)
            
            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            
            # Format the output with VACUUM results
            vacuum_output = "\n".join(notices) if notices else f"VACUUM completed successfully on {table_name or 'all tables'}"
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error_message": None,
                    "details": {
                        "dry_run": False,
                        "action": vacuum_cmd,
                        "table": table_name or "all",
                        "full": full,
                        "analyze": analyze,
                        "vacuum_output": vacuum_output,
                        "notices_count": len(notices),
                    }
                },
                "error": None,
            }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] VACUUM failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "vacuum_failed", "message": str(exc)},
        }


async def tool_db_postgres_archive_rows(
    session_factory: Any,
    table_name: str,
    archive_table_name: str,
    where_clause: str,
    max_rows: int = 1000,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Archive old rows from a table to an archive table.
    
    Args:
        session_factory: SQLAlchemy session factory
        table_name: Source table name
        archive_table_name: Destination archive table name
        where_clause: SQL WHERE clause to select rows (e.g., "created_at < NOW() - INTERVAL '90 days'")
        max_rows: Maximum number of rows to archive in one operation
        dry_run: If True, only count rows that would be archived
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.uow import UnitOfWork
    from sqlalchemy import text
    
    start = datetime.now(UTC)
    
    try:
        async with UnitOfWork(session_factory) as uow:
            # First, count rows that match
            count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            result = await uow.session.execute(text(count_query))
            total_matching = result.scalar()
            
            rows_to_archive = min(total_matching, max_rows)
            
            if dry_run:
                return {
                    "ok": True,
                    "data": {
                        "status": "ok",
                        "latency_ms": int((datetime.now(UTC) - start).total_seconds() * 1000),
                        "error_message": None,
                        "details": {
                            "dry_run": True,
                            "table": table_name,
                            "archive_table": archive_table_name,
                            "total_matching": total_matching,
                            "would_archive": rows_to_archive,
                            "where_clause": where_clause,
                        }
                    },
                    "error": None,
                }
            
            # Create archive table if it doesn't exist (same structure as source)
            create_archive_query = f"""
                CREATE TABLE IF NOT EXISTS {archive_table_name} 
                (LIKE {table_name} INCLUDING ALL)
            """
            await uow.session.execute(text(create_archive_query))
            
            # Copy rows to archive table
            archive_query = f"""
                INSERT INTO {archive_table_name}
                SELECT * FROM {table_name}
                WHERE {where_clause}
                LIMIT {max_rows}
            """
            result = await uow.session.execute(text(archive_query))
            archived_count = result.rowcount
            
            # Delete archived rows from source table
            delete_query = f"""
                DELETE FROM {table_name}
                WHERE ctid IN (
                    SELECT ctid FROM {table_name}
                    WHERE {where_clause}
                    LIMIT {max_rows}
                )
            """
            result = await uow.session.execute(text(delete_query))
            deleted_count = result.rowcount
            
            await uow.commit()
            
            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error_message": None,
                    "details": {
                        "dry_run": False,
                        "table": table_name,
                        "archive_table": archive_table_name,
                        "archived_count": archived_count,
                        "deleted_count": deleted_count,
                        "remaining": total_matching - deleted_count,
                    }
                },
                "error": None,
            }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] Archive failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "archive_failed", "message": str(exc)},
        }


async def tool_db_postgres_delete_rows(
    session_factory: Any,
    table_name: str,
    where_clause: str,
    max_rows: int = 1000,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Delete rows from a PostgreSQL table with safety checks.
    
    Args:
        session_factory: SQLAlchemy session factory
        table_name: Table name
        where_clause: SQL WHERE clause to select rows
        max_rows: Maximum number of rows to delete in one operation
        dry_run: If True, only count rows that would be deleted
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.uow import UnitOfWork
    from sqlalchemy import text
    
    start = datetime.now(UTC)
    
    try:
        async with UnitOfWork(session_factory) as uow:
            # Count rows that match
            count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            result = await uow.session.execute(text(count_query))
            total_matching = result.scalar()
            
            rows_to_delete = min(total_matching, max_rows)
            
            if dry_run:
                return {
                    "ok": True,
                    "data": {
                        "status": "ok",
                        "latency_ms": int((datetime.now(UTC) - start).total_seconds() * 1000),
                        "error_message": None,
                        "details": {
                            "dry_run": True,
                            "table": table_name,
                            "total_matching": total_matching,
                            "would_delete": rows_to_delete,
                            "where_clause": where_clause,
                        }
                    },
                    "error": None,
                }
            
            # Delete rows with limit
            delete_query = f"""
                DELETE FROM {table_name}
                WHERE ctid IN (
                    SELECT ctid FROM {table_name}
                    WHERE {where_clause}
                    LIMIT {max_rows}
                )
            """
            result = await uow.session.execute(text(delete_query))
            deleted_count = result.rowcount
            
            await uow.commit()
            
            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error_message": None,
                    "details": {
                        "dry_run": False,
                        "table": table_name,
                        "deleted_count": deleted_count,
                        "remaining": total_matching - deleted_count,
                    }
                },
                "error": None,
            }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] Delete failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "delete_failed", "message": str(exc)},
        }


# ============================================================================
# ChromaDB Remediation Tools
# ============================================================================

async def tool_db_chroma_get_collection_stats() -> Dict[str, Any]:
    """Get statistics for all ChromaDB collections.
    
    Returns:
        Dict with ok, data (collection stats), and error fields
    """
    from aico.data.chroma.connection import get_chroma_client
    
    start = datetime.now(UTC)
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        stats = []
        total_vectors = 0
        
        for collection in collections:
            count = collection.count()
            total_vectors += count
            
            stats.append({
                "name": collection.name,
                "count": count,
                "metadata": collection.metadata or {},
            })
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "collections": stats,
                    "collection_count": len(stats),
                    "total_vectors": total_vectors,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] ChromaDB stats failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "chroma_stats_failed", "message": str(exc)},
        }


async def tool_db_chroma_delete_vectors(
    collection_name: str,
    where_filter: Optional[Dict[str, Any]] = None,
    max_count: int = 1000,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Delete vectors from a ChromaDB collection.
    
    Args:
        collection_name: Name of the collection
        where_filter: Metadata filter for selecting vectors to delete
        max_count: Maximum number of vectors to delete
        dry_run: If True, only count vectors that would be deleted
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.chroma.connection import get_chroma_client
    
    start = datetime.now(UTC)
    
    try:
        client = get_chroma_client()
        collection = client.get_collection(name=collection_name)
        
        # Query to get IDs of vectors to delete
        query_params = {"limit": max_count}
        if where_filter:
            query_params["where"] = where_filter
        
        results = collection.get(**query_params)
        ids_to_delete = results.get("ids", [])
        count_to_delete = len(ids_to_delete)
        
        if dry_run:
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": int((datetime.now(UTC) - start).total_seconds() * 1000),
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "collection": collection_name,
                        "would_delete": count_to_delete,
                        "filter": where_filter,
                    }
                },
                "error": None,
            }
        
        # Delete vectors
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": False,
                    "collection": collection_name,
                    "deleted_count": count_to_delete,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] ChromaDB delete failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "chroma_delete_failed", "message": str(exc)},
        }


async def tool_db_chroma_compact_store() -> Dict[str, Any]:
    """Trigger compaction for ChromaDB (if supported by backend).
    
    Note: ChromaDB compaction is typically automatic. This is a placeholder
    for future explicit compaction support.
    
    Returns:
        Dict with ok, data, and error fields
    """
    start = datetime.now(UTC)
    
    try:
        # ChromaDB handles compaction automatically in most cases
        # This is a placeholder for explicit compaction if needed
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "message": "ChromaDB compaction is automatic",
                    "action": "none_required",
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] ChromaDB compact failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "chroma_compact_failed", "message": str(exc)},
        }


# ============================================================================
# InfluxDB Remediation Tools
# ============================================================================

async def tool_db_influx_list_retention_policies() -> Dict[str, Any]:
    """List retention policies for InfluxDB buckets.
    
    Returns:
        Dict with ok, data (retention policies), and error fields
    """
    from aico.data.influx.connection import InfluxDBConnection
    
    start = datetime.now(UTC)
    
    try:
        conn = InfluxDBConnection()
        
        if not conn.client:
            return {
                "ok": False,
                "data": {
                    "status": "error",
                    "latency_ms": 0,
                    "error_message": "InfluxDB client not available",
                    "details": {},
                },
                "error": {"code": "client_unavailable", "message": "InfluxDB client not available"},
            }
        
        buckets_api = conn.client.buckets_api()
        buckets = buckets_api.find_buckets()
        
        policies = []
        
        if buckets and buckets.buckets:
            for bucket in buckets.buckets:
                # Skip system buckets
                if bucket.name.startswith('_'):
                    continue
                
                retention_rules = bucket.retention_rules or []
                retention_seconds = retention_rules[0].every_seconds if retention_rules else None
                
                policies.append({
                    "bucket": bucket.name,
                    "retention_seconds": retention_seconds,
                    "retention_days": retention_seconds // 86400 if retention_seconds else None,
                    "retention_human": _format_duration(retention_seconds) if retention_seconds else "infinite",
                })
        
        conn.close()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "policies": policies,
                    "bucket_count": len(policies),
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB list retention failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_list_retention_failed", "message": str(exc)},
        }


async def tool_db_influx_apply_retention_policy(
    bucket_name: str,
    retention_days: int,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Apply or update retention policy for an InfluxDB bucket.
    
    Args:
        bucket_name: Name of the bucket
        retention_days: Retention period in days (0 = infinite)
        dry_run: If True, only report what would be done
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.influx.connection import InfluxDBConnection
    
    start = datetime.now(UTC)
    
    try:
        if dry_run:
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": 0,
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "bucket": bucket_name,
                        "retention_days": retention_days,
                        "message": f"Would set retention to {retention_days} days for bucket '{bucket_name}'",
                    }
                },
                "error": None,
            }
        
        conn = InfluxDBConnection()
        
        if not conn.client:
            return {
                "ok": False,
                "data": {
                    "status": "error",
                    "latency_ms": 0,
                    "error_message": "InfluxDB client not available",
                    "details": {},
                },
                "error": {"code": "client_unavailable", "message": "InfluxDB client not available"},
            }
        
        buckets_api = conn.client.buckets_api()
        
        # Find the bucket
        bucket = buckets_api.find_bucket_by_name(bucket_name)
        if not bucket:
            conn.close()
            return {
                "ok": False,
                "data": {
                    "status": "error",
                    "latency_ms": 0,
                    "error_message": f"Bucket '{bucket_name}' not found",
                    "details": {},
                },
                "error": {"code": "bucket_not_found", "message": f"Bucket '{bucket_name}' not found"},
            }
        
        # Update retention policy
        from influxdb_client.domain.retention_rule import RetentionRule
        
        retention_seconds = retention_days * 86400 if retention_days > 0 else 0
        bucket.retention_rules = [RetentionRule(type="expire", every_seconds=retention_seconds)]
        
        buckets_api.update_bucket(bucket=bucket)
        
        conn.close()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": False,
                    "bucket": bucket_name,
                    "retention_days": retention_days,
                    "retention_seconds": retention_seconds,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB apply retention failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_apply_retention_failed", "message": str(exc)},
        }


async def tool_db_influx_drop_measurement(
    bucket_name: str,
    measurement_name: str,
    start_time: Optional[str] = None,
    stop_time: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Drop (delete) a measurement or time range from InfluxDB.
    
    Args:
        bucket_name: Name of the bucket
        measurement_name: Name of the measurement to drop
        start_time: Start time for deletion (RFC3339 format, e.g., "2024-01-01T00:00:00Z")
        stop_time: Stop time for deletion (RFC3339 format)
        dry_run: If True, only report what would be done
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.influx.connection import InfluxDBConnection
    
    start = datetime.now(UTC)
    
    try:
        if dry_run:
            time_range = ""
            if start_time and stop_time:
                time_range = f" between {start_time} and {stop_time}"
            elif start_time:
                time_range = f" from {start_time} onwards"
            
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": 0,
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "bucket": bucket_name,
                        "measurement": measurement_name,
                        "time_range": time_range,
                        "message": f"Would drop measurement '{measurement_name}'{time_range} from bucket '{bucket_name}'",
                    }
                },
                "error": None,
            }
        
        conn = InfluxDBConnection()
        
        if not conn.client:
            return {
                "ok": False,
                "data": {
                    "status": "error",
                    "latency_ms": 0,
                    "error_message": "InfluxDB client not available",
                    "details": {},
                },
                "error": {"code": "client_unavailable", "message": "InfluxDB client not available"},
            }
        
        delete_api = conn.client.delete_api()
        
        # Build predicate
        predicate = f'_measurement="{measurement_name}"'
        
        # Use provided times or default to all time
        start_delete = start_time or "1970-01-01T00:00:00Z"
        stop_delete = stop_time or datetime.now(UTC).isoformat()
        
        # Execute deletion
        delete_api.delete(
            start=start_delete,
            stop=stop_delete,
            predicate=predicate,
            bucket=bucket_name,
            org=conn.org,
        )
        
        conn.close()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": False,
                    "bucket": bucket_name,
                    "measurement": measurement_name,
                    "start_time": start_delete,
                    "stop_time": stop_delete,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB drop measurement failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_drop_measurement_failed", "message": str(exc)},
        }


# ============================================================================
# LMDB Remediation Tools
# ============================================================================

async def tool_db_lmdb_check_map_size() -> Dict[str, Any]:
    """Check LMDB map size usage.
    
    Returns:
        Dict with ok, data (map size info), and error fields
    """
    from aico.data.lmdb.connection import get_lmdb_env
    from pathlib import Path
    
    start = datetime.now(UTC)
    
    try:
        env = get_lmdb_env()
        
        # Get environment info
        info = env.info()
        stat = env.stat()
        
        map_size = info['map_size']
        
        # Get actual file size
        db_path = Path(env.path())
        actual_size = db_path.stat().st_size if db_path.exists() else 0
        
        usage_percent = (actual_size / map_size * 100) if map_size > 0 else 0
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "map_size": map_size,
                    "map_size_human": _format_bytes(map_size),
                    "actual_size": actual_size,
                    "actual_size_human": _format_bytes(actual_size),
                    "usage_percent": round(usage_percent, 2),
                    "entries": stat['entries'],
                    "pages_used": stat['psize'] * stat['depth'],
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] LMDB map size check failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "lmdb_map_size_failed", "message": str(exc)},
        }


async def tool_db_lmdb_compact(dry_run: bool = True) -> Dict[str, Any]:
    """Compact LMDB database by copying to a new file.
    
    Args:
        dry_run: If True, only report what would be done
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.lmdb.connection import get_lmdb_env
    from pathlib import Path
    import shutil
    
    start = datetime.now(UTC)
    
    try:
        env = get_lmdb_env()
        db_path = Path(env.path())
        
        # Get current size
        current_size = db_path.stat().st_size if db_path.exists() else 0
        
        if dry_run:
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": 0,
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "current_size": current_size,
                        "current_size_human": _format_bytes(current_size),
                        "message": "Would compact LMDB database (requires restart)",
                    }
                },
                "error": None,
            }
        
        # Compaction requires copying to a new file
        # This is a simplified version - production would need proper backup/restore
        compact_path = db_path.parent / f"{db_path.name}.compact"
        
        # Copy environment to compact file
        env.copy(str(compact_path), compact=True)
        
        # Get new size
        new_size = compact_path.stat().st_size if compact_path.exists() else 0
        saved_bytes = current_size - new_size
        
        # Note: In production, would need to:
        # 1. Stop all writes
        # 2. Replace old file with compact file
        # 3. Restart LMDB environment
        # For now, just report the results
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": False,
                    "current_size": current_size,
                    "new_size": new_size,
                    "saved_bytes": saved_bytes,
                    "saved_human": _format_bytes(saved_bytes),
                    "compact_file": str(compact_path),
                    "message": "Compact file created - manual replacement required",
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] LMDB compact failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "lmdb_compact_failed", "message": str(exc)},
        }


async def tool_db_lmdb_delete_keys_by_prefix(
    db_name: str,
    prefix: str,
    max_keys: int = 1000,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Delete keys from LMDB by prefix.
    
    Args:
        db_name: Name of the sub-database
        prefix: Key prefix to match
        max_keys: Maximum number of keys to delete
        dry_run: If True, only count keys that would be deleted
    
    Returns:
        Dict with ok, data, and error fields
    """
    from aico.data.lmdb.connection import get_lmdb_env
    
    start = datetime.now(UTC)
    
    try:
        env = get_lmdb_env()
        
        # Open sub-database
        db = env.open_db(db_name.encode() if db_name else None)
        
        # Count matching keys
        matching_keys = []
        with env.begin(db=db) as txn:
            cursor = txn.cursor()
            prefix_bytes = prefix.encode()
            
            # Seek to first key with prefix
            if cursor.set_range(prefix_bytes):
                for key, _ in cursor:
                    if not key.startswith(prefix_bytes):
                        break
                    matching_keys.append(key)
                    if len(matching_keys) >= max_keys:
                        break
        
        count_to_delete = len(matching_keys)
        
        if dry_run:
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "latency_ms": int((datetime.now(UTC) - start).total_seconds() * 1000),
                    "error_message": None,
                    "details": {
                        "dry_run": True,
                        "db_name": db_name,
                        "prefix": prefix,
                        "would_delete": count_to_delete,
                    }
                },
                "error": None,
            }
        
        # Delete keys
        with env.begin(db=db, write=True) as txn:
            for key in matching_keys:
                txn.delete(key)
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": False,
                    "db_name": db_name,
                    "prefix": prefix,
                    "deleted_count": count_to_delete,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] LMDB delete by prefix failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "lmdb_delete_failed", "message": str(exc)},
        }


# ============================================================================
# InfluxDB Remediation Tools
# ============================================================================

async def tool_db_influx_get_measurements(
    config: Any,
    measurement_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Get list of measurements in InfluxDB bucket with size estimates.
    
    Args:
        config: Configuration object
        measurement_filter: Optional regex filter for measurement names
    
    Returns:
        Dict with ok, data (measurements list), and error fields
    """
    from influxdb_client import InfluxDBClient
    from aico.security import AICOKeyManager
    
    start = datetime.now(UTC)
    
    try:
        # Get InfluxDB connection details - FAIL LOUD if missing
        url = config.get("core.database.influx.url")
        if not url:
            raise ValueError("Missing required config: core.database.influx.url")
        
        org = config.get("core.database.influx.org")
        if not org:
            raise ValueError("Missing required config: core.database.influx.org")
        
        bucket = config.get("core.database.influx.bucket")
        if not bucket:
            raise ValueError("Missing required config: core.database.influx.bucket")
        
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token")
        
        # Connect to InfluxDB
        with InfluxDBClient(url=url, token=token, org=org) as client:
            query_api = client.query_api()
            
            # Query to get measurements with cardinality estimates
            filter_clause = f'|> filter(fn: (r) => r._measurement =~ /{measurement_filter}/)' if measurement_filter else ''
            
            query = f'''
                import "influxdata/influxdb/schema"
                schema.measurements(bucket: "{bucket}")
                {filter_clause}
            '''
            
            tables = query_api.query(query)
            
            measurements = []
            for table in tables:
                for record in table.records:
                    measurement_name = record.get_value()
                    
                    # Get approximate point count for this measurement
                    count_query = f'''
                        from(bucket: "{bucket}")
                        |> range(start: -30d)
                        |> filter(fn: (r) => r._measurement == "{measurement_name}")
                        |> count()
                    '''
                    
                    try:
                        count_tables = query_api.query(count_query)
                        total_points = sum(
                            record.get_value()
                            for table in count_tables
                            for record in table.records
                        )
                    except Exception:
                        total_points = 0
                    
                    measurements.append({
                        "name": measurement_name,
                        "estimated_points": total_points,
                    })
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "bucket": bucket,
                    "measurements": measurements,
                    "total_measurements": len(measurements),
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB get measurements failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_query_failed", "message": str(exc)},
        }


async def tool_db_influx_apply_retention(
    config: Any,
    measurement: Optional[str] = None,
    retention_days: Optional[int] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Apply retention policy to delete old data from InfluxDB.
    
    Deletes data older than the specified retention period. Uses configuration
    defaults if retention_days not specified.
    
    Args:
        config: Configuration object
        measurement: Specific measurement to clean (None = use config policies)
        retention_days: Days to retain (overrides config)
        dry_run: If True, only report what would be deleted
    
    Returns:
        Dict with ok, data (deletion summary), and error fields
    """
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS
    from aico.security import AICOKeyManager
    
    print(f"\n{'='*80}")
    print(f"[INFLUX TOOL] tool_db_influx_apply_retention called")
    print(f"{'='*80}")
    print(f"measurement: {measurement}")
    print(f"retention_days: {retention_days}")
    print(f"dry_run: {dry_run} (type: {type(dry_run).__name__})")
    print(f"{'='*80}\n")
    
    start = datetime.now(UTC)
    
    try:
        # Get InfluxDB connection details - FAIL LOUD if missing
        url = config.get("core.database.influx.url")
        if not url:
            raise ValueError("Missing required config: core.database.influx.url")
        
        org = config.get("core.database.influx.org")
        if not org:
            raise ValueError("Missing required config: core.database.influx.org")
        
        bucket = config.get("core.database.influx.bucket")
        if not bucket:
            raise ValueError("Missing required config: core.database.influx.bucket")
        
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token")
        
        # Determine retention policy - FAIL LOUD if config missing
        if retention_days is None:
            if measurement:
                # Check for measurement-specific retention
                retention_days = config.get(
                    f"core.database.influx.retention.measurements.{measurement}.retention_days"
                )
                if retention_days is None:
                    # Fall back to default
                    retention_days = config.get("core.database.influx.retention.default_days")
                    if retention_days is None:
                        raise ValueError(
                            f"Missing retention config for measurement '{measurement}' and no default found. "
                            f"Expected: core.database.influx.retention.measurements.{measurement}.retention_days "
                            f"or core.database.influx.retention.default_days"
                        )
            else:
                # Use default retention - MUST be configured
                retention_days = config.get("core.database.influx.retention.default_days")
                if retention_days is None:
                    raise ValueError(
                        "Missing required config: core.database.influx.retention.default_days. "
                        "Cannot apply retention without configured policy."
                    )
        
        # Calculate cutoff time
        cutoff_time = datetime.now(UTC) - timedelta(days=retention_days)
        
        # Connect to InfluxDB
        with InfluxDBClient(url=url, token=token, org=org) as client:
            delete_api = client.delete_api()
            query_api = client.query_api()
            
            # Determine which measurements to process
            if measurement:
                measurements_to_process = [measurement]
            else:
                # Get all measurements with configured retention policies - FAIL LOUD if missing
                measurements_config = config.get("core.database.influx.retention.measurements")
                if not measurements_config:
                    raise ValueError(
                        "Missing required config: core.database.influx.retention.measurements. "
                        "Cannot apply retention policies without configured measurements."
                    )
                measurements_to_process = list(measurements_config.keys())
                if not measurements_to_process:
                    raise ValueError(
                        "No measurements configured in core.database.influx.retention.measurements. "
                        "Add at least one measurement with retention_days setting."
                    )
            
            deleted_summary = []
            
            for meas in measurements_to_process:
                # Get measurement-specific retention if not overridden
                if retention_days is None or not measurement:
                    meas_retention = config.get(
                        f"core.database.influx.retention.measurements.{meas}.retention_days"
                    )
                    if meas_retention is None:
                        # Fall back to default
                        meas_retention = config.get("core.database.influx.retention.default_days")
                        if meas_retention is None:
                            logger.warning(
                                f"[TOOL_DB_REMEDIATION] No retention configured for '{meas}', skipping"
                            )
                            continue
                    meas_cutoff = datetime.now(UTC) - timedelta(days=meas_retention)
                else:
                    meas_retention = retention_days
                    meas_cutoff = cutoff_time
                
                # Count points to be deleted (dry-run preview)
                count_query = f'''
                    from(bucket: "{bucket}")
                    |> range(start: -365d, stop: {meas_cutoff.isoformat()})
                    |> filter(fn: (r) => r._measurement == "{meas}")
                    |> count()
                '''
                
                try:
                    count_tables = query_api.query(count_query)
                    points_to_delete = sum(
                        record.get_value()
                        for table in count_tables
                        for record in table.records
                    )
                except Exception:
                    points_to_delete = 0
                
                if not dry_run and points_to_delete > 0:
                    # Execute deletion
                    predicate = f'_measurement="{meas}"'
                    delete_api.delete(
                        start="1970-01-01T00:00:00Z",
                        stop=meas_cutoff.isoformat(),
                        predicate=predicate,
                        bucket=bucket,
                        org=org
                    )
                
                deleted_summary.append({
                    "measurement": meas,
                    "retention_days": meas_retention,
                    "cutoff_time": meas_cutoff.isoformat(),
                    "points_deleted": points_to_delete if not dry_run else 0,
                    "points_to_delete": points_to_delete if dry_run else 0,
                })
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        total_deleted = sum(item["points_deleted"] for item in deleted_summary)
        total_to_delete = sum(item["points_to_delete"] for item in deleted_summary)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": dry_run,
                    "bucket": bucket,
                    "measurements_processed": len(deleted_summary),
                    "total_points_deleted": total_deleted,
                    "total_points_to_delete": total_to_delete,
                    "summary": deleted_summary,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB retention apply failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_delete_failed", "message": str(exc)},
        }


async def tool_db_influx_drop_measurement(
    config: Any,
    measurement: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Drop an entire measurement from InfluxDB.
    
    WARNING: This deletes ALL data for the specified measurement.
    
    Args:
        config: Configuration object
        measurement: Measurement name to drop
        dry_run: If True, only report what would be deleted
    
    Returns:
        Dict with ok, data (deletion summary), and error fields
    """
    from influxdb_client import InfluxDBClient
    from aico.security import AICOKeyManager
    
    start = datetime.now(UTC)
    
    try:
        # Get InfluxDB connection details - FAIL LOUD if missing
        url = config.get("core.database.influx.url")
        if not url:
            raise ValueError("Missing required config: core.database.influx.url")
        
        org = config.get("core.database.influx.org")
        if not org:
            raise ValueError("Missing required config: core.database.influx.org")
        
        bucket = config.get("core.database.influx.bucket")
        if not bucket:
            raise ValueError("Missing required config: core.database.influx.bucket")
        
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token")
        
        # Connect to InfluxDB
        with InfluxDBClient(url=url, token=token, org=org) as client:
            delete_api = client.delete_api()
            query_api = client.query_api()
            
            # Count total points in measurement
            count_query = f'''
                from(bucket: "{bucket}")
                |> range(start: -365d)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> count()
            '''
            
            try:
                count_tables = query_api.query(count_query)
                total_points = sum(
                    record.get_value()
                    for table in count_tables
                    for record in table.records
                )
            except Exception:
                total_points = 0
            
            if not dry_run and total_points > 0:
                # Drop the entire measurement
                predicate = f'_measurement="{measurement}"'
                delete_api.delete(
                    start="1970-01-01T00:00:00Z",
                    stop=datetime.now(UTC).isoformat(),
                    predicate=predicate,
                    bucket=bucket,
                    org=org
                )
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "dry_run": dry_run,
                    "bucket": bucket,
                    "measurement": measurement,
                    "points_deleted": total_points if not dry_run else 0,
                    "points_to_delete": total_points if dry_run else 0,
                }
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_REMEDIATION] InfluxDB drop measurement failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_drop_failed", "message": str(exc)},
        }


# ============================================================================
# Helper Functions
# ============================================================================

def _format_bytes(bytes_val: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f}PB"


def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"
