"""Database Health Monitoring Tools

Atomic tools for retrieving detailed health metrics from databases.
Separate from connectivity tools which only do ping checks.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.data.lmdb import get_lmdb_path, initialize_lmdb_env
from aico.ai.agency.tools.registry import ToolDefinition, get_tool_registry


logger = get_logger("aico.ai.agency.tools.database_health")


async def tool_db_postgres_health() -> Dict[str, Any]:
    """Get PostgreSQL database health metrics."""
    from aico.data.postgres.connection import get_session_factory
    from sqlalchemy import text
    
    start = datetime.now(UTC)
    try:
        session_factory = await get_session_factory()
        
        async with session_factory() as session:
            # Query database size
            result = await session.execute(
                text("SELECT pg_database_size(current_database()) as size")
            )
            row = result.fetchone()
            db_size_bytes = row[0] if row else 0
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
            
            # Query connection count
            result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )
            row = result.fetchone()
            connections = row[0] if row else 0
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "database_size_mb": db_size_mb,
                    "active_connections": connections
                },
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_HEALTH] PostgreSQL health check failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "postgres_health_failed", "message": str(exc)},
        }


async def tool_db_chroma_health() -> Dict[str, Any]:
    """Get ChromaDB health metrics including collection count."""
    start = datetime.now(UTC)
    try:
        import chromadb
        from chromadb.config import Settings
        
        chroma_path = AICOPaths.get_semantic_memory_path()
        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        
        # Get collection count and details
        collections = client.list_collections()
        collection_count = len(collections)
        
        # Get total document count across all collections
        total_documents = 0
        for collection in collections:
            try:
                count = collection.count()
                total_documents += count
            except Exception:
                pass
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "collections": collection_count,
                    "total_documents": total_documents
                },
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_HEALTH] ChromaDB health check failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "chroma_health_failed", "message": str(exc)},
        }


async def tool_db_influx_health() -> Dict[str, Any]:
    """Get InfluxDB health metrics including metric count."""
    from aico.data.influx.connection import InfluxDBConnection
    
    start = datetime.now(UTC)
    try:
        conn = InfluxDBConnection()
        
        # Count total metrics across all user buckets
        total_metrics = 0
        if conn.client:
            try:
                buckets_api = conn.client.buckets_api()
                buckets = buckets_api.find_buckets()
                if buckets and buckets.buckets:
                    # Filter out system buckets (those starting with underscore)
                    user_buckets = [b for b in buckets.buckets if not b.name.startswith('_')]
                    
                    # Query each bucket for metric count
                    query_api = conn.client.query_api()
                    for bucket in user_buckets:
                        try:
                            # Query to get distinct measurements (metrics) in bucket
                            flux_query = f'''
                                import "influxdata/influxdb/schema"
                                schema.measurements(bucket: "{bucket.name}")
                            '''
                            result = query_api.query(flux_query, org=conn.org)
                            # Count the number of measurements returned
                            for table in result:
                                total_metrics += len(table.records)
                        except Exception as e:
                            logger.debug("[TOOL_DB_HEALTH] Could not query bucket %s: %s", bucket.name, e)
            except Exception as e:
                logger.warning("[TOOL_DB_HEALTH] Could not retrieve metric count: %s", e)
        
        conn.close()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "measurements": total_metrics
                },
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_HEALTH] InfluxDB health check failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "influx_health_failed", "message": str(exc)},
        }


async def tool_db_lmdb_health() -> Dict[str, Any]:
    """Get LMDB health metrics including entry count and size."""
    start = datetime.now(UTC)
    try:
        import lmdb
        
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        db_path = get_lmdb_path(config)
        initialize_lmdb_env(config)
        
        # Get named databases from config
        memory_config = config.get("core.memory.working", {})
        named_dbs = memory_config.get("named_databases", [])
        
        # Open with enough max_dbs for all named databases
        env = lmdb.open(str(db_path), max_dbs=len(named_dbs) + 1, readonly=True)
        
        # Count entries across all databases
        total_entries = 0
        
        # Count main database
        with env.begin() as txn:
            stat = txn.stat()
            total_entries += stat['entries']
        
        # Count each named database
        for db_name in named_dbs:
            try:
                with env.begin() as txn:
                    db = env.open_db(db_name.encode('utf-8'), txn=txn)
                    stat = txn.stat(db)
                    total_entries += stat['entries']
            except Exception as e:
                logger.debug("[TOOL_DB_HEALTH] Could not read named DB '%s': %s", db_name, e)
        
        info = env.info()
        map_size_mb = round(info['map_size'] / (1024 * 1024), 2)
        
        env.close()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "entries": total_entries,
                    "map_size_mb": map_size_mb
                },
            },
            "error": None,
        }
    
    except Exception as exc:
        logger.error("[TOOL_DB_HEALTH] LMDB health check failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {"code": "lmdb_health_failed", "message": str(exc)},
        }


def _register_database_health_tools():
    """Register database health monitoring tools."""
    registry = get_tool_registry()
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.postgres.health",
            name="PostgreSQL Health Check",
            description="Get PostgreSQL database health metrics (size, connections).",
            domain="database",
            backend="postgres",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_db_postgres_health,
        )
    )
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.chroma.health",
            name="ChromaDB Health Check",
            description="Get ChromaDB health metrics (collections, documents).",
            domain="database",
            backend="chroma",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_db_chroma_health,
        )
    )
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.influx.health",
            name="InfluxDB Health Check",
            description="Get InfluxDB health metrics (buckets).",
            domain="database",
            backend="influx",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_db_influx_health,
        )
    )
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.lmdb.health",
            name="LMDB Health Check",
            description="Get LMDB health metrics (entries, size).",
            domain="database",
            backend="lmdb",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_db_lmdb_health,
        )
    )


# Register tools at import time
_register_database_health_tools()
