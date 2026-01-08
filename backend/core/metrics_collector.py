"""
Metrics Collection Infrastructure

Provides real-time metrics collection for all AICO subsystems.
All metrics are stored in the database and aggregated for the Studio dashboard.

Design Principles:
- No mock data - all metrics are real
- Transparent health scoring with clear reasoning
- Efficient aggregation with minimal overhead
- Thread-safe collection from multiple sources
"""

import time
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger("backend.metrics_collector")


class MetricsCollector:
    """
    Centralized metrics collection and aggregation service.
    
    Collects metrics from all subsystems and provides aggregated views
    for the Studio dashboard. All data is persisted to the database.
    """
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
        self.lock = Lock()
        self._ensure_schema()
        logger.info("MetricsCollector initialized")
    
    def _ensure_schema(self):
        """Create metrics tables if they don't exist"""
        cursor = self.db.cursor()
        
        # API Gateway request metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_request_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                protocol TEXT DEFAULT 'REST',
                client_id TEXT,
                error_message TEXT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_path (path),
                INDEX idx_status (status_code)
            )
        """)
        
        # Modelservice inference metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modelservice_inference_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                model_name TEXT NOT NULL,
                inference_time_ms REAL NOT NULL,
                tokens_generated INTEGER,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_model (model_name)
            )
        """)
        
        # Memory system query metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_query_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                query_type TEXT NOT NULL,
                query_time_ms REAL NOT NULL,
                results_count INTEGER,
                success BOOLEAN NOT NULL,
                INDEX idx_timestamp (timestamp),
                INDEX idx_type (query_type)
            )
        """)
        
        # Scheduler job metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_job_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                job_type TEXT NOT NULL,
                queue_name TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_job_type (job_type),
                INDEX idx_queue (queue_name)
            )
        """)
        
        # Message bus metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_bus_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                topic TEXT NOT NULL,
                message_count INTEGER DEFAULT 1,
                processing_time_ms REAL,
                backlog_depth INTEGER,
                consumer_count INTEGER,
                INDEX idx_timestamp (timestamp),
                INDEX idx_topic (topic)
            )
        """)
        
        self.db.commit()
        logger.info("Metrics schema initialized")
    
    # ==================== API Gateway Metrics ====================
    
    def record_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        protocol: str = "REST",
        client_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Record an API request with timing and status"""
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO api_request_metrics 
                (timestamp, method, path, status_code, latency_ms, protocol, client_id, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (time.time(), method, path, status_code, latency_ms, protocol, client_id, error_message))
            self.db.commit()
    
    def get_api_gateway_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Get aggregated API Gateway metrics for the specified time window.
        
        Returns real data only - no mocks.
        """
        cutoff = time.time() - (window_hours * 3600)
        cursor = self.db.cursor()
        
        # Total requests in window
        cursor.execute("""
            SELECT COUNT(*), AVG(latency_ms), 
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM api_request_metrics 
            WHERE timestamp > ?
        """, (cutoff,))
        total_requests, avg_latency, error_count = cursor.fetchone()
        total_requests = total_requests or 0
        avg_latency = avg_latency or 0.0
        error_count = error_count or 0
        
        # Calculate rates
        requests_per_second = total_requests / (window_hours * 3600) if total_requests > 0 else 0.0
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0
        success_rate = 100.0 - error_rate
        
        # P95 and P99 latency
        cursor.execute("""
            SELECT latency_ms FROM api_request_metrics 
            WHERE timestamp > ?
            ORDER BY latency_ms
        """, (cutoff,))
        latencies = [row[0] for row in cursor.fetchall()]
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
        p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
        
        # Status code distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN status_code < 300 THEN '2xx'
                    WHEN status_code < 400 THEN '3xx'
                    WHEN status_code < 500 THEN '4xx'
                    ELSE '5xx'
                END as status_group,
                COUNT(*) as count
            FROM api_request_metrics
            WHERE timestamp > ?
            GROUP BY status_group
        """, (cutoff,))
        status_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Top endpoints by request count
        cursor.execute("""
            SELECT path, COUNT(*) as requests, AVG(latency_ms) as avg_latency,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate
            FROM api_request_metrics
            WHERE timestamp > ?
            GROUP BY path
            ORDER BY requests DESC
            LIMIT 5
        """, (cutoff,))
        top_endpoints = [
            {
                "path": row[0],
                "requests": row[1],
                "avg_latency": round(row[2], 1),
                "error_rate": round(row[3], 1)
            }
            for row in cursor.fetchall()
        ]
        
        # Protocol distribution
        cursor.execute("""
            SELECT protocol, COUNT(*) as count
            FROM api_request_metrics
            WHERE timestamp > ?
            GROUP BY protocol
        """, (cutoff,))
        protocol_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Calculate trends (compare to previous window)
        prev_cutoff = cutoff - (window_hours * 3600)
        cursor.execute("""
            SELECT COUNT(*), AVG(latency_ms),
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as prev_error_rate
            FROM api_request_metrics 
            WHERE timestamp > ? AND timestamp <= ?
        """, (prev_cutoff, cutoff))
        prev_data = cursor.fetchone()
        prev_requests = prev_data[0] or 0
        prev_latency = prev_data[1] or avg_latency
        prev_error_rate = prev_data[2] or error_rate
        
        requests_trend = ((total_requests - prev_requests) / prev_requests * 100) if prev_requests > 0 else 0.0
        latency_trend = ((avg_latency - prev_latency) / prev_latency * 100) if prev_latency > 0 else 0.0
        error_trend = ((error_rate - prev_error_rate) / prev_error_rate * 100) if prev_error_rate > 0 else 0.0
        
        return {
            "requests_per_second": requests_per_second,
            "avg_response_time": avg_latency,
            "p95_response_time": p95_latency,
            "p99_response_time": p99_latency,
            "error_rate": error_rate,
            "success_rate": success_rate,
            "total_requests_24h": total_requests,
            "status_code_distribution": status_distribution,
            "top_endpoints": top_endpoints,
            "protocol_distribution": protocol_distribution,
            "trends": {
                "requests": requests_trend,
                "latency": latency_trend,
                "error_rate": error_trend
            }
        }
    
    # ==================== Modelservice Metrics ====================
    
    def record_inference(
        self,
        model_name: str,
        inference_time_ms: float,
        tokens_generated: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Record a model inference operation"""
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO modelservice_inference_metrics 
                (timestamp, model_name, inference_time_ms, tokens_generated, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (time.time(), model_name, inference_time_ms, tokens_generated, success, error_message))
            self.db.commit()
    
    def get_modelservice_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated Modelservice metrics"""
        cutoff = time.time() - (window_hours * 3600)
        cursor = self.db.cursor()
        
        # Total inferences and average time
        cursor.execute("""
            SELECT COUNT(*), AVG(inference_time_ms), SUM(tokens_generated)
            FROM modelservice_inference_metrics 
            WHERE timestamp > ?
        """, (cutoff,))
        total_inferences, avg_time, total_tokens = cursor.fetchone()
        total_inferences = total_inferences or 0
        avg_time = (avg_time or 0.0) / 1000.0  # Convert to seconds
        total_tokens = total_tokens or 0
        
        # Tokens per second throughput
        throughput = total_tokens / (window_hours * 3600) if total_tokens > 0 else 0.0
        
        # Active models (models used in last hour)
        recent_cutoff = time.time() - 3600
        cursor.execute("""
            SELECT COUNT(DISTINCT model_name)
            FROM modelservice_inference_metrics 
            WHERE timestamp > ?
        """, (recent_cutoff,))
        active_models = cursor.fetchone()[0] or 0
        
        # Model usage distribution
        cursor.execute("""
            SELECT model_name, COUNT(*) as count
            FROM modelservice_inference_metrics
            WHERE timestamp > ?
            GROUP BY model_name
        """, (cutoff,))
        model_usage = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Latency distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN inference_time_ms < 1000 THEN '0-1s'
                    WHEN inference_time_ms < 2000 THEN '1-2s'
                    WHEN inference_time_ms < 3000 THEN '2-3s'
                    WHEN inference_time_ms < 5000 THEN '3-5s'
                    ELSE '5s+'
                END as bucket,
                COUNT(*) as count
            FROM modelservice_inference_metrics
            WHERE timestamp > ?
            GROUP BY bucket
        """, (cutoff,))
        latency_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Calculate trend
        prev_cutoff = cutoff - (window_hours * 3600)
        cursor.execute("""
            SELECT AVG(inference_time_ms), SUM(tokens_generated)
            FROM modelservice_inference_metrics 
            WHERE timestamp > ? AND timestamp <= ?
        """, (prev_cutoff, cutoff))
        prev_data = cursor.fetchone()
        prev_time = (prev_data[0] or avg_time * 1000) / 1000.0
        prev_tokens = prev_data[1] or total_tokens
        
        time_trend = ((avg_time - prev_time) / prev_time * 100) if prev_time > 0 else 0.0
        throughput_trend = ((total_tokens - prev_tokens) / prev_tokens * 100) if prev_tokens > 0 else 0.0
        
        return {
            "active_models": active_models,
            "inference_throughput": throughput,
            "avg_inference_time": avg_time,
            "total_inferences_24h": total_inferences,
            "model_usage": model_usage,
            "latency_distribution": latency_distribution,
            "trends": {
                "inference_time": time_trend,
                "throughput": throughput_trend
            }
        }
    
    # ==================== Memory System Metrics ====================
    
    def record_memory_query(
        self,
        query_type: str,
        query_time_ms: float,
        results_count: int,
        success: bool = True
    ):
        """Record a memory system query"""
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO memory_query_metrics 
                (timestamp, query_type, query_time_ms, results_count, success)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), query_type, query_time_ms, results_count, success))
            self.db.commit()
    
    def get_memory_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated Memory system metrics"""
        cutoff = time.time() - (window_hours * 3600)
        cursor = self.db.cursor()
        
        # Query rate
        cursor.execute("""
            SELECT COUNT(*) FROM memory_query_metrics WHERE timestamp > ?
        """, (cutoff,))
        total_queries = cursor.fetchone()[0] or 0
        queries_per_second = total_queries / (window_hours * 3600) if total_queries > 0 else 0.0
        
        # Calculate trend
        prev_cutoff = cutoff - (window_hours * 3600)
        cursor.execute("""
            SELECT COUNT(*) FROM memory_query_metrics 
            WHERE timestamp > ? AND timestamp <= ?
        """, (prev_cutoff, cutoff))
        prev_queries = cursor.fetchone()[0] or total_queries
        query_trend = ((total_queries - prev_queries) / prev_queries * 100) if prev_queries > 0 else 0.0
        
        return {
            "queries_per_second": queries_per_second,
            "total_queries_24h": total_queries,
            "trends": {
                "queries": query_trend
            }
        }
    
    # ==================== Scheduler Metrics ====================
    
    def record_scheduler_job(
        self,
        job_type: str,
        queue_name: str,
        duration_ms: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Record a scheduler job execution"""
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO scheduler_job_metrics 
                (timestamp, job_type, queue_name, duration_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (time.time(), job_type, queue_name, duration_ms, success, error_message))
            self.db.commit()
    
    def get_scheduler_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated Scheduler metrics"""
        cutoff = time.time() - (window_hours * 3600)
        cursor = self.db.cursor()
        
        # Job counts and success rate
        cursor.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                   AVG(duration_ms)
            FROM scheduler_job_metrics 
            WHERE timestamp > ?
        """, (cutoff,))
        total_jobs, successes, failures, avg_duration = cursor.fetchone()
        total_jobs = total_jobs or 0
        successes = successes or 0
        failures = failures or 0
        avg_duration = (avg_duration or 0.0) / 1000.0  # Convert to seconds
        
        success_rate = (successes / total_jobs * 100) if total_jobs > 0 else 100.0
        
        # Job type distribution
        cursor.execute("""
            SELECT job_type, COUNT(*) as count
            FROM scheduler_job_metrics
            WHERE timestamp > ?
            GROUP BY job_type
        """, (cutoff,))
        job_type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Queue utilization (jobs per queue)
        cursor.execute("""
            SELECT queue_name, COUNT(*) as count
            FROM scheduler_job_metrics
            WHERE timestamp > ?
            GROUP BY queue_name
        """, (cutoff,))
        queue_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Failed job reasons
        cursor.execute("""
            SELECT error_message, COUNT(*) as count, MAX(timestamp) as last_occurrence
            FROM scheduler_job_metrics
            WHERE timestamp > ? AND success = 0 AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 5
        """, (cutoff,))
        failed_job_reasons = [
            {
                "reason": row[0],
                "count": row[1],
                "last_occurrence": datetime.fromtimestamp(row[2]).isoformat() + "Z"
            }
            for row in cursor.fetchall()
        ]
        
        # Calculate trends
        prev_cutoff = cutoff - (window_hours * 3600)
        cursor.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as prev_success_rate
            FROM scheduler_job_metrics 
            WHERE timestamp > ? AND timestamp <= ?
        """, (prev_cutoff, cutoff))
        prev_data = cursor.fetchone()
        prev_jobs = prev_data[0] or total_jobs
        prev_success_rate = prev_data[1] or success_rate
        
        jobs_trend = ((total_jobs - prev_jobs) / prev_jobs * 100) if prev_jobs > 0 else 0.0
        success_trend = ((success_rate - prev_success_rate) / prev_success_rate * 100) if prev_success_rate > 0 else 0.0
        
        return {
            "jobs_today": total_jobs,
            "success_rate": success_rate,
            "failed_jobs": failures,
            "avg_job_duration": avg_duration,
            "job_type_distribution": job_type_distribution,
            "queue_counts": queue_counts,
            "failed_job_reasons": failed_job_reasons,
            "trends": {
                "jobs": jobs_trend,
                "success_rate": success_trend,
                "failures": ((failures - (prev_jobs - (prev_jobs * prev_success_rate / 100))) / max(1, prev_jobs - (prev_jobs * prev_success_rate / 100)) * 100) if prev_jobs > 0 else 0.0
            }
        }
    
    # ==================== Message Bus Metrics ====================
    
    def record_message_bus_activity(
        self,
        topic: str,
        message_count: int = 1,
        processing_time_ms: Optional[float] = None,
        backlog_depth: Optional[int] = None,
        consumer_count: Optional[int] = None
    ):
        """Record message bus activity"""
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO message_bus_metrics 
                (timestamp, topic, message_count, processing_time_ms, backlog_depth, consumer_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (time.time(), topic, message_count, processing_time_ms, backlog_depth, consumer_count))
            self.db.commit()
    
    def get_message_bus_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated Message Bus metrics"""
        cutoff = time.time() - (window_hours * 3600)
        cursor = self.db.cursor()
        
        # Message rate
        cursor.execute("""
            SELECT SUM(message_count) FROM message_bus_metrics WHERE timestamp > ?
        """, (cutoff,))
        total_messages = cursor.fetchone()[0] or 0
        messages_per_second = total_messages / (window_hours * 3600) if total_messages > 0 else 0.0
        
        # Current backlog (latest value)
        cursor.execute("""
            SELECT SUM(backlog_depth) FROM message_bus_metrics 
            WHERE timestamp > ? AND backlog_depth IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """, (time.time() - 60,))  # Last minute
        backlog_result = cursor.fetchone()
        current_backlog = backlog_result[0] if backlog_result and backlog_result[0] else 0
        
        # Topic count
        cursor.execute("""
            SELECT COUNT(DISTINCT topic) FROM message_bus_metrics WHERE timestamp > ?
        """, (cutoff,))
        topic_count = cursor.fetchone()[0] or 0
        
        # Consumer groups (distinct consumer counts)
        cursor.execute("""
            SELECT COUNT(DISTINCT consumer_count) FROM message_bus_metrics 
            WHERE timestamp > ? AND consumer_count IS NOT NULL
        """, (cutoff,))
        consumer_groups = cursor.fetchone()[0] or 0
        
        # Top topics by message volume
        cursor.execute("""
            SELECT topic, SUM(message_count) as total_messages,
                   AVG(backlog_depth) as avg_backlog,
                   MAX(consumer_count) as consumers
            FROM message_bus_metrics
            WHERE timestamp > ?
            GROUP BY topic
            ORDER BY total_messages DESC
            LIMIT 5
        """, (cutoff,))
        top_topics = [
            {
                "topic": row[0],
                "msg_per_sec": round(row[1] / (window_hours * 3600), 1),
                "backlog": int(row[2] or 0),
                "consumers": int(row[3] or 0)
            }
            for row in cursor.fetchall()
        ]
        
        # Message type distribution (from topic names)
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN topic LIKE 'conversation%' THEN 'conversation'
                    WHEN topic LIKE 'emotion%' THEN 'emotion'
                    WHEN topic LIKE 'memory%' THEN 'memory'
                    WHEN topic LIKE 'agency%' THEN 'agency'
                    WHEN topic LIKE 'logs%' THEN 'logs'
                    ELSE 'other'
                END as message_type,
                SUM(message_count) as count
            FROM message_bus_metrics
            WHERE timestamp > ?
            GROUP BY message_type
        """, (cutoff,))
        message_type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Latency by topic
        cursor.execute("""
            SELECT topic, AVG(processing_time_ms) as avg_latency
            FROM message_bus_metrics
            WHERE timestamp > ? AND processing_time_ms IS NOT NULL
            GROUP BY topic
        """, (cutoff,))
        latency_by_topic = {row[0]: round(row[1], 1) for row in cursor.fetchall()}
        
        # Calculate trends
        prev_cutoff = cutoff - (window_hours * 3600)
        cursor.execute("""
            SELECT SUM(message_count) FROM message_bus_metrics 
            WHERE timestamp > ? AND timestamp <= ?
        """, (prev_cutoff, cutoff))
        prev_messages = cursor.fetchone()[0] or total_messages
        messages_trend = ((total_messages - prev_messages) / prev_messages * 100) if prev_messages > 0 else 0.0
        
        return {
            "messages_per_second": messages_per_second,
            "backlog_depth": current_backlog,
            "topic_count": topic_count,
            "consumer_groups": consumer_groups,
            "top_topics": top_topics,
            "message_type_distribution": message_type_distribution,
            "latency_by_topic": latency_by_topic,
            "trends": {
                "messages": messages_trend,
                "backlog": 0.0  # Would need historical backlog tracking
            }
        }
    
    # ==================== Cleanup ====================
    
    def cleanup_old_metrics(self, days_to_keep: int = 7):
        """Remove metrics older than specified days"""
        cutoff = time.time() - (days_to_keep * 86400)
        with self.lock:
            cursor = self.db.cursor()
            for table in [
                "api_request_metrics",
                "modelservice_inference_metrics",
                "memory_query_metrics",
                "scheduler_job_metrics",
                "message_bus_metrics"
            ]:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
            self.db.commit()
            logger.info(f"Cleaned up metrics older than {days_to_keep} days")
