"""
OpenTelemetry to InfluxDB Exporter

Exports OpenTelemetry metrics directly to InfluxDB using the line protocol.
This replaces the SQLite-based OTelStorageExporter and implements the schema
defined in shared/aico/data/influx/schema.lp with 100% fidelity.

Design Principles:
- Direct InfluxDB writes via HTTP API (line protocol)
- Exact schema.lp compliance (measurements, tags, fields, types)
- Efficient batch writes
- Thread-safe operations
- Automatic tag derivation (status_class, etc.)
- Resource attributes → global tags (service, deployment, host, version)
"""

import time
import logging
import socket
from typing import Optional, Sequence, Dict, Any, List
from threading import Lock
from datetime import datetime

from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricsData,
    MetricExportResult,
)

logger = logging.getLogger("backend.otel_influx")


class OTelInfluxExporter(MetricExporter):
    """
    MetricExporter that writes OpenTelemetry metrics to InfluxDB.
    
    Implements the exact schema defined in shared/aico/data/influx/schema.lp:
    - Measurements: api_request, model_inference, memory_query, scheduler_job, messagebus_event
    - Tags: service, deployment, host, version, plus metric-specific tags
    - Fields: with type suffixes (_f, _i, _s, _b)
    """
    
    def __init__(
        self,
        influx_url: str = "http://127.0.0.1:8086",
        org: str = "aico",
        bucket: str = "aico_telemetry",
        token: Optional[str] = None,
        resource_attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        
        self.influx_url = influx_url.rstrip("/")
        self.org = org
        self.bucket = bucket
        self.token = token
        self.resource_attributes = resource_attributes or {}
        self.lock = Lock()
        
        # Extract global tags from resource attributes
        self.global_tags = self._extract_global_tags()
        
        # Build write API URL
        self.write_url = f"{self.influx_url}/api/v2/write?org={self.org}&bucket={self.bucket}&precision=ns"
        
        logger.info(f"OTelInfluxExporter initialized: {self.influx_url} (org={self.org}, bucket={self.bucket})")
    
    def _extract_global_tags(self) -> Dict[str, str]:
        """Extract global tags from OTel resource attributes."""
        tags = {}
        
        # Map OTel resource attributes to schema.lp global tags
        # service.name → service
        if "service.name" in self.resource_attributes:
            tags["service"] = str(self.resource_attributes["service.name"])
        
        # deployment.environment → deployment
        if "deployment.environment" in self.resource_attributes:
            tags["deployment"] = str(self.resource_attributes["deployment.environment"])
        
        # host.name → host (fallback to socket.gethostname())
        if "host.name" in self.resource_attributes:
            tags["host"] = str(self.resource_attributes["host.name"])
        else:
            try:
                tags["host"] = socket.gethostname()
            except Exception:
                tags["host"] = "unknown"
        
        # service.version → version (optional)
        if "service.version" in self.resource_attributes:
            tags["version"] = str(self.resource_attributes["service.version"])
        
        # service.instance.id → instance (optional)
        if "service.instance.id" in self.resource_attributes:
            tags["instance"] = str(self.resource_attributes["service.instance.id"])
        
        return tags
    
    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """
        Export metrics to InfluxDB.
        
        This is called periodically by the PeriodicExportingMetricReader.
        We parse the metrics and write them as line protocol to InfluxDB.
        """
        if not metrics_data or not metrics_data.resource_metrics:
            return MetricExportResult.SUCCESS
        
        with self.lock:
            try:
                # Collect all line protocol lines
                lines: List[str] = []
                
                for resource_metric in metrics_data.resource_metrics:
                    for scope_metric in resource_metric.scope_metrics:
                        for metric in scope_metric.metrics:
                            metric_lines = self._process_metric(metric)
                            lines.extend(metric_lines)
                
                if not lines:
                    return MetricExportResult.SUCCESS
                
                # Write batch to InfluxDB
                success = self._write_to_influx(lines)
                
                return MetricExportResult.SUCCESS if success else MetricExportResult.FAILURE
                
            except Exception as e:
                logger.error(f"Failed to export metrics to InfluxDB: {e}", exc_info=True)
                return MetricExportResult.FAILURE
    
    def _process_metric(self, metric) -> List[str]:
        """Process a single OTel metric and convert to line protocol."""
        metric_name = metric.name
        
        # Route metric to appropriate measurement based on name
        if metric_name.startswith("aico.api."):
            return self._process_api_metric(metric)
        elif metric_name.startswith("aico.modelservice."):
            return self._process_modelservice_metric(metric)
        elif metric_name.startswith("aico.memory."):
            return self._process_memory_metric(metric)
        elif metric_name.startswith("aico.scheduler."):
            return self._process_scheduler_metric(metric)
        elif metric_name.startswith("aico.messagebus."):
            return self._process_messagebus_metric(metric)
        else:
            # Unknown metric - skip
            return []
    
    def _process_api_metric(self, metric) -> List[str]:
        """
        Process API Gateway metrics → api_request measurement.
        
        Schema (from schema.lp):
        - Measurement: api_request
        - Tags: service, deployment, host, version, method, path, protocol, category, status_class
        - Fields: status_code_i, latency_ms_f, request_body_b, response_size_i, error_message_s
        """
        lines = []
        
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.api.request.duration":
                # Extract histogram data (sum/count for average)
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count == 0:
                        continue
                    
                    avg_latency_seconds = data_point.sum / data_point.count
                    latency_ms = avg_latency_seconds * 1000
                    
                    # Build tags (global + metric-specific)
                    tags = dict(self.global_tags)
                    
                    # Metric-specific tags (rename from OTel conventions)
                    method = attributes.get('http.method', 'GET')
                    path = attributes.get('http.target', '/')
                    protocol = attributes.get('http.scheme', 'HTTP').upper()
                    category = attributes.get('category', 'other')
                    status_code = attributes.get('http.status_code', 200)
                    
                    # Derive status_class from status_code
                    status_class = self._derive_status_class(status_code)
                    
                    tags['method'] = method
                    tags['path'] = path
                    tags['protocol'] = protocol
                    tags['category'] = category
                    tags['status_class'] = status_class
                    
                    # Build fields (with type suffixes)
                    fields = {
                        'status_code_i': f"{status_code}i",
                        'latency_ms_f': f"{latency_ms:.2f}",
                    }
                    
                    # Optional fields
                    if 'request.body' in attributes:
                        fields['request_body_b'] = 'true' if attributes['request.body'] else 'false'
                    
                    if 'response.size' in attributes:
                        fields['response_size_i'] = f"{attributes['response.size']}i"
                    
                    if 'error.message' in attributes:
                        # Escape and quote string field
                        error_msg = str(attributes['error.message']).replace('"', '\\"')
                        fields['error_message_s'] = f'"{error_msg}"'
                    
                    # Build line protocol
                    timestamp_ns = data_point.time_unix_nano
                    line = self._build_line_protocol('api_request', tags, fields, timestamp_ns)
                    lines.append(line)
        
        return lines
    
    def _process_modelservice_metric(self, metric) -> List[str]:
        """
        Process Modelservice metrics → model_inference measurement.
        
        Schema (from schema.lp):
        - Measurement: model_inference
        - Tags: service, deployment, host, version, model_name, task_type, provider
        - Fields: duration_ms_f, tokens_generated_i, prompt_tokens_i, entities_count_i,
                  entity_types_s, confidence_score_f, sentiment_result_s, ttft_ms_f,
                  success_b, error_message_s
        """
        lines = []
        
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.modelservice.inference.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count == 0:
                        continue
                    
                    avg_time_seconds = data_point.sum / data_point.count
                    duration_ms = avg_time_seconds * 1000
                    
                    # Build tags
                    tags = dict(self.global_tags)
                    tags['model_name'] = attributes.get('model.name', 'unknown')
                    tags['task_type'] = attributes.get('task.type', 'unknown')
                    tags['provider'] = attributes.get('provider', 'unknown')
                    
                    # Build fields
                    fields = {
                        'duration_ms_f': f"{duration_ms:.2f}",
                        'success_b': 'true' if attributes.get('success', True) else 'false',
                    }
                    
                    # Optional fields
                    if 'tokens.generated' in attributes:
                        fields['tokens_generated_i'] = f"{attributes['tokens.generated']}i"
                    
                    if 'prompt.tokens' in attributes:
                        fields['prompt_tokens_i'] = f"{attributes['prompt.tokens']}i"
                    
                    if 'entities.count' in attributes:
                        fields['entities_count_i'] = f"{attributes['entities.count']}i"
                    
                    if 'entity.types' in attributes:
                        entity_types = str(attributes['entity.types']).replace('"', '\\"')
                        fields['entity_types_s'] = f'"{entity_types}"'
                    
                    if 'confidence.score' in attributes:
                        fields['confidence_score_f'] = f"{attributes['confidence.score']:.4f}"
                    
                    if 'sentiment.result' in attributes:
                        sentiment = str(attributes['sentiment.result']).replace('"', '\\"')
                        fields['sentiment_result_s'] = f'"{sentiment}"'
                    
                    if 'ttft' in attributes:
                        fields['ttft_ms_f'] = f"{attributes['ttft']:.2f}"
                    
                    if 'error.message' in attributes:
                        error_msg = str(attributes['error.message']).replace('"', '\\"')
                        fields['error_message_s'] = f'"{error_msg}"'
                    
                    timestamp_ns = data_point.time_unix_nano
                    line = self._build_line_protocol('model_inference', tags, fields, timestamp_ns)
                    lines.append(line)
        
        return lines
    
    def _process_memory_metric(self, metric) -> List[str]:
        """
        Process Memory system metrics → memory_query measurement.
        
        Schema (from schema.lp):
        - Measurement: memory_query
        - Tags: service, deployment, host, version, query_type
        - Fields: query_time_ms_f, results_count_i, success_b
        """
        lines = []
        
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.memory.query.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count == 0:
                        continue
                    
                    avg_time_seconds = data_point.sum / data_point.count
                    query_time_ms = avg_time_seconds * 1000
                    
                    tags = dict(self.global_tags)
                    tags['query_type'] = attributes.get('query.type', 'unknown')
                    
                    fields = {
                        'query_time_ms_f': f"{query_time_ms:.2f}",
                        'results_count_i': f"{attributes.get('results.count', 0)}i",
                        'success_b': 'true' if attributes.get('success', True) else 'false',
                    }
                    
                    timestamp_ns = data_point.time_unix_nano
                    line = self._build_line_protocol('memory_query', tags, fields, timestamp_ns)
                    lines.append(line)
        
        return lines
    
    def _process_scheduler_metric(self, metric) -> List[str]:
        """
        Process Scheduler metrics → scheduler_job measurement.
        
        Schema (from schema.lp):
        - Measurement: scheduler_job
        - Tags: service, deployment, host, version, job_type, queue_name
        - Fields: duration_ms_f, success_b, error_message_s
        """
        lines = []
        
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.scheduler.job.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count == 0:
                        continue
                    
                    avg_time_seconds = data_point.sum / data_point.count
                    duration_ms = avg_time_seconds * 1000
                    
                    tags = dict(self.global_tags)
                    tags['job_type'] = attributes.get('job.type', 'unknown')
                    tags['queue_name'] = attributes.get('queue.name', 'default')
                    
                    fields = {
                        'duration_ms_f': f"{duration_ms:.2f}",
                        'success_b': 'true' if attributes.get('success', True) else 'false',
                    }
                    
                    if 'error.message' in attributes:
                        error_msg = str(attributes['error.message']).replace('"', '\\"')
                        fields['error_message_s'] = f'"{error_msg}"'
                    
                    timestamp_ns = data_point.time_unix_nano
                    line = self._build_line_protocol('scheduler_job', tags, fields, timestamp_ns)
                    lines.append(line)
        
        return lines
    
    def _process_messagebus_metric(self, metric) -> List[str]:
        """
        Process Message Bus metrics → messagebus_event measurement.
        
        Schema (from schema.lp):
        - Measurement: messagebus_event
        - Tags: service, deployment, host, version, topic
        - Fields: message_count_i, processing_time_ms_f, backlog_depth_i, consumer_count_i
        """
        lines = []
        
        for data_point in metric.data.data_points:
            attributes = dict(data_point.attributes) if data_point.attributes else {}
            
            if metric.name == "aico.messagebus.message.duration":
                if hasattr(data_point, 'sum') and hasattr(data_point, 'count'):
                    if data_point.count == 0:
                        continue
                    
                    avg_time_seconds = data_point.sum / data_point.count
                    processing_time_ms = avg_time_seconds * 1000
                    
                    tags = dict(self.global_tags)
                    tags['topic'] = attributes.get('topic', 'unknown')
                    
                    fields = {
                        'message_count_i': f"{data_point.count}i",
                        'processing_time_ms_f': f"{processing_time_ms:.2f}",
                        'backlog_depth_i': f"{attributes.get('backlog.depth', 0)}i",
                        'consumer_count_i': f"{attributes.get('consumer.count', 0)}i",
                    }
                    
                    timestamp_ns = data_point.time_unix_nano
                    line = self._build_line_protocol('messagebus_event', tags, fields, timestamp_ns)
                    lines.append(line)
        
        return lines
    
    def _derive_status_class(self, status_code: int) -> str:
        """Derive status_class tag from HTTP status code."""
        if 200 <= status_code < 300:
            return "2xx"
        elif 300 <= status_code < 400:
            return "3xx"
        elif 400 <= status_code < 500:
            return "4xx"
        elif 500 <= status_code < 600:
            return "5xx"
        else:
            return "other"
    
    def _build_line_protocol(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, str],
        timestamp_ns: int
    ) -> str:
        """
        Build InfluxDB line protocol string.
        
        Format: measurement,tag1=value1,tag2=value2 field1=value1,field2=value2 timestamp
        """
        # Escape special characters in tags and measurement
        measurement = self._escape_measurement(measurement)
        tag_str = ",".join(f"{self._escape_tag_key(k)}={self._escape_tag_value(v)}" for k, v in sorted(tags.items()))
        field_str = ",".join(f"{self._escape_field_key(k)}={v}" for k, v in fields.items())
        
        return f"{measurement},{tag_str} {field_str} {timestamp_ns}"
    
    def _escape_measurement(self, s: str) -> str:
        """Escape measurement name."""
        return s.replace(",", "\\,").replace(" ", "\\ ")
    
    def _escape_tag_key(self, s: str) -> str:
        """Escape tag key."""
        return s.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
    
    def _escape_tag_value(self, s: str) -> str:
        """Escape tag value."""
        return s.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
    
    def _escape_field_key(self, s: str) -> str:
        """Escape field key."""
        return s.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
    
    def _write_to_influx(self, lines: List[str]) -> bool:
        """Write line protocol batch to InfluxDB via HTTP API."""
        if not lines:
            return True
        
        try:
            import requests
            
            # Join lines with newline
            payload = "\n".join(lines)
            
            # Build headers
            headers = {
                "Content-Type": "text/plain; charset=utf-8",
            }
            
            if self.token:
                headers["Authorization"] = f"Token {self.token}"
            
            # Write to InfluxDB
            response = requests.post(
                self.write_url,
                data=payload.encode('utf-8'),
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 204:
                logger.debug(f"Successfully wrote {len(lines)} points to InfluxDB")
                return True
            else:
                logger.error(f"InfluxDB write failed: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}", exc_info=True)
            return False
    
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shutdown the exporter."""
        logger.info("OTelInfluxExporter shutting down")
    
    def force_flush(self, timeout_millis: float = 10_000, **kwargs) -> bool:
        """Force flush any pending metrics."""
        logger.debug("OTelInfluxExporter force flush")
        return True
