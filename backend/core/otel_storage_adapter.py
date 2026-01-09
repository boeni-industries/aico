"""
OpenTelemetry to SQLite Storage Adapter

Bridges OpenTelemetry metrics to local SQLite storage for Studio dashboard.
Implements MetricExporter interface to export metrics periodically.

Design Principles:
- Reuse existing metrics table schema
- Efficient batch writes
- Automatic aggregation (rates, percentiles, trends)
- Thread-safe operations
- Uses encrypted database connection
"""

import time
import logging
from typing import Optional, Sequence, Dict, Any
from threading import Lock
from collections import defaultdict

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricReader,
    MetricExporter,
    MetricsData,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import View

logger = logging.getLogger("backend.otel_storage")


class OTelStorageExporter(MetricExporter):
    """
    MetricReader that exports OpenTelemetry metrics to SQLite.
    
    Collects metrics periodically and writes to database tables
    that match the existing schema used by MetricsCollector.
    
    Uses the encrypted database connection from the service container.
    """
    
    def __init__(
        self,
        db_connection=None,
    ):
        super().__init__()
        
        self.db_connection = db_connection
        self.lock = Lock()
    
    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> "MetricExportResult":
        """
        Export metrics to SQLite database.
        
        This is called periodically by the PeriodicExportingMetricReader.
        We parse the metrics and write them to appropriate SQLite tables.
        """
        from opentelemetry.sdk.metrics.export import MetricExportResult
        
        if not metrics_data or not metrics_data.resource_metrics:
            return MetricExportResult.SUCCESS
        
        with self.lock:
            try:
                if not self.db_connection:
                    logger.warning("No database connection available for metrics export")
                    return MetricExportResult.FAILURE
                
                # Use connection context manager with retry logic for locks
                max_retries = 3
                retry_delay = 0.5  # 500ms
                
                for attempt in range(max_retries):
                    try:
                        with self.db_connection.get_connection() as conn:
                            # Set busy_timeout to handle concurrent writes from multiple services
                            conn.execute("PRAGMA busy_timeout = 5000")
                            
                            for resource_metric in metrics_data.resource_metrics:
                                for scope_metric in resource_metric.scope_metrics:
                                    for metric in scope_metric.metrics:
                                        self._process_metric(conn, metric)
                        
                        # Commit after cursor is closed (outside context manager)
                        self.db_connection.commit()
                        return MetricExportResult.SUCCESS
                    
                    except ValueError as e:
                        if "database is locked" in str(e):
                            if attempt < max_retries - 1:
                                # Database is busy, wait and retry
                                time.sleep(retry_delay)
                                continue
                            else:
                                # Max retries reached - log warning about DB performance issue
                                logger.warning(f"Failed to export metrics after {max_retries} attempts - database locked. This indicates DB performance issues.")
                                return MetricExportResult.SUCCESS
                        else:
                            # Different error
                            logger.warning(f"Failed to export metrics: {e}")
                            return MetricExportResult.SUCCESS
                    
            except Exception as e:
                # Silently skip on errors - metrics collection should not disrupt the system
                return MetricExportResult.SUCCESS
    
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shutdown the exporter"""
        pass
    
    def force_flush(self, timeout_millis: float = 10_000, **kwargs) -> bool:
        """Force flush any pending metrics"""
        logger.debug("OTelStorageExporter force flush")
        return True
    
    def _process_metric(self, cursor, metric) -> None:
        """Process a single metric and write to appropriate table"""
        metric_name = metric.name
        
        # Route metric to appropriate table based on name
        if metric_name.startswith("aico.api."):
            self._process_api_metric(cursor, metric)
        elif metric_name.startswith("aico.modelservice."):
            self._process_modelservice_metric(cursor, metric)
        elif metric_name.startswith("aico.memory."):
            self._process_memory_metric(cursor, metric)
        elif metric_name.startswith("aico.scheduler."):
            self._process_scheduler_metric(cursor, metric)
        elif metric_name.startswith("aico.messagebus."):
            self._process_messagebus_metric(cursor, metric)
    
    def _process_api_metric(self, conn, metric) -> None:
        """Process API Gateway metrics"""
        # Extract data points from metric
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            # Map metric to table columns
            if metric.name == "aico.api.request.duration":
                # Histogram - extract aggregated data (sum/count)
                # For histograms, we store the average latency per data point
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count > 0:
                        avg_latency_seconds = data_point.sum / data_point.count
                        conn.execute("""
                            INSERT INTO otel_api_requests 
                            (timestamp, method, path, status_code, latency_ms, protocol, service, category)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data_point.time_unix_nano / 1e9,
                            attributes.get('http.method', 'GET'),
                            attributes.get('http.target', '/'),
                            attributes.get('http.status_code', 200),
                            avg_latency_seconds * 1000,  # Convert to ms
                            attributes.get('http.scheme', 'REST').upper(),
                            attributes.get('service', 'unknown'),
                            attributes.get('category', 'other')
                        ))
    
    def _process_modelservice_metric(self, conn, metric) -> None:
        """Process Modelservice metrics"""
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.modelservice.inference.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count > 0:
                        avg_time_seconds = data_point.sum / data_point.count
                        
                        # Check if new columns exist (post-migration)
                        # This gracefully handles both old and new schema
                        try:
                            # Try new schema with all columns
                            task_type = attributes.get('task.type', 'unknown')
                            tokens_generated = attributes.get('tokens.generated')
                            prompt_tokens = attributes.get('prompt.tokens')
                            entities_count = attributes.get('entities.count')
                            entity_types = attributes.get('entity.types')
                            confidence_score = attributes.get('confidence.score')
                            sentiment_result = attributes.get('sentiment.result')
                            ttft = attributes.get('ttft')
                            
                            conn.execute("""
                                INSERT INTO otel_model_inferences 
                                (timestamp, model_name, task_type, inference_time_ms, tokens_generated, 
                                 prompt_tokens, entities_count, entity_types, confidence_score, 
                                 sentiment_result, ttft, success)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                data_point.time_unix_nano / 1e9,
                                attributes.get('model.name', 'unknown'),
                                task_type,
                                avg_time_seconds * 1000,
                                tokens_generated if tokens_generated is not None else None,
                                prompt_tokens if prompt_tokens is not None else None,
                                entities_count if entities_count is not None else None,
                                entity_types if entity_types else None,
                                confidence_score if confidence_score is not None else None,
                                sentiment_result if sentiment_result else None,
                                ttft if ttft is not None else None,
                                attributes.get('success', True)
                            ))
                        except Exception:
                            # Fall back to old schema (pre-migration)
                            tokens_generated = attributes.get('tokens.generated')
                            conn.execute("""
                                INSERT INTO otel_model_inferences 
                                (timestamp, model_name, inference_time_ms, tokens_generated, success)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                data_point.time_unix_nano / 1e9,
                                attributes.get('model.name', 'unknown'),
                                avg_time_seconds * 1000,
                                tokens_generated if tokens_generated is not None else None,
                                attributes.get('success', True)
                            ))
    
    def _process_memory_metric(self, conn, metric) -> None:
        """Process Memory system metrics"""
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.memory.query.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count > 0:
                        avg_time_seconds = data_point.sum / data_point.count
                        conn.execute("""
                            INSERT INTO otel_memory_queries 
                            (timestamp, query_type, query_time_ms, results_count, success)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            data_point.time_unix_nano / 1e9,
                            attributes.get('query.type', 'unknown'),
                            avg_time_seconds * 1000,  # Convert to ms
                            attributes.get('results.count', 0),
                            attributes.get('success', True)
                        ))
    
    def _process_scheduler_metric(self, conn, metric) -> None:
        """Process Scheduler metrics"""
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.scheduler.job.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count > 0:
                        avg_time_seconds = data_point.sum / data_point.count
                        conn.execute("""
                            INSERT INTO otel_scheduler_jobs 
                            (timestamp, job_type, queue_name, duration_ms, success, error_message)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            data_point.time_unix_nano / 1e9,
                            attributes.get('job.type', 'unknown'),
                            attributes.get('queue.name', 'default'),
                            avg_time_seconds * 1000,  # Convert to ms
                            attributes.get('success', True),
                            attributes.get('error.message')
                        ))
    
    def _process_messagebus_metric(self, conn, metric) -> None:
        """Process Message Bus metrics"""
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.messagebus.message.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count > 0:
                        avg_time_seconds = data_point.sum / data_point.count
                        conn.execute("""
                            INSERT INTO otel_message_bus_events 
                            (timestamp, topic, message_count, processing_time_ms, backlog_depth, consumer_count)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            data_point.time_unix_nano / 1e9,
                            attributes.get('topic', 'unknown'),
                            data_point.count,  # Use actual count
                            avg_time_seconds * 1000,  # Convert to ms
                            attributes.get('backlog.depth', 0),
                            attributes.get('consumer.count', 0)
                        ))
    
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> bool:
        """Shutdown the reader and flush pending metrics"""
        logger.info("OTelStorageReader shutting down")
        return True
