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

# Fix Windows asyncio event loop compatibility with ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import AICO modules
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger, initialize_logging

# Initialize logging first before importing any modules that use loggers
config_manager = ConfigurationManager()
initialize_logging(config_manager)

from core.lifecycle_manager import BackendLifecycleManager

# Import version from shared version system
from aico.core.version import get_backend_version
__version__ = get_backend_version()

# Global components - config_manager already initialized above
logger = get_logger("backend", "main")
process_manager = None
shutdown_event = asyncio.Event()

try:
    # Configuration already initialized above
    config_manager.initialize(lightweight=False)
    
    # Initialize process manager AFTER logging is set up
    from aico.core.process import ProcessManager
    process_manager = ProcessManager("gateway")
    process_manager.write_pid(os.getpid())
    
    
    # Lifecycle manager already imported above
    
except Exception as e:
    print(f"Initialization error: {e}")
    sys.exit(1)


async def setup_backend_components():
    """Setup backend components using new lifecycle manager"""
    # Create shared database connection
    from aico.security import AICOKeyManager
    from aico.core.paths import AICOPaths
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    
    key_manager = AICOKeyManager(config_manager)
    paths = AICOPaths()
    db_path = paths.resolve_database_path("aico.db")
    
    # Get encryption key
    cached_key = key_manager._get_cached_session()
    if cached_key:
        key_manager._extend_session()
        db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
    else:
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        else:
            raise RuntimeError("Master key not found. Run 'aico security setup' to initialize.")
    
    shared_db_connection = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    logger.info("Created shared database connection")
    
    # Create and initialize lifecycle manager with service container
    lifecycle_manager = BackendLifecycleManager(config_manager)
    
    # Create FastAPI app using lifecycle manager
    app = await lifecycle_manager.startup()
    logger.info("Backend lifecycle manager initialized")
    
    return app, lifecycle_manager


# Removed unused create_app function - replaced by lifecycle manager




async def main():
    """Run the application using lifecycle manager"""
    logger.info("Starting AICO Backend with lifecycle manager...")
    
    # Setup backend components using lifecycle manager
    app, lifecycle_manager = await setup_backend_components()
    
    # Get server configuration
    core_config = config_manager.config_cache.get('core', {})
    api_gateway_config = core_config.get('api_gateway', {})
    rest_config = api_gateway_config.get('rest', {})
    
    host = rest_config.get('host', '127.0.0.1')
    port = rest_config.get('port', 8771)
    
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        lifespan="on",
        access_log=False
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
    print("[*] AICO Backend Server")
    print("="*60)
    print(f"[>] Server: http://{host}:{port}")
    print(f"[>] Environment: {os.getenv('AICO_ENV', 'development')}")
    print(f"[>] Service Container: {len(lifecycle_manager.container._definitions)} services")
    print(f"[>] Plugins: Active plugins will be shown after startup")
    print("="*60)
    print("[+] Starting server... (Press Ctrl+C to stop)\n")
    
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
        print("[+] Shutdown complete.")
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[MAIN] Application error: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        sys.exit(1)
