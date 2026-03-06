#!/usr/bin/env python3
"""AICO Gateway Server (HTTP edge).

Runs the FastAPI API gateway only. Core domain services run in a separate process
(`backend/core_main.py`) and communicate via NATS.
"""

import asyncio
import os
import signal
import sys
import uvicorn
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from aico.core.config import ConfigurationManager
from aico.core.config_validation import validate_startup_config, print_config_summary
from aico.core.logging import initialize_logging, get_logger, shutdown_logging
from aico.core.fs_guard import enable_fs_guard

from core.lifecycle_manager import BackendLifecycleManager


config_manager = ConfigurationManager()
initialize_logging(service_name="gateway", enable_loki=True, enable_console=True)
enable_fs_guard()
config_manager.initialize(lightweight=False)
validate_startup_config(config_manager, service="backend")
print_config_summary(config_manager)

logger = get_logger("backend.gateway_main")
shutdown_event = asyncio.Event()


async def setup_gateway_components():
    logger.info("Gateway using PostgreSQL with UnitOfWork pattern - no shared connection needed")
    lifecycle_manager = BackendLifecycleManager(config_manager, role="gateway")
    app = await lifecycle_manager.startup()
    logger.info("Gateway lifecycle manager initialized")
    return app, lifecycle_manager


async def main():
    logger.info("Starting AICO Gateway (HTTP edge)...")

    app, lifecycle_manager = await setup_gateway_components()

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

        await lifecycle_manager.stop()
        shutdown_logging()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
