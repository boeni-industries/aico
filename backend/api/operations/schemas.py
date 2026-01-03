"""
Operations API Schemas

Data models for operations monitoring endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


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
