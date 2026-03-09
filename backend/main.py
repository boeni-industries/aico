#!/usr/bin/env python3
"""
AICO Backend Server - Clean Implementation with Service Container

Refactored architecture:
- Service container for dependency injection
- BackendLifecycleManager for clean FastAPI integration
- Standardized plugin base classes
- Proper lifecycle management
"""

import asyncio
import os
import sys
import signal
import uvicorn
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


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

# Import AICO modules
from aico.core.config import ConfigurationManager
from aico.core.config_validation import validate_startup_config, print_config_summary
from aico.core.logging import initialize_logging, get_logger, shutdown_logging
from aico.core.fs_guard import enable_fs_guard

# Initialize backend-specific logging first before importing any modules that use loggers
config_manager = ConfigurationManager()
_require_container_data_dir()
initialize_logging(service_name="backend", enable_loki=True, enable_console=True)

enable_fs_guard()

# Explicitly initialize configuration before validation to avoid implicit initialization
# (and file watcher startup) during validate_startup_config().
config_manager.initialize(lightweight=False)

# Validate startup configuration
validate_startup_config(config_manager)
print_config_summary(config_manager)

from core.lifecycle_manager import BackendLifecycleManager

# Import version from shared version system
from aico.core.version import get_backend_version
__version__ = get_backend_version()

# Global components - config_manager already initialized above
logger = get_logger("backend.main")
shutdown_event = asyncio.Event()

# Lifecycle manager already imported above


async def setup_backend_components():
    """Setup backend components using new lifecycle manager"""
    # PostgreSQL connection handled by UnitOfWork pattern
    # No shared database connection needed - each request gets its own UnitOfWork
    logger.info("Backend using PostgreSQL with UnitOfWork pattern - no shared connection needed")
    
    # Create and initialize lifecycle manager with explicit role.
    # Monolith mode is removed; this entrypoint runs the HTTP gateway.
    lifecycle_manager = BackendLifecycleManager(config_manager, role="gateway")
    
    # Create FastAPI app using lifecycle manager
    app = await lifecycle_manager.startup()
    logger.info("Backend lifecycle manager initialized")
    
    return app, lifecycle_manager

async def main():
    """Run the application using lifecycle manager"""
    logger.info("Starting AICO Backend with lifecycle manager...")
    
    # Setup backend components using lifecycle manager
    app, lifecycle_manager = await setup_backend_components()
    
    # Get server configuration
    host = config_manager.get("api_gateway.rest.host", "127.0.0.1")
    port = config_manager.get("api_gateway.rest.port", 8771)
    
    # The lifecycle manager already handles all service registration internally
    # No manual service registration needed here
    
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        lifespan="on",
        access_log=False,
        log_config=None  # Disable Uvicorn's logging config to prevent it from shutting down our handlers
    )
    server = uvicorn.Server(config)

    # Setup shutdown file monitoring
    from aico.core.paths import AICOPaths
    paths = AICOPaths()
    shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
    
    async def monitor_shutdown_file():
        """Monitor for shutdown file to enable graceful CLI stop"""
        while not shutdown_event.is_set():
            if shutdown_file.exists():
                logger.info("Shutdown file detected, initiating graceful shutdown")
                shutdown_file.unlink()  # Clean up shutdown file
                shutdown_event.set()
                server.should_exit = True
                break
            await asyncio.sleep(0.5)

    # Signal handling for graceful shutdown
    def handle_exit(sig, frame):
        logger.warning(f"Received signal {sig}, shutting down.")
        shutdown_event.set()
        server.handle_exit(sig, frame)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Beautiful cross-platform startup display
    print("\n" + "="*60)
    print("🚀 AICO Backend Server")
    print("="*60)
    print(f"✓ Server: http://{host}:{port}")
    print(f"✓ Environment: {os.getenv('AICO_ENV', 'development')}")
    if hasattr(lifecycle_manager, 'container') and hasattr(lifecycle_manager.container, '_definitions'):
        print(f"✓ Services: {len(lifecycle_manager.container._definitions)} registered")
    print("="*60)
    print("✅ STARTUP COMPLETE - Server ready to accept connections")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    try:
        # Start shutdown file monitoring task
        shutdown_monitor_task = asyncio.create_task(monitor_shutdown_file())
        
        await server.serve()
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[-] Graceful shutdown initiated...")
        logger.info("Server operation was cancelled.")
    finally:
        # Cancel shutdown monitor
        if 'shutdown_monitor_task' in locals():
            shutdown_monitor_task.cancel()
            try:
                await shutdown_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop lifecycle manager
        print("[~] Stopping services...")
        await lifecycle_manager.stop()
        if process_manager:
            process_manager.cleanup_pid_files()
        
        # Shutdown logging system (flush and close InfluxDB handler)
        print("[~] Shutting down logging system...")
        shutdown_logging()
        
        print("[+] Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[MAIN] Application error: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        sys.exit(1)
