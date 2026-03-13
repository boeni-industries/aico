"""
Operations API Schemas

Data models for operations monitoring endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class DatabaseMetrics(BaseModel):
    """Metrics for a single database"""
    name: str = Field(..., description="Database name")
    type: str = Field(..., description="Database type (postgresql, influxdb)")
    size_bytes: int = Field(..., description="Database size in bytes")
    status: str = Field(..., description="Database status (healthy, degraded, critical)")
    location: str = Field(..., description="Database location (file path or connection string)")
    error_details: Optional[str] = Field(None, description="Error details for degraded/critical status")
    table_count: Optional[int] = Field(None, description="Number of tables (PostgreSQL)")
    connection_count: Optional[int] = Field(None, description="Active connections (PostgreSQL)")
    wal_size_bytes: Optional[int] = Field(None, description="WAL size in bytes (PostgreSQL)")
    database_name: Optional[str] = Field(None, description="Database name (PostgreSQL)")
    host: Optional[str] = Field(None, description="Database host (PostgreSQL)")
    port: Optional[int] = Field(None, description="Database port (PostgreSQL)")
    bucket_count: Optional[int] = Field(None, description="Number of buckets (InfluxDB)")
    measurement_count: Optional[int] = Field(None, description="Number of measurements (InfluxDB)")
    series_count: Optional[int] = Field(None, description="Number of series (InfluxDB)")
    org: Optional[str] = Field(None, description="Organization name (InfluxDB)")
    bucket: Optional[str] = Field(None, description="Bucket name (InfluxDB)")


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics"""
    databases: list[DatabaseMetrics] = Field(..., description="List of database metrics")


class TableInfo(BaseModel):
    """Information about a database table"""
    name: str = Field(..., description="Table name")
    row_count: int = Field(..., description="Number of rows")
    size_bytes: Optional[int] = Field(None, description="Table size in bytes")
    columns: Optional[int] = Field(None, description="Number of columns")


class CollectionInfo(BaseModel):
    """Information about a database collection"""
    name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of documents")
    metadata: Optional[dict] = Field(None, description="Collection metadata")
    dimension: Optional[int] = Field(None, description="Embedding dimension")


class DatabaseDetailsResponse(BaseModel):
    """Response model for database details"""
    database_type: str = Field(..., description="Database type (postgresql, influxdb)")
    tables: Optional[list[TableInfo]] = Field(None, description="Tables (PostgreSQL)")


class QueryResult(BaseModel):
    """Result of a SQL query execution"""
    success: bool = Field(..., description="Whether query executed successfully")
    error: Optional[str] = Field(None, description="Error message if query failed")
    columns: list[str] = Field(default_factory=list, description="Column names")
    rows: list[list] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(0, description="Number of rows returned")
    is_destructive: bool = Field(False, description="Whether query contains destructive operations")


class QueryRequest(BaseModel):
    """Request to execute a SQL query"""
    query: str = Field(..., description="SQL query to execute")
    limit: Optional[int] = Field(100, description="Maximum rows to return")
    allow_destructive: bool = Field(False, description="Allow destructive operations (DELETE, UPDATE, INSERT)")


class SchemaMetadata(BaseModel):
    """Database schema metadata for autocomplete"""
    tables: list[str] = Field(default_factory=list, description="List of table names")
    columns: dict[str, list[str]] = Field(default_factory=dict, description="Columns per table")


class BackupSetCreateRequest(BaseModel):
    """Request to create a coordinated backup set."""
    output_path: Optional[str] = Field(
        None,
        description="Optional host filesystem path where the backup set directory should be created. If omitted, a platform-dependent default derived from AICOPaths is used.",
    )
    include_influx: bool = Field(
        False,
        description="Whether to include InfluxDB (telemetry) in the backup set. Excluded by default.",
    )
    created_by_user_uuid: Optional[str] = Field(
        None,
        description="User UUID responsible for creating the backup set (set by gateway for auditability).",
    )


class BackupSetInfo(BaseModel):
    """Lightweight registry information for a backup set."""
    backup_id: str = Field(..., description="Backup set ID")
    created_at: str = Field(..., description="Backup set creation timestamp")
    path: str = Field(..., description="Absolute path to the backup set directory on disk")
    included: dict = Field(..., description="Component inclusion map (postgres/lmdb/influxdb)")
    status: Optional[str] = Field(None, description="Backup set status (creating/available/deleted/error)")
    deleted_at: Optional[str] = Field(None, description="Deletion timestamp when soft-deleted")
    deleted_by_user_uuid: Optional[str] = Field(None, description="User UUID who deleted the backup")


class BackupSetCreateResponse(BaseModel):
    """Response for backup set creation."""
    success: bool = Field(..., description="Whether backup set creation succeeded")
    backup_set: Optional[BackupSetInfo] = Field(None, description="Backup set info")
    message: str = Field(..., description="Status message")


class BackupSetListResponse(BaseModel):
    """Response for listing backup sets."""
    backup_sets: list[BackupSetInfo] = Field(..., description="Known backup sets")
    total_count: int = Field(..., description="Total number of backup sets")


class BackupSetStatusResponse(BaseModel):
    """Response for backup set status."""
    backup_set: BackupSetInfo = Field(..., description="Backup set info")
    manifest: Optional[dict] = Field(None, description="Parsed manifest.json (if available)")


class BackupSetUploadResponse(BaseModel):
    """Response for uploading/importing a backup set archive."""
    success: bool = Field(..., description="Whether upload succeeded")
    backup_id: str = Field(..., description="Imported backup set ID")
    message: str = Field(..., description="Status message")


class BackupSetRestoreRequest(BaseModel):
    """Request to restore a coordinated backup set."""
    backup_id: str = Field(..., description="Backup set ID to restore")
    confirm_destroy_existing: bool = Field(
        False,
        description="Must be true to perform restore operations that replace existing databases.",
    )
    restore_to_primary: bool = Field(
        False,
        description="If true, restore PostgreSQL to the primary container after restoring+verifying postgres-shadow.",
    )
    restore_influx: bool = Field(
        False,
        description="If true and the backup set includes InfluxDB, restore InfluxDB telemetry.",
    )


class BackupSetRestoreResponse(BaseModel):
    """Response for backup set restore."""
    success: bool = Field(..., description="Whether restore succeeded")
    message: str = Field(..., description="Status message")


class BackupSetDeleteResponse(BaseModel):
    """Response for deleting a backup set."""
    success: bool = Field(..., description="Whether delete succeeded")
    backup_id: str = Field(..., description="Backup set ID")
    deleted_dir: bool = Field(..., description="Whether the backup set directory was deleted")
    deleted_archive: bool = Field(..., description="Whether the backup set tar.gz archive was deleted")
    freed_bytes: int = Field(..., description="Estimated bytes freed")
    message: str = Field(..., description="Status message")


class BackupSetPruneRequest(BaseModel):
    """Request to prune backup sets."""
    keep_last_n: Optional[int] = Field(
        None,
        description="If provided, keep the newest N backup sets and delete older ones.",
    )
    older_than_days: Optional[int] = Field(
        None,
        description="If provided, delete backup sets older than this many days.",
    )
    dry_run: bool = Field(
        True,
        description="If true, only report what would be deleted without deleting anything.",
    )


class BackupSetPruneResponse(BaseModel):
    """Response for pruning backup sets."""
    success: bool = Field(..., description="Whether prune operation succeeded")
    dry_run: bool = Field(..., description="Whether this was a dry-run")
    considered_count: int = Field(..., description="Total backup sets considered")
    deleted_count: int = Field(..., description="Number of backup sets deleted")
    would_delete_backup_ids: list[str] = Field(..., description="Backup IDs that were (or would be) deleted")
    freed_bytes: int = Field(..., description="Estimated bytes freed")
    message: str = Field(..., description="Status message")


class UserSession(BaseModel):
    """Active user session information"""
    user_uuid: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User full name")
    nickname: Optional[str] = Field(None, description="User nickname")
    session_count: int = Field(..., description="Number of active sessions")
    last_activity: str = Field(..., description="Last activity timestamp")


class ActiveSessionsResponse(BaseModel):
    """Response model for active user sessions"""
    sessions: list[UserSession] = Field(..., description="List of active user sessions")
    total_sessions: int = Field(..., description="Total number of active sessions")


class ServiceNode(BaseModel):
    """Service node in the topology graph"""
    id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service display name")
    type: str = Field(..., description="Service type (backend, modelservice, scheduler, etc.)")
    status: str = Field(..., description="Service status (healthy, degraded, critical, offline)")
    version: str = Field(..., description="Service version")
    host: str = Field(..., description="Host address")
    port: Optional[int] = Field(None, description="Port number")
    uptime: str = Field(..., description="Service uptime")


class ServiceConnection(BaseModel):
    """Connection between services"""
    model_config = {"populate_by_name": True}
    
    from_service: str = Field(..., alias="from", description="Source service ID")
    to_service: str = Field(..., alias="to", description="Target service ID")
    protocol: str = Field(..., description="Communication protocol (HTTP, WebSocket, ZMQ)")
    port: Optional[int] = Field(None, description="Connection port")
    status: str = Field(..., description="Connection status (active, inactive)")
    latency: Optional[float] = Field(None, description="Connection latency in ms")


class TopologyResponse(BaseModel):
    """Response model for system topology"""
    services: list[ServiceNode] = Field(..., description="List of services in the topology")
    connections: list[ServiceConnection] = Field(..., description="List of connections between services")
    deployment_type: str = Field(..., description="Deployment type (localhost, distributed)")
