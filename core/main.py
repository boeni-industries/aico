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

# Add the parent directory to Python path to import core modules
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

from core.services.core_lifecycle_manager import CoreLifecycleManager


config_manager = ConfigurationManager()
_require_container_data_dir()
initialize_logging(service_name="core", enable_loki=True, enable_console=True)
enable_fs_guard()
config_manager.initialize(lightweight=False)
validate_startup_config(config_manager, service="core")
print_config_summary(config_manager)

logger = get_logger("core.main")
shutdown_event = asyncio.Event()


async def main():
    logger.info("Starting AICO Core service...")

    lifecycle_manager = CoreLifecycleManager(config_manager)
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
