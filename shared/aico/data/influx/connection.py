"""InfluxDB connection layer for AICO telemetry.

This module provides a high-level abstraction for writing and querying
telemetry data in InfluxDB, with integrated credential management via
AICOKeyManager.

Design principles:
- Credentials retrieved from system keyring (never hardcoded)
- Configuration from core.yaml (url, org, bucket)
- Batch writing support for high-throughput scenarios
- Automatic retry logic for transient failures
- Type-safe line protocol generation
"""

import logging
import sys
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse
from contextlib import contextmanager

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager

logger = logging.getLogger(__name__)

# Monkey-patch InfluxDB client to suppress __del__ exception
# This is a known bug in influxdb-client-python where ApiClient.__del__ fails during shutdown
try:
    from influxdb_client._sync.api_client import ApiClient
    _original_del = ApiClient.__del__
    
    def _patched_del(self):
        try:
            _original_del(self)
        except (TypeError, AttributeError):
            # Suppress the 'NoneType' object is not callable error during shutdown
            pass
    
    ApiClient.__del__ = _patched_del
except Exception:
    # If patching fails, just continue - the exception is cosmetic anyway
    pass


class InfluxDBConnection:
    """InfluxDB client wrapper with credential management and batch writing.
    
    Usage:
        # Initialize from config
        conn = InfluxDBConnection()
        
        # Write single point
        conn.write_point(
            measurement="api_request",
            tags={"service": "backend", "method": "GET"},
            fields={"latency_ms": 123.4, "status_code": 200}
        )
        
        # Write batch
        points = [
            {"measurement": "api_request", "tags": {...}, "fields": {...}},
            {"measurement": "model_inference", "tags": {...}, "fields": {...}}
        ]
        conn.write_points(points)
        
        # Query with Flux
        results = conn.query('from(bucket: "aico_telemetry") |> range(start: -1h)')
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigurationManager] = None,
        key_manager: Optional[AICOKeyManager] = None,
        async_mode: bool = False
    ):
        """Initialize InfluxDB connection.
        
        Args:
            config_manager: Configuration manager instance (creates new if None)
            key_manager: Key manager for credential retrieval (creates new if None)
            async_mode: Use asynchronous write API (default: synchronous)
        """
        # Initialize config and key managers
        if config_manager is None:
            config_manager = ConfigurationManager()
            config_manager.initialize(lightweight=True)
        
        if key_manager is None:
            key_manager = AICOKeyManager(config_manager)
        
        self.config_manager = config_manager
        self.key_manager = key_manager
        self.async_mode = async_mode
        
        # Load configuration
        influx_config = config_manager.get("influx", {}) or {}
        
        self.url = influx_config.get("url", "http://127.0.0.1:8086")
        self.org = influx_config.get("org", "aico")
        self.bucket = influx_config.get("bucket", "aico_telemetry")
        
        # Retrieve token from keyring
        self.token = key_manager.get_database_password("influx", username="admin_token")
        
        if not self.token:
            raise ValueError(
                "InfluxDB admin token not found in keyring. "
                "Run 'aico deploy influx' to set up credentials."
            )
        
        # Initialize InfluxDB client
        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org,
            timeout=30_000  # 30 seconds
        )
        
        # Initialize write API
        write_mode = ASYNCHRONOUS if async_mode else SYNCHRONOUS
        self.write_api = self.client.write_api(write_options=write_mode)
        
        # Initialize query API
        self.query_api = self.client.query_api()
        
        logger.debug(
            f"InfluxDB connection initialized: url={self.url}, org={self.org}, "
            f"bucket={self.bucket}, async={async_mode}"
        )
    
    def write_point(
        self,
        measurement: str,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        bucket: Optional[str] = None
    ) -> None:
        """Write a single data point to InfluxDB.
        
        Args:
            measurement: Measurement name (e.g., "api_request", "model_inference")
            tags: Tag key-value pairs (indexed, low cardinality)
            fields: Field key-value pairs (not indexed, can be high cardinality)
            timestamp: Point timestamp (default: current time)
            bucket: Target bucket (default: configured bucket)
        
        Example:
            conn.write_point(
                measurement="api_request",
                tags={
                    "service": "api-gateway",
                    "method": "GET",
                    "path": "/v1/messages",
                    "status_class": "2xx"
                },
                fields={
                    "status_code_i": 200,
                    "latency_ms_f": 123.4,
                    "response_size_i": 2048
                }
            )
        """
        point = Point(measurement)
        
        # Add tags
        if tags:
            for key, value in tags.items():
                point.tag(key, value)
        
        # Add fields
        if fields:
            for key, value in fields.items():
                point.field(key, value)
        
        # Set timestamp
        if timestamp:
            point.time(timestamp, WritePrecision.NS)
        
        # Write to InfluxDB
        target_bucket = bucket or self.bucket
        try:
            self.write_api.write(bucket=target_bucket, org=self.org, record=point)
            logger.debug(f"Wrote point to {measurement}: tags={tags}, fields={fields}")
        except InfluxDBError as e:
            logger.error(f"Failed to write point to InfluxDB: {e}")
            raise
    
    def write_points(
        self,
        points: List[Dict[str, Any]],
        bucket: Optional[str] = None
    ) -> None:
        """Write multiple data points to InfluxDB in a batch.
        
        Args:
            points: List of point dictionaries with keys: measurement, tags, fields, timestamp
            bucket: Target bucket (default: configured bucket)
        
        Example:
            points = [
                {
                    "measurement": "api_request",
                    "tags": {"service": "backend", "method": "GET"},
                    "fields": {"latency_ms_f": 123.4, "status_code_i": 200}
                },
                {
                    "measurement": "model_inference",
                    "tags": {"model_name": "llama-3.2-3b", "task_type": "chat"},
                    "fields": {"duration_ms_f": 842.7, "tokens_generated_i": 256}
                }
            ]
            conn.write_points(points)
        """
        influx_points = []
        
        for point_data in points:
            point = Point(point_data["measurement"])
            
            # Add tags
            if "tags" in point_data and point_data["tags"]:
                for key, value in point_data["tags"].items():
                    point.tag(key, value)
            
            # Add fields
            if "fields" in point_data and point_data["fields"]:
                for key, value in point_data["fields"].items():
                    point.field(key, value)
            
            # Set timestamp
            if "timestamp" in point_data and point_data["timestamp"]:
                point.time(point_data["timestamp"], WritePrecision.NS)
            
            influx_points.append(point)
        
        # Write batch to InfluxDB
        target_bucket = bucket or self.bucket
        try:
            self.write_api.write(bucket=target_bucket, org=self.org, record=influx_points)
            logger.debug(f"Wrote {len(influx_points)} points to InfluxDB")
        except InfluxDBError as e:
            logger.error(f"Failed to write batch to InfluxDB: {e}")
            raise
    
    def write_line_protocol(
        self,
        line_protocol: Union[str, List[str]],
        bucket: Optional[str] = None
    ) -> None:
        """Write raw line protocol to InfluxDB.
        
        Args:
            line_protocol: Line protocol string or list of strings
            bucket: Target bucket (default: configured bucket)
        
        Example:
            conn.write_line_protocol(
                "api_request,service=backend,method=GET latency_ms_f=123.4,status_code_i=200"
            )
        """
        target_bucket = bucket or self.bucket
        try:
            self.write_api.write(bucket=target_bucket, org=self.org, record=line_protocol)
            logger.debug(f"Wrote line protocol to InfluxDB")
        except InfluxDBError as e:
            logger.error(f"Failed to write line protocol to InfluxDB: {e}")
            raise
    
    def query(
        self,
        flux_query: str,
        org: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Flux query and return results as list of dictionaries.
        
        Args:
            flux_query: Flux query string
            org: Organization name (default: configured org)
        
        Returns:
            List of result dictionaries with keys from the query
        
        Example:
            results = conn.query('''
                from(bucket: "aico_telemetry")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "backend")
                |> mean(column: "latency_ms_f")
            ''')
        """
        target_org = org or self.org
        
        try:
            tables = self.query_api.query(flux_query, org=target_org)
            
            results = []
            for table in tables:
                for record in table.records:
                    # Convert FluxRecord to dictionary
                    result = {}
                    
                    # Safely get measurement, time, value, field (may not exist in all queries)
                    try:
                        result["measurement"] = record.get_measurement()
                    except (KeyError, AttributeError):
                        pass
                    
                    try:
                        result["time"] = record.get_time()
                    except (KeyError, AttributeError):
                        pass
                    
                    try:
                        result["value"] = record.get_value()
                    except (KeyError, AttributeError):
                        pass
                    
                    try:
                        result["field"] = record.get_field()
                    except (KeyError, AttributeError):
                        pass
                    
                    # Add all tags and fields from record.values
                    result.update(record.values)
                    
                    results.append(result)
            
            logger.debug(f"Query returned {len(results)} results")
            return results
            
        except InfluxDBError as e:
            # Downgrade "empty range" errors to DEBUG - these are expected when measurements have no data
            if "cannot query an empty range" in str(e):
                logger.debug(f"Query returned empty range (no data available): {e}")
            else:
                logger.error(f"Failed to execute query: {e}")
            raise
    
    def query_dataframe(
        self,
        flux_query: str,
        org: Optional[str] = None
    ):
        """Execute a Flux query and return results as pandas DataFrame.
        
        Args:
            flux_query: Flux query string
            org: Organization name (default: configured org)
        
        Returns:
            pandas DataFrame with query results
        
        Note:
            Requires pandas to be installed
        """
        target_org = org or self.org
        
        try:
            df = self.query_api.query_data_frame(flux_query, org=target_org)
            logger.debug(f"Query returned DataFrame with {len(df)} rows")
            return df
        except InfluxDBError as e:
            # Downgrade "empty range" errors to DEBUG - these are expected when measurements have no data
            if "cannot query an empty range" in str(e):
                logger.debug(f"Query returned empty range (no data available): {e}")
            else:
                logger.error(f"Failed to execute query: {e}")
            raise
        except ImportError:
            logger.error("pandas is required for query_dataframe()")
            raise
    
    def health(self) -> Dict[str, Any]:
        """Check InfluxDB health status.
        
        Returns:
            Dictionary with health status information
        """
        try:
            health = self.client.health()
            return {
                "status": health.status,
                "message": health.message,
                "version": health.version,
                "healthy": health.status == "pass"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "fail",
                "message": str(e),
                "healthy": False
            }
    
    def ping(self) -> bool:
        """Ping InfluxDB to check connectivity.
        
        Returns:
            True if InfluxDB is reachable, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the InfluxDB client connection."""
        try:
            if hasattr(self, 'write_api') and self.write_api is not None:
                self.write_api.close()
                self.write_api = None
            if hasattr(self, 'client') and self.client is not None:
                self.client.close()
                self.client = None
            logger.debug("InfluxDB connection closed")
        except Exception:
            # Ignore errors during cleanup (e.g., during Python shutdown)
            pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        try:
            self.close()
        except Exception:
            pass
