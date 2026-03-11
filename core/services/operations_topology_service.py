import asyncio
import subprocess
from datetime import datetime

from aico.core.logging import get_logger
from aico.core.version import get_backend_version, get_modelservice_version
from core.services.runtime_info import format_uptime, start_time
from core.services.version_detector import get_version_detector

logger = get_logger("core.services.operations_topology_service")


async def get_operations_topology() -> dict:
    backend_version = get_backend_version()
    modelservice_version = get_modelservice_version()

    version_detector = get_version_detector()
    db_versions = await version_detector.get_all_versions()

    backend_uptime_str = "N/A"
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-core"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            started_at = datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
            uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
            backend_uptime_str = format_uptime(uptime_seconds)
    except Exception:
        backend_uptime_str = format_uptime(max(0.0, datetime.now().timestamp() - start_time))

    modelservice_uptime_str = "N/A"
    try:
        from core.services import get_modelservice_client
        from aico.core.config import ConfigurationManager

        config = ConfigurationManager()
        modelservice_client = get_modelservice_client(config)
        health_data = await modelservice_client.get_health()
        if health_data and health_data.get("success") and health_data.get("uptime_seconds"):
            modelservice_uptime_str = format_uptime(health_data["uptime_seconds"])
    except Exception:
        pass

    postgres_uptime_str = "N/A"
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-postgres"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            started_at = datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
            uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
            postgres_uptime_str = format_uptime(uptime_seconds)
    except Exception:
        pass

    minio_status = "offline"
    minio_version = "unknown"
    minio_uptime_str = "N/A"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:9000/minio/health/live")
            if response.status_code == 200:
                minio_status = "healthy"
    except Exception:
        pass

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "exec", "aico-minio", "minio", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            version_line = result.stdout.strip()
            if "RELEASE" in version_line:
                timestamp = version_line.split("RELEASE.")[1].split()[0] if len(version_line.split("RELEASE.")) > 1 else ""
                minio_version = timestamp.split("T")[0] if timestamp and "T" in timestamp else (timestamp or "unknown")
    except Exception:
        pass

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-minio"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            started_at = datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
            uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
            minio_uptime_str = format_uptime(uptime_seconds)
    except Exception:
        pass

    services = [
        {"id": "gateway", "name": "API Gateway", "type": "gateway", "status": "healthy", "version": backend_version, "host": "localhost", "port": 8771, "uptime": backend_uptime_str},
        {"id": "core", "name": "Backend Core", "type": "backend", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
        {"id": "studio", "name": "Studio", "type": "studio", "status": "healthy", "version": "N/A", "host": "localhost", "port": 3000, "uptime": "N/A"},
        {"id": "modelservice", "name": "Model Service", "type": "modelservice", "status": "healthy", "version": modelservice_version, "host": "localhost", "port": 11434, "uptime": modelservice_uptime_str},
        {"id": "scheduler", "name": "Task Scheduler", "type": "scheduler", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
        {"id": "nats", "name": "NATS", "type": "bus", "status": "healthy", "version": "2.10", "host": "localhost", "port": 4222, "uptime": "N/A"},
        {"id": "loki", "name": "Loki", "type": "logs", "status": "healthy", "version": "2.9.0", "host": "localhost", "port": 3100, "uptime": "N/A"},
        {"id": "grafana", "name": "Grafana", "type": "dashboard", "status": "healthy", "version": "12.1", "host": "localhost", "port": 3001, "uptime": "N/A"},
        {"id": "postgresql", "name": "PostgreSQL", "type": "database", "status": "healthy", "version": db_versions.get("PostgreSQL", "18.1"), "host": "localhost", "port": 5432, "uptime": postgres_uptime_str},
        {"id": "minio", "name": "MinIO", "type": "database", "status": minio_status, "version": minio_version, "host": "localhost", "port": 9000, "uptime": minio_uptime_str},
    ]
    connections = [
        {"from_service": "studio", "to_service": "gateway", "protocol": "HTTP/WebSocket", "status": "active"},
        {"from_service": "gateway", "to_service": "nats", "protocol": "NATS", "status": "active"},
        {"from_service": "nats", "to_service": "core", "protocol": "NATS", "status": "active"},
        {"from_service": "core", "to_service": "nats", "protocol": "NATS", "status": "active"},
        {"from_service": "core", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
        {"from_service": "core", "to_service": "minio", "protocol": "S3", "status": "active"},
        {"from_service": "core", "to_service": "modelservice", "protocol": "ZMQ", "status": "active"},
        {"from_service": "core", "to_service": "loki", "protocol": "HTTP", "status": "active"},
        {"from_service": "grafana", "to_service": "loki", "protocol": "HTTP", "status": "active"},
        {"from_service": "grafana", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
    ]
    return {"services": services, "connections": connections, "deployment_type": "docker-compose"}
