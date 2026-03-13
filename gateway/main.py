#!/usr/bin/env python3
"""AICO Gateway Server (HTTP edge).

Runs the FastAPI API gateway only. Core domain services run in a separate process
(`core/main.py`) and communicate via NATS.
"""

import asyncio
import os
import signal
import sys
import uvicorn
from pathlib import Path

# Add the parent directory to Python path to import gateway and core modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def _is_running_in_docker() -> bool:
    if os.getenv("AICO_DOCKER", "").strip() in {"1", "true", "yes"}:
        return True
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists() and "docker" in cgroup.read_text(encoding="utf-8", errors="ignore"):
            return True
    except Exception:
        pass
    return False


def _require_container_data_dir() -> None:
    if not _is_running_in_docker():
        return
    data_dir = os.getenv("AICO_DATA_DIR")
    if not data_dir or not data_dir.strip():
        raise SystemExit(
            "FATAL: Running in Docker but AICO_DATA_DIR is not set. "
            "Set AICO_DATA_DIR to a mounted volume path (e.g. /var/lib/aico)."
        )

from aico.core.config import ConfigurationManager
from aico.core.config_validation import validate_startup_config, print_config_summary
from aico.core.logging import initialize_logging, get_logger, shutdown_logging
from aico.core.fs_guard import enable_fs_guard

from gateway.core.gateway_core import GatewayCore


config_manager = ConfigurationManager()
_require_container_data_dir()
initialize_logging(service_name="gateway", enable_loki=True, enable_console=True)
enable_fs_guard()
config_manager.initialize(lightweight=False)
validate_startup_config(config_manager, service="gateway")
print_config_summary(config_manager)

logger = get_logger("gateway.main")
shutdown_event = asyncio.Event()


async def setup_gateway_components():
    logger.info("Gateway using PostgreSQL with UnitOfWork pattern - no shared connection needed")
    gateway_core = GatewayCore(config_manager)
    app = await gateway_core.start()
    logger.info("Gateway core initialized")
    return app, gateway_core


async def main():
    logger.info("Starting AICO Gateway (HTTP edge)...")

    app, gateway_core = await setup_gateway_components()

    host = config_manager.get("api_gateway.rest.host", "127.0.0.1")
    port = config_manager.get("api_gateway.rest.port", 8771)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        lifespan="on",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)

    from aico.core.paths import AICOPaths
    paths = AICOPaths()
    shutdown_file = paths.get_runtime_path() / "gateway.shutdown"

    async def monitor_shutdown_file():
        while not shutdown_event.is_set():
            if shutdown_file.exists():
                logger.info("Shutdown file detected, initiating graceful shutdown")
                shutdown_file.unlink()
                shutdown_event.set()
                server.should_exit = True
                break
            await asyncio.sleep(0.5)

    def handle_exit(sig, frame):
        logger.warning(f"Received signal {sig}, shutting down.")
        shutdown_event.set()
        server.handle_exit(sig, frame)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        shutdown_monitor_task = asyncio.create_task(monitor_shutdown_file())
        await server.serve()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Server operation was cancelled.")
    finally:
        if 'shutdown_monitor_task' in locals():
            shutdown_monitor_task.cancel()
            try:
                await shutdown_monitor_task
            except asyncio.CancelledError:
                pass

        await gateway_core.stop()
        shutdown_logging()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
