import asyncio
import subprocess
from datetime import datetime

import httpx

from aico.core.bus import MessageBusClient
from aico.core.logging import get_logger
from aico.core.version import get_backend_version, get_modelservice_version
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from core.services.runtime_info import format_uptime, start_time
from core.services.version_detector import get_version_detector

logger = get_logger("core.services.operations_topology_service")


async def _probe_http(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except Exception:
        return False


async def _detect_deployment_type() -> str:
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return "docker-compose"
    except Exception:
        pass

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            container_names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if any(name.startswith("aico-") for name in container_names):
                return "docker"
    except Exception:
        pass

    return "unknown"


async def get_operations_topology() -> dict:
    backend_version = get_backend_version()
    modelservice_version = get_modelservice_version()
    deployment_type = await _detect_deployment_type()

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

    gateway_status = "healthy" if await _probe_http("http://localhost:8771/health") else "offline"

    studio_port = 3002 if await _probe_http("http://localhost:3002/") else 3000
    studio_status = "healthy" if await _probe_http(f"http://localhost:{studio_port}/") else "offline"

    modelservice_status = "offline"
    try:
        from core.services import get_modelservice_client
        from aico.core.config import ConfigurationManager

        config = ConfigurationManager()
        modelservice_client = get_modelservice_client(config)
        health_data = await modelservice_client.get_health()
        if health_data and health_data.get("success"):
            modelservice_status = "healthy"
    except Exception:
        pass

    postgres_status = "offline"
    try:
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            if hasattr(uow, "user_profiles"):
                await uow.user_profiles.list(limit=1)
        postgres_status = "healthy"
    except Exception:
        pass

    nats_status = "offline"
    try:
        client = MessageBusClient("operations_topology_probe")
        await client.connect()
        await client.disconnect()
        nats_status = "healthy"
    except Exception:
        pass

    loki_status = "healthy" if await _probe_http("http://localhost:3100/ready") else "offline"
    grafana_status = "healthy" if await _probe_http("http://localhost:3001/api/health") else "offline"

    core_status = "healthy" if backend_uptime_str != "N/A" else "unknown"
    scheduler_status = core_status

    services = [
        {"id": "gateway", "name": "API Gateway", "type": "gateway", "status": gateway_status, "version": backend_version, "host": "localhost", "port": 8771, "uptime": backend_uptime_str},
        {"id": "core", "name": "Backend Core", "type": "backend", "status": core_status, "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
        {"id": "studio", "name": "Studio", "type": "studio", "status": studio_status, "version": "unknown", "host": "localhost", "port": studio_port, "uptime": "N/A"},
        {"id": "modelservice", "name": "Model Service", "type": "modelservice", "status": modelservice_status, "version": modelservice_version, "host": "localhost", "port": 11434, "uptime": modelservice_uptime_str},
        {"id": "scheduler", "name": "Task Scheduler", "type": "scheduler", "status": scheduler_status, "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
        {"id": "nats", "name": "NATS", "type": "bus", "status": nats_status, "version": "unknown", "host": "localhost", "port": 4222, "uptime": "N/A"},
        {"id": "loki", "name": "Loki", "type": "logs", "status": loki_status, "version": "unknown", "host": "localhost", "port": 3100, "uptime": "N/A"},
        {"id": "grafana", "name": "Grafana", "type": "dashboard", "status": grafana_status, "version": "unknown", "host": "localhost", "port": 3001, "uptime": "N/A"},
        {"id": "postgresql", "name": "PostgreSQL", "type": "database", "status": postgres_status, "version": db_versions.get("PostgreSQL", "unknown"), "host": "localhost", "port": 5432, "uptime": postgres_uptime_str},
        {"id": "minio", "name": "MinIO", "type": "database", "status": minio_status, "version": minio_version, "host": "localhost", "port": 9000, "uptime": minio_uptime_str},
    ]
    connections = [
        {"from_service": "studio", "to_service": "gateway", "protocol": "HTTP/WebSocket", "status": "active" if studio_status == "healthy" and gateway_status == "healthy" else "degraded"},
        {"from_service": "gateway", "to_service": "nats", "protocol": "NATS", "status": "active" if gateway_status == "healthy" and nats_status == "healthy" else "degraded"},
        {"from_service": "nats", "to_service": "core", "protocol": "NATS", "status": "active" if nats_status == "healthy" and core_status == "healthy" else "degraded"},
        {"from_service": "core", "to_service": "nats", "protocol": "NATS", "status": "active" if nats_status == "healthy" and core_status == "healthy" else "degraded"},
        {"from_service": "core", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active" if core_status == "healthy" and postgres_status == "healthy" else "degraded"},
        {"from_service": "core", "to_service": "minio", "protocol": "S3", "status": "active" if core_status == "healthy" and minio_status == "healthy" else "degraded"},
        {"from_service": "core", "to_service": "modelservice", "protocol": "ZMQ", "status": "active" if core_status == "healthy" and modelservice_status == "healthy" else "degraded"},
        {"from_service": "core", "to_service": "loki", "protocol": "HTTP", "status": "active" if core_status == "healthy" and loki_status == "healthy" else "degraded"},
        {"from_service": "grafana", "to_service": "loki", "protocol": "HTTP", "status": "active" if grafana_status == "healthy" and loki_status == "healthy" else "degraded"},
        {"from_service": "grafana", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active" if grafana_status == "healthy" and postgres_status == "healthy" else "degraded"},
    ]
    return {"services": services, "connections": connections, "deployment_type": deployment_type}
