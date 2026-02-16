"""
System Health Metrics Endpoint

Provides overall system health metrics including:
- Health score (0-100)
- Component status
- Resource utilization (CPU, memory, disk)
- System uptime
- Active sessions
- Overall throughput and error rates

Aggregates metrics from all subsystems.
"""

import time
import os
import psutil
from fastapi import APIRouter, HTTPException

from ..models import SystemHealthMetrics
from ..influx_client import MetricsInfluxClient
from aico.core.logging import get_logger

# Import start_time from shared module to avoid circular imports
from backend.api.metrics.start_time import start_time

logger = get_logger("backend.api.metrics.system")

router = APIRouter()


@router.get("/system", response_model=SystemHealthMetrics)
async def get_system_health_metrics():
    """Get overall system health metrics."""
    try:
        with MetricsInfluxClient() as client:
            # Calculate backend uptime using the same start_time as topology page
            uptime_seconds = int(time.time() - start_time)
            
            # Get resource utilization
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Aggregate metrics from all subsystems
            gateway_rps = client.count_points("api_request", "-1m", {"service": "aico-backend"}) / 60.0
            gateway_errors = client.count_points("api_request", "-1m", {"service": "aico-backend", "status_class": "5xx"})
            gateway_total = client.count_points("api_request", "-1m", {"service": "aico-backend"})
            system_error_rate = (gateway_errors / gateway_total * 100) if gateway_total > 0 else 0.0
            
            avg_latency = client.mean_field("api_request", "latency_ms_f", "-1m", {"service": "aico-backend"}) or 0.0
            
            # Calculate component health scores from real metrics
            # API Gateway: Based on error rate (80%) and response time (20%)
            # Latency penalty: 0-500ms = no penalty, 500-2000ms = linear penalty, >2000ms = max penalty
            gateway_success_rate = ((gateway_total - gateway_errors) / gateway_total * 100) if gateway_total > 0 else 100.0
            latency_penalty = max(0, min((avg_latency - 500) / 15, 100))  # 500ms = 0%, 2000ms = 100% penalty
            gateway_health = min(100, int(gateway_success_rate * 0.8 + (100 - latency_penalty) * 0.2))
            
            # Modelservice: Based on LLM success rate (default 100% if no data)
            llm_success = client.count_points_by_field("model_inference", "success_b", True, "-5m", {"service": "aico-backend"})
            llm_total = client.count_points("model_inference", "-5m", {"service": "aico-backend"})
            modelservice_health = int((llm_success / llm_total * 100) if llm_total > 0 else 100.0)
            
            # Memory: Based on query success rate (default 100% if no data)
            memory_success = client.count_points_by_field("memory_query", "success_b", True, "-5m", {"service": "aico-backend"})
            memory_total = client.count_points("memory_query", "-5m", {"service": "aico-backend"})
            memory_health = int((memory_success / memory_total * 100) if memory_total > 0 else 100.0)
            
            # Scheduler: Based on job success rate (default 100% if no data)
            # Count only success_b field to avoid double-counting (InfluxDB stores each field separately)
            scheduler_success = client.count_points_by_field("scheduler_job", "success_b", True, "-5m", {"service": "aico-backend"})
            scheduler_total = client.count_field_points("scheduler_job", "success_b", "-5m", {"service": "aico-backend"})
            logger.debug(f"Scheduler metrics: success={scheduler_success}, total={scheduler_total}")
            scheduler_health = int((scheduler_success / scheduler_total * 100) if scheduler_total > 0 else 100.0)
            
            # Message Bus: Based on backlog depth (lower is better)
            msg_backlog = client.mean_field("messagebus_event", "backlog_depth_i", "-1m") or 0
            messagebus_health = max(0, min(100, int(100 - (msg_backlog / 10))))  # 0 backlog = 100%, 1000+ backlog = 0%
            
            # Calculate overall health score (weighted average)
            health_components = {
                "API Gateway": gateway_health,
                "Modelservice": modelservice_health,
                "Memory": memory_health,
                "Scheduler": scheduler_health,
                "Message Bus": messagebus_health,
            }
            health_score = int(sum(health_components.values()) / len(health_components))
            
            # Component status with health percentages and detailed explanations
            component_status = {}
            
            # API Gateway explanation
            gateway_explanation = []
            if gateway_total == 0:
                gateway_explanation.append("No requests in last minute")
            else:
                if gateway_errors > 0:
                    gateway_explanation.append(f"{gateway_errors}/{gateway_total} requests failed (5xx errors)")
                if avg_latency > 500:
                    gateway_explanation.append(f"High latency: {avg_latency:.0f}ms avg (target: <500ms)")
                if not gateway_explanation:
                    gateway_explanation.append("All requests successful, latency normal")
            
            component_status["API Gateway"] = {
                "status": "healthy" if gateway_health > 90 else "warning" if gateway_health > 75 else "critical",
                "health": f"{gateway_health}%",
                "explanation": " • ".join(gateway_explanation)
            }
            
            # Modelservice explanation
            modelservice_explanation = []
            if llm_total == 0:
                modelservice_explanation.append("No inference requests in last 5 minutes")
            else:
                llm_failures = llm_total - llm_success
                if llm_failures > 0:
                    modelservice_explanation.append(f"{llm_failures}/{llm_total} inference requests failed")
                else:
                    modelservice_explanation.append("All inference requests successful")
            
            component_status["Modelservice"] = {
                "status": "healthy" if modelservice_health > 90 else "warning" if modelservice_health > 75 else "critical",
                "health": f"{modelservice_health}%",
                "explanation": " • ".join(modelservice_explanation)
            }
            
            # Memory explanation
            memory_explanation = []
            if memory_total == 0:
                memory_explanation.append("No memory queries in last 5 minutes")
            else:
                memory_failures = memory_total - memory_success
                if memory_failures > 0:
                    memory_explanation.append(f"{memory_failures}/{memory_total} memory queries failed")
                else:
                    memory_explanation.append("All memory queries successful")
            
            component_status["Memory"] = {
                "status": "healthy" if memory_health > 90 else "warning" if memory_health > 75 else "critical",
                "health": f"{memory_health}%",
                "explanation": " • ".join(memory_explanation)
            }
            
            # Scheduler explanation
            scheduler_explanation = []
            if scheduler_total == 0:
                scheduler_explanation.append("No scheduled jobs executed in last 5 minutes")
            else:
                scheduler_failures = scheduler_total - scheduler_success
                if scheduler_failures > 0:
                    scheduler_explanation.append(f"{scheduler_failures}/{scheduler_total} scheduled jobs failed")
                else:
                    scheduler_explanation.append("All scheduled jobs completed successfully")
            
            component_status["Scheduler"] = {
                "status": "healthy" if scheduler_health > 90 else "warning" if scheduler_health > 75 else "critical",
                "health": f"{scheduler_health}%",
                "explanation": " • ".join(scheduler_explanation)
            }
            
            # Message Bus explanation
            messagebus_explanation = []
            if msg_backlog == 0:
                messagebus_explanation.append("No message backlog")
            elif msg_backlog < 100:
                messagebus_explanation.append(f"Low backlog: {int(msg_backlog)} messages queued")
            elif msg_backlog < 500:
                messagebus_explanation.append(f"Moderate backlog: {int(msg_backlog)} messages queued")
            else:
                messagebus_explanation.append(f"High backlog: {int(msg_backlog)} messages queued (investigate slow consumers)")
            
            component_status["Message Bus"] = {
                "status": "healthy" if messagebus_health > 90 else "warning" if messagebus_health > 75 else "critical",
                "health": f"{messagebus_health}%",
                "explanation": " • ".join(messagebus_explanation)
            }
            
            # Calculate real queue backlog from message bus
            queue_backlog = int(msg_backlog)
            
            import os
            from pathlib import Path
            storage_size_mb = 0.0
            try:
                data_dir = Path.home() / "Library" / "Application Support" / "aico" / "data"
                if data_dir.exists():
                    for file in data_dir.rglob("*"):
                        if file.is_file():
                            storage_size_mb += file.stat().st_size / (1024 * 1024)
            except Exception:
                pass
            
            # Count critical alerts and warnings
            critical_alerts = sum(1 for score in health_components.values() if score < 75)
            warnings = sum(1 for score in health_components.values() if 75 <= score <= 90)
            
            return SystemHealthMetrics(
                health_score=health_score,
                component_status=component_status,
                cpu_percent=round(cpu_percent, 2),
                memory_percent=round(memory_percent, 2),
                disk_percent=round(disk_percent, 2),
                uptime_seconds=uptime_seconds,
                active_sessions=0,  # TODO: Implement session tracking
                total_throughput=round(gateway_rps, 2),
                system_error_rate=round(system_error_rate, 2),
                avg_latency_ms=round(avg_latency, 2),
                queue_backlog=queue_backlog,
                storage_size_mb=round(storage_size_mb, 2),
                critical_alerts=critical_alerts,
                warnings=warnings
            )
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.debug(f"InfluxDB query failed (likely no data yet), returning zero metrics: {e}")
        
        # Return empty/zero metrics
        return SystemHealthMetrics(
            health_score=100,
            component_status={},
            cpu_percent=0.0,
            memory_percent=0.0,
            disk_percent=0.0,
            uptime_seconds=0,
            active_sessions=0,
            total_throughput=0.0,
            system_error_rate=0.0,
            avg_latency_ms=0.0,
            queue_backlog=0,
            storage_size_mb=0.0,
            critical_alerts=0,
            warnings=0
        )
