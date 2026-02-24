#!/usr/bin/env python3
"""AICO Core Service.

Runs internal domain services (conversation engine, scheduler, emotion engine, etc.)
without exposing an HTTP interface. Communicates via NATS.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from aico.core.config import ConfigurationManager
from aico.core.config_validation import validate_startup_config, print_config_summary
from aico.core.logging import initialize_logging, get_logger, shutdown_logging

from core.lifecycle_manager import BackendLifecycleManager


config_manager = ConfigurationManager()
initialize_logging(service_name="core", enable_loki=True, enable_console=True)
config_manager.initialize(lightweight=False)
validate_startup_config(config_manager, service="backend")
print_config_summary(config_manager)

logger = get_logger("backend.core_main")
shutdown_event = asyncio.Event()


async def main():
    logger.info("Starting AICO Core service...")

    lifecycle_manager = BackendLifecycleManager(config_manager, role="core")
    await lifecycle_manager.startup()

    from aico.core.paths import AICOPaths
    paths = AICOPaths()
    shutdown_file = paths.get_runtime_path() / "core.shutdown"

    async def monitor_shutdown_file():
        while not shutdown_event.is_set():
            if shutdown_file.exists():
                logger.info("Shutdown file detected, initiating graceful shutdown")
                shutdown_file.unlink()
                shutdown_event.set()
                break
            await asyncio.sleep(0.5)

    def handle_exit(sig, frame):
        logger.warning(f"Received signal {sig}, shutting down.")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    monitor_task = asyncio.create_task(monitor_shutdown_file())
    try:
        while not shutdown_event.is_set():
            await asyncio.sleep(1.0)
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        await lifecycle_manager.stop()
        shutdown_logging()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
