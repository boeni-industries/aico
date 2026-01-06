"""
Operations API Schemas

Data models for operations monitoring endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class DatabaseMetrics(BaseModel):
    """Metrics for a single database"""
    name: str = Field(..., description="Database name")
    type: str = Field(..., description="Database type (libsql, chromadb, lmdb)")
    size_bytes: int = Field(..., description="Database size in bytes")
    status: str = Field(..., description="Database status (healthy, degraded, critical)")
    location: str = Field(..., description="Database file path")
    error_details: Optional[str] = Field(None, description="Error details for degraded/critical status")
    table_count: Optional[int] = Field(None, description="Number of tables (LibSQL)")
    connection_count: Optional[int] = Field(None, description="Active connections (LibSQL)")
    wal_size_bytes: Optional[int] = Field(None, description="WAL size in bytes (LibSQL)")
    collection_count: Optional[int] = Field(None, description="Number of collections (ChromaDB)")
    document_count: Optional[int] = Field(None, description="Number of documents (ChromaDB)")
    index_size_bytes: Optional[int] = Field(None, description="Index size in bytes (ChromaDB)")
    database_count: Optional[int] = Field(None, description="Number of databases (LMDB)")
    key_count: Optional[int] = Field(None, description="Number of keys (LMDB)")
    map_size_bytes: Optional[int] = Field(None, description="Map size in bytes (LMDB)")


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
    """Information about a ChromaDB collection"""
    name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of documents")
    metadata: Optional[dict] = Field(None, description="Collection metadata")
    dimension: Optional[int] = Field(None, description="Embedding dimension")


class LMDBDatabaseInfo(BaseModel):
    """Information about an LMDB database"""
    name: str = Field(..., description="Database name")
    key_count: int = Field(..., description="Number of keys")
    size_bytes: Optional[int] = Field(None, description="Database size")


class DatabaseDetailsResponse(BaseModel):
    """Response model for database details"""
    database_type: str = Field(..., description="Database type (libsql, chromadb, lmdb)")
    tables: Optional[list[TableInfo]] = Field(None, description="Tables (LibSQL)")
    collections: Optional[list[CollectionInfo]] = Field(None, description="Collections (ChromaDB)")
    databases: Optional[list[LMDBDatabaseInfo]] = Field(None, description="Databases (LMDB)")


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


class BackupInfo(BaseModel):
    """Information about a database backup"""
    id: str = Field(..., description="Backup ID")
    database_name: str = Field(..., description="Database name")
    created_at: str = Field(..., description="Backup creation timestamp")
    size_bytes: int = Field(..., description="Backup size in bytes")
    backup_path: str = Field(..., description="Path to backup file")
    status: str = Field(..., description="Backup status (completed, failed, in_progress)")


class BackupResponse(BaseModel):
    """Response for backup operation"""
    success: bool = Field(..., description="Whether backup succeeded")
    backup_info: Optional[BackupInfo] = Field(None, description="Backup information")
    message: str = Field(..., description="Status message")


class BackupHistoryResponse(BaseModel):
    """Response for backup history"""
    backups: list[BackupInfo] = Field(..., description="List of backups")
    total_count: int = Field(..., description="Total number of backups")


class RestoreRequest(BaseModel):
    """Request to restore from backup"""
    backup_id: str = Field(..., description="Backup ID to restore from")


class RestoreResponse(BaseModel):
    """Response for restore operation"""
    success: bool = Field(..., description="Whether restore succeeded")
    message: str = Field(..., description="Status message")


class StorageDataPoint(BaseModel):
    """Storage size at a point in time"""
    timestamp: str = Field(..., description="Timestamp")
    size_bytes: int = Field(..., description="Size in bytes")


class StorageTrendResponse(BaseModel):
    """Response model for storage growth trends"""
    database_name: str = Field(..., description="Database name")
    data_points: list[StorageDataPoint] = Field(..., description="Historical data points")
    current_size: int = Field(..., description="Current size in bytes")
    growth_rate: Optional[float] = Field(None, description="Growth rate (bytes per day)")


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
