"""
Operations API Router

REST API endpoints for operations monitoring, database metrics, and active sessions.
"""

import os
import time
import shutil
import uuid
import asyncio
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from datetime import datetime, timedelta

from aico.core.logging import get_logger
from aico.core.version import get_backend_version, get_modelservice_version
from backend.api.operations.schemas import (
    DatabaseStatsResponse, DatabaseMetrics,
    DatabaseDetailsResponse, TableInfo, CollectionInfo, LMDBDatabaseInfo,
    QueryRequest, QueryResult, SchemaMetadata,
    BackupInfo, BackupResponse, BackupHistoryResponse, RestoreRequest, RestoreResponse,
    StorageTrendResponse, StorageDataPoint,
    ActiveSessionsResponse, UserSession,
    TopologyResponse, ServiceNode, ServiceConnection
)
from backend.api.system.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork
from backend.api.metrics.start_time import start_time
from backend.api.system.router import format_uptime
from backend.api.operations import database_admin
from backend.api.operations import database_routes

logger = get_logger("backend.api.operations")

router = APIRouter()

# Include database routes (LMDB/ChromaDB browsing, SQL queries, backups)
router.include_router(database_routes.router, tags=["databases"])


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
    user: Annotated[dict, Depends(get_current_user)]
) -> DatabaseStatsResponse:
    """
    Get database statistics for all databases (PostgreSQL, ChromaDB, LMDB).
    
    Returns metrics including size, table/collection counts, and health status.
    """
    try:
        databases = []
        
        # PostgreSQL Database
        try:
            import psycopg2
            from aico.core.config import ConfigurationManager
            from aico.security.key_manager import AICOKeyManager
            
            config = ConfigurationManager()
            pg_config = config.get('core.database.postgres', {})
            
            db_host = pg_config.get('host', '127.0.0.1')
            db_port = pg_config.get('port', 5432)
            db_name = pg_config.get('db_name', 'aico')
            db_user = pg_config.get('user', 'postgres')
            
            # Get password from keyring using AICOKeyManager
            key_manager = AICOKeyManager(config)
            db_password = key_manager.get_database_password('postgres', db_user) or ''
            
            # Initialize metrics
            db_size = 0
            table_count = 0
            connection_count = 0
            wal_size = 0
            status = "healthy"
            
            try:
                # Connect to PostgreSQL
                conn = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password,
                    connect_timeout=5
                )
                
                with conn.cursor() as cur:
                    # Get table count from aico_core schema
                    cur.execute(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE'"
                    )
                    table_count = cur.fetchone()[0]
                    
                    # Get active connections
                    cur.execute(
                        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()"
                    )
                    connection_count = cur.fetchone()[0]
                    
                    # Get database size
                    cur.execute(
                        "SELECT pg_database_size(current_database())"
                    )
                    db_size = cur.fetchone()[0]
                    
                    # Get WAL size (approximate current WAL position)
                    cur.execute(
                        "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')"
                    )
                    wal_size = int(cur.fetchone()[0])
                
                conn.close()
                logger.info(f"PostgreSQL metrics collected: {table_count} tables, {connection_count} connections, {db_size} bytes")
                
            except psycopg2.OperationalError as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                status = "critical"
            except Exception as e:
                logger.error(f"Failed to query PostgreSQL metrics: {e}")
                status = "degraded"
            
            databases.append(DatabaseMetrics(
                name="PostgreSQL",
                type="postgresql",
                size_bytes=db_size,
                status=status,
                location=f"{db_host}:{db_port}/{db_name}",
                table_count=table_count,
                connection_count=connection_count,
                wal_size_bytes=wal_size,
                database_name=db_name,
                host=db_host,
                port=db_port,
            ))
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL metrics: {e}")
            databases.append(DatabaseMetrics(
                name="PostgreSQL",
                type="postgresql",
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
        
        # InfluxDB
        try:
            from aico.data.influx.connection import InfluxDBConnection
            from aico.core.config import ConfigurationManager
            
            config = ConfigurationManager()
            influx_config = config.get('core.database.influx', {})
            
            influx_url = influx_config.get('url', 'http://127.0.0.1:8086')
            influx_org = influx_config.get('org', 'aico')
            influx_bucket = influx_config.get('bucket', 'aico_telemetry')
            
            # Initialize metrics
            influx_size = 0
            bucket_count = 0
            measurement_count = 0
            series_count = 0
            status = "healthy"
            error_details = None
            
            try:
                # Connect to InfluxDB
                influx_conn = InfluxDBConnection()
                
                # Check health
                health = influx_conn.health()
                if not health.get('healthy', False):
                    status = "degraded"
                    error_details = health.get('message', 'Health check failed')
                else:
                    # Get bucket list
                    buckets_api = influx_conn.client.buckets_api()
                    buckets = buckets_api.find_buckets().buckets
                    bucket_count = len(buckets) if buckets else 0
                    
                    # Get measurements count for the configured bucket
                    try:
                        measurements_query = f'''
                            import "influxdata/influxdb/schema"
                            schema.measurements(bucket: "{influx_bucket}")
                        '''
                        measurements = influx_conn.query(measurements_query)
                        measurement_count = len(measurements)
                    except Exception as e:
                        logger.debug(f"Could not query measurements: {e}")
                        measurement_count = 0
                    
                    # Get series cardinality (approximate size indicator)
                    try:
                        cardinality_query = f'''
                            from(bucket: "{influx_bucket}")
                            |> range(start: -30d)
                            |> group()
                            |> count()
                        '''
                        cardinality = influx_conn.query(cardinality_query)
                        if cardinality:
                            series_count = sum(r.get('_value', 0) for r in cardinality)
                    except Exception as e:
                        logger.debug(f"Could not query cardinality: {e}")
                        series_count = 0
                    
                    # Estimate size based on series count (rough approximation)
                    # Average ~1KB per series
                    influx_size = series_count * 1024 if series_count > 0 else 0
                
                influx_conn.close()
                
            except ValueError as e:
                # Token not found in keyring
                status = "degraded"
                error_details = str(e)
                logger.warning(f"InfluxDB credentials not configured: {e}")
            except Exception as e:
                status = "degraded"
                error_details = f"Connection failed: {str(e)}"
                logger.error(f"Failed to connect to InfluxDB: {e}")
            
            databases.append(DatabaseMetrics(
                name="InfluxDB",
                type="influxdb",
                size_bytes=influx_size,
                status=status,
                location=influx_url,
                error_details=error_details,
                bucket_count=bucket_count,
                measurement_count=measurement_count,
                series_count=series_count,
                org=influx_org,
                bucket=influx_bucket,
            ))
        except Exception as e:
            logger.error(f"Failed to get InfluxDB metrics: {e}")
            databases.append(DatabaseMetrics(
                name="InfluxDB",
                type="influxdb",
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
    uow: Annotated[UnitOfWork, Depends(get_uow)]
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
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Get all active sessions from last hour
            recent_sessions = await uow.sessions.list(
                filters={"is_active": True},
                limit=10000
            )
            recent_sessions = [s for s in recent_sessions if s.created_at and s.created_at >= cutoff_time]
            
            # Get all users
            all_users = await uow.users.list(limit=10000)
            users_by_uuid = {u.uuid: u for u in all_users}
            
            # Group sessions by user
            sessions_by_user = {}
            for session in recent_sessions:
                if session.user_uuid not in sessions_by_user:
                    sessions_by_user[session.user_uuid] = []
                sessions_by_user[session.user_uuid].append(session)
            
            # Build user session list
            for user_uuid, user_sessions in sessions_by_user.items():
                user_profile = users_by_uuid.get(user_uuid)
                if not user_profile:
                    continue
                
                session_count = len(user_sessions)
                last_activity = max(s.created_at for s in user_sessions if s.created_at)
                
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
                    full_name=user_profile.full_name,
                    nickname=user_profile.nickname,
                    session_count=session_count,
                    last_activity=last_activity.isoformat() if hasattr(last_activity, 'isoformat') else last_activity
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


@router.get("/topology", response_model=TopologyResponse)
async def get_system_topology(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)]
) -> TopologyResponse:
    """
    Get system topology showing service architecture and dependencies.
    
    Returns information about all services, their connections, and deployment configuration.
    """
    try:
        from backend.core.lifecycle_manager import get_service_container
        from backend.services.version_detector import get_version_detector
        import time
        
        # Get versions from shared version system
        backend_version = get_backend_version()
        modelservice_version = get_modelservice_version()
        studio_version = "N/A"  # Placeholder - Studio manages its own version
        
        # Get database versions with caching
        version_detector = get_version_detector()
        db_versions = await version_detector.get_all_versions()
        
        # Get health data for service statuses
        container = get_service_container(request)
        config = container.config if container else None
        
        # Calculate backend uptime (shared by backend, gateway, bus, scheduler)
        backend_uptime_seconds = time.time() - start_time
        backend_uptime_str = format_uptime(backend_uptime_seconds)
        
        # Run all health checks and docker inspects in parallel for performance
        async def get_modelservice_uptime():
            try:
                from backend.services import get_modelservice_client
                from aico.core.config import ConfigurationManager
                
                config = ConfigurationManager()
                modelservice_client = get_modelservice_client(config)
                
                health_data = await modelservice_client.get_health()
                if health_data and health_data.get('success') and health_data.get('uptime_seconds'):
                    return format_uptime(health_data['uptime_seconds'])
            except Exception as e:
                logger.debug(f"Could not poll modelservice uptime: {e}")
            return "N/A"
        
        async def check_ollama_status():
            try:
                import httpx
                
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get("http://localhost:11434/api/version")
                    if response.status_code == 200:
                        return "healthy"
            except Exception as e:
                logger.debug(f"Could not poll Ollama: {e}")
            return "unavailable"
        
        async def get_studio_uptime():
            try:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get("http://localhost:3000")
                    if response.status_code == 200:
                        # Studio is running, try to get uptime from docker if containerized
                        try:
                            result = await asyncio.to_thread(
                                subprocess.run,
                                ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-studio"],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if result.returncode == 0:
                                from datetime import datetime
                                started_at = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                                uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                                return format_uptime(uptime_seconds)
                        except Exception:
                            pass
            except Exception:
                pass
            return "N/A"
        
        async def get_postgres_uptime():
            try:
                import subprocess
                from datetime import datetime
                
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-postgres"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    started_at_str = result.stdout.strip()
                    logger.debug(f"PostgreSQL container started at: {started_at_str}")
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    return format_uptime(uptime_seconds)
                else:
                    logger.debug(f"Docker inspect failed for aico-postgres: {result.stderr}")
            except Exception as e:
                logger.debug(f"Could not get PostgreSQL uptime: {e}")
            return "N/A"
        
        async def get_influxdb_uptime():
            try:
                import subprocess
                from datetime import datetime
                
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-influxdb"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    started_at_str = result.stdout.strip()
                    logger.debug(f"InfluxDB container started at: {started_at_str}")
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    return format_uptime(uptime_seconds)
                else:
                    logger.debug(f"Docker inspect failed for aico-influxdb: {result.stderr}")
            except Exception as e:
                logger.debug(f"Could not get InfluxDB uptime: {e}")
            return "N/A"
        
        # Execute all checks in parallel
        (
            modelservice_uptime_str,
            ollama_status,
            studio_uptime_str,
            postgres_uptime_str,
            influxdb_uptime_str
        ) = await asyncio.gather(
            get_modelservice_uptime(),
            check_ollama_status(),
            get_studio_uptime(),
            get_postgres_uptime(),
            get_influxdb_uptime(),
            return_exceptions=False
        )
        
        # Get Ollama uptime and version
        ollama_uptime_str = modelservice_uptime_str  # Ollama managed by modelservice
        ollama_version = db_versions.get("Ollama", "0.5.x")
        
        # Define services
        services = [
            ServiceNode(
                id="backend",
                name="Backend",
                type="backend",
                status="healthy",
                version=backend_version,
                host="localhost",
                port=8771,
                uptime=backend_uptime_str
            ),
            ServiceNode(
                id="gateway",
                name="API Gateway",
                type="gateway",
                status="healthy",
                version=backend_version,
                host="localhost",
                port=8771,
                uptime=backend_uptime_str
            ),
            ServiceNode(
                id="studio",
                name="Studio",
                type="studio",
                status="healthy",
                version=studio_version,
                host="localhost",
                port=3000,
                uptime=studio_uptime_str
            ),
            ServiceNode(
                id="modelservice",
                name="Model Service",
                type="modelservice",
                status="healthy",
                version=modelservice_version,
                host="localhost",
                port=11434,
                uptime=modelservice_uptime_str
            ),
            ServiceNode(
                id="scheduler",
                name="Task Scheduler",
                type="scheduler",
                status="healthy",
                version=backend_version,
                host="localhost",
                uptime=backend_uptime_str
            ),
            ServiceNode(
                id="bus",
                name="Message Bus",
                type="bus",
                status="healthy",
                version=backend_version,
                host="localhost",
                uptime=backend_uptime_str
            ),
            ServiceNode(
                id="postgresql",
                name="PostgreSQL",
                type="database",
                status="healthy",
                version=db_versions.get("PostgreSQL", "18.1"),
                host="localhost",
                port=5432,
                uptime=postgres_uptime_str
            ),
            ServiceNode(
                id="influxdb",
                name="InfluxDB",
                type="database",
                status="healthy",
                version=db_versions.get("InfluxDB", "2.8.0"),
                host="localhost",
                port=8086,
                uptime=influxdb_uptime_str
            ),
            ServiceNode(
                id="chromadb",
                name="ChromaDB",
                type="database",
                status="healthy",
                version=db_versions.get("ChromaDB", "0.5.x"),
                host="localhost",
                uptime="N/A"
            ),
            ServiceNode(
                id="ollama",
                name="Ollama",
                type="ollama",
                status=ollama_status,
                version=ollama_version,
                host="localhost",
                port=11434,
                uptime=ollama_uptime_str
            ),
            ServiceNode(
                id="lmdb",
                name="LMDB",
                type="database",
                status="healthy",
                version=db_versions.get("LMDB", "0.9.x"),
                host="localhost",
                uptime="N/A"
            ),
        ]
        
        # Define connections
        connections = [
            # Studio -> Gateway
            ServiceConnection(
                from_service="studio",
                to_service="gateway",
                protocol="HTTP/WebSocket",
                port=8771,
                status="active"
            ),
            # Frontend (Flutter) -> Gateway
            ServiceConnection(
                from_service="Frontend",
                to_service="gateway",
                protocol="HTTP/WebSocket",
                port=8771,
                status="active"
            ),
            # CLI -> Gateway
            ServiceConnection(
                from_service="CLI",
                to_service="gateway",
                protocol="HTTP",
                port=8771,
                status="active"
            ),
            # Gateway -> Backend
            ServiceConnection(
                from_service="gateway",
                to_service="backend",
                protocol="HTTP",
                status="active"
            ),
            # Backend -> Model Service
            ServiceConnection(
                from_service="backend",
                to_service="modelservice",
                protocol="HTTP",
                port=8773,
                status="active"
            ),
            # Model Service -> Ollama
            ServiceConnection(
                from_service="modelservice",
                to_service="ollama",
                protocol="HTTP",
                port=11434,
                status="active"
            ),
            # Backend -> Scheduler
            ServiceConnection(
                from_service="backend",
                to_service="scheduler",
                protocol="Internal",
                status="active"
            ),
            # Backend -> Message Bus
            ServiceConnection(
                from_service="backend",
                to_service="bus",
                protocol="ZMQ",
                status="active"
            ),
            # Backend -> PostgreSQL
            ServiceConnection(
                from_service="backend",
                to_service="postgresql",
                protocol="PostgreSQL",
                port=5432,
                status="active"
            ),
            # Backend -> InfluxDB
            ServiceConnection(
                from_service="backend",
                to_service="influxdb",
                protocol="HTTP",
                port=8086,
                status="active"
            ),
            # Backend -> ChromaDB
            ServiceConnection(
                from_service="backend",
                to_service="chromadb",
                protocol="HTTP",
                status="active"
            ),
            # Backend -> LMDB
            ServiceConnection(
                from_service="backend",
                to_service="lmdb",
                protocol="Direct",
                status="active"
            ),
            # Scheduler -> Message Bus
            ServiceConnection(
                from_service="scheduler",
                to_service="bus",
                protocol="ZMQ",
                status="active"
            ),
        ]
        
        return TopologyResponse(
            services=services,
            connections=connections,
            deployment_type="localhost"
        )
        
    except Exception as e:
        logger.exception(f"Failed to get system topology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system topology: {str(e)}"
        )


# ============================================================================
# Stage 1: Database Details - Table/Collection Browser
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
    """
    if database_type == "postgresql":
        return await database_admin.get_postgresql_details()
    elif database_type == "chromadb":
        return await database_admin.get_chromadb_details(request)
    elif database_type == "lmdb":
        return await database_admin.get_lmdb_details()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown database type: {database_type}"
        )


# ============================================================================
# Stage 2: SQL Query Interface
# ============================================================================

@router.get("/databases/postgresql/schema", response_model=SchemaMetadata)
async def get_database_schema(
    user: Annotated[dict, Depends(get_current_user)]
) -> SchemaMetadata:
    """
    Get database schema metadata for autocomplete.
    Returns table names and their columns.
    """
    return await database_admin.get_schema_metadata()


@router.post("/databases/postgresql/query", response_model=QueryResult)
async def execute_sql_query(
    query_request: QueryRequest,
    user: Annotated[dict, Depends(get_current_user)]
) -> QueryResult:
    """
    Execute a SQL query on PostgreSQL database.
    
    **Security**:
    - SELECT and SHOW queries allowed by default
    - Destructive operations (DELETE, UPDATE, INSERT) require allow_destructive=true
    - Forbidden operations (DROP, ALTER, TRUNCATE) always blocked
    - Auto-adds LIMIT to SELECT queries
    - Maximum query length: 10,000 characters
    - Execution timeout: 30 seconds
    """
    return await database_admin.execute_sql_query(
        query_request.query,
        query_request.limit or 100,
        query_request.allow_destructive
    )


# format_uptime is now imported from backend.api.system.router
