#!/usr/bin/env python3
"""
AICO Backend Server - Clean Implementation Following REFACTOR_SUMMARY.md

This implements the proper architecture:
- Main FastAPI Backend (port 8771): Handles ALL REST API endpoints
- API Gateway provides FastAPI integration via setup_fastapi_integration()
- WebSocket and ZeroMQ adapters run on separate ports
"""

import asyncio
import os
import sys
import signal
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Fix Windows asyncio event loop compatibility with ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import AICO modules
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger, initialize_logging
from api_gateway.gateway_v2 import AICOAPIGatewayV2

__version__ = "0.5.0"

# Global components
config_manager = None
logger = None
process_manager = None
shutdown_event = asyncio.Event()
background_tasks = set()  # Track all background tasks for cleanup

try:
    # Initialize configuration and logging
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=False)
    initialize_logging(config_manager)
    logger = get_logger("backend", "main")
    
    # Initialize process manager AFTER logging is set up
    from aico.core.process import ProcessManager
    process_manager = ProcessManager("gateway")
    process_manager.write_pid(os.getpid())
    
    
    # Import API Gateway after logging is initialized
    from api_gateway.gateway_v2 import AICOAPIGatewayV2
    
except Exception as e:
    print(f"Initialization error: {e}")
    sys.exit(1)


async def setup_backend_components():
    """Setup backend components following proper architecture"""
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
    
    # Create and initialize API Gateway first (starts message bus)
    api_gateway = AICOAPIGatewayV2(config_manager, db_connection=shared_db_connection)
    await api_gateway.start()
    logger.info("API Gateway initialized")
    
    # Initialize Task Scheduler
    from backend.scheduler import TaskScheduler, TaskStore
    task_scheduler = TaskScheduler(config_manager, shared_db_connection)
    await task_scheduler.start()
    logger.info("Task Scheduler initialized and started")
    
    # Log consumer is already started by the API Gateway plugin system
    # No need to start it separately here
    
    return api_gateway, task_scheduler, shared_db_connection


def create_app():
    """Create FastAPI app with proper lifespan management"""
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        # Startup
        from aico.core.paths import AICOPaths
        paths = AICOPaths()
        shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
        if shutdown_file.exists():
            shutdown_file.unlink()

        # Initialize logging
        logger = get_logger("backend", "service")
        logger.info("Starting AICO Backend Server...")
        
        # Set debug print mode based on detach setting
        from backend.log_consumer import set_foreground_mode
        is_foreground = os.getenv('AICO_DETACH_MODE') == 'false'
        set_foreground_mode(is_foreground)
        if is_foreground:
            logger.info("Running in foreground mode - debug output enabled")
        logger.info(f"Starting AICO backend server v{__version__}")
        api_gateway, task_scheduler, shared_db_connection = await setup_backend_components()
        
        # Create UserService with shared DB connection
        from aico.data.user import UserService
        user_service = UserService(shared_db_connection)
        
        # Store components in app state
        app.state.gateway = api_gateway
        app.state.task_scheduler = task_scheduler
        app.state.db_connection = shared_db_connection
        app.state.user_service = user_service
        
        # Skip FastAPI integration to avoid middleware timing issues
        # Routes will be handled directly by the health endpoint below
        logger.info("Backend components initialized - LogConsumer active")
        
        # TODO: The heartbeat test logging is deprecated and will be removed.
        # It was used for initial diagnostics and is no longer needed.
        # # Heartbeat test logs
        # hb_logger = get_logger("backend", "heartbeat")
        # # hb_logger.info(
        # #     "[HEARTBEAT TEST] Synchronous emit at startup",
        # #     extra={
        # #         "event_type": "heartbeat_test",
        # #         "sequence": 0,
        # #         "source": "backend.main",
        # #     },
        # # )

        # async def _emit_heartbeat_logs():
        #     try:
        #         for i in range(1, 4):
        #             hb_logger.info(
        #                 f"[HEARTBEAT TEST] Emitting heartbeat log {i}/3",
        #                 extra={
        #                     "event_type": "heartbeat_test",
        #                     "sequence": i,
        #                     "source": "backend.main",
        #                 },
        #             )
        #             await asyncio.sleep(1.0)
        #     except Exception as e:
        #         print(f"[HEARTBEAT TEST] Error emitting heartbeat logs: {e}")

        # heartbeat_task = asyncio.create_task(_emit_heartbeat_logs())
        # heartbeat_task.set_name("heartbeat_logs")
        # background_tasks.add(heartbeat_task)
        # app.state.heartbeat_task = heartbeat_task

        async def watch_for_shutdown_file():
            """On Windows, watch for a shutdown file to trigger graceful exit."""
            from aico.core.paths import AICOPaths
            paths = AICOPaths()
            shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
            while True:
                if shutdown_file.exists():
                    logger.info("Shutdown file detected, initiating graceful shutdown.")
                    try:
                        shutdown_file.unlink()
                    except OSError:
                        pass
                    # Set server.should_exit = True. Uvicorn's main loop checks this flag
                    # and initiates a graceful shutdown. This is the simplest and most reliable
                    # way to programmatically stop the server without signals or deadlocks.
                    if hasattr(app.state, 'server'):
                        app.state.server.should_exit = True
                        logger.info("server.should_exit set to True. Uvicorn will now shut down.")
                    else:
                        logger.error("Server instance not found in app.state. Cannot initiate shutdown.")
                    break
                await asyncio.sleep(1)

        # On Windows, use a file watcher for reliable shutdown from 'aico gateway stop'
        # This should only run in detached mode to avoid affecting foreground sessions.
        is_detached = os.getenv('AICO_DETACH_MODE', 'false') == 'true'
        if sys.platform == "win32":
            logger.info("Starting shutdown file watcher for detached mode on Windows.")
            shutdown_watcher_task = asyncio.create_task(watch_for_shutdown_file())
            shutdown_watcher_task.set_name("shutdown_watcher")
            app.state.shutdown_watcher_task = shutdown_watcher_task
        
        yield
        
        # Shutdown - cleanup async resources
        logger.info("Initiating graceful shutdown of backend components...")
        
        # Cancel all background tasks first
        logger.info("Cancelling background tasks...")
        for task in list(background_tasks):
            if not task.done():
                logger.info(f"Cancelling task: {task.get_name()}")
                task.cancel()
                try:
                    # Give tasks a moment to cancel, but don't wait forever.
                    await asyncio.wait_for(task, timeout=2.0)
                    logger.info(f"Task {task.get_name()} cancelled successfully.")
                except asyncio.CancelledError:
                    logger.info(f"Task {task.get_name()} was already cancelled.")
                except asyncio.TimeoutError:
                    logger.warning(f"Task {task.get_name()} did not cancel within 2 seconds.")
        background_tasks.clear()
        logger.info("All background tasks processed.")
        
        # Stop scheduler first
        if hasattr(app.state, 'task_scheduler'):
            logger.info("Stopping task scheduler...")
            await app.state.task_scheduler.stop()
            logger.info("Task scheduler stopped.")
        
        # Stop gateway components
        if hasattr(app.state, 'gateway'):
            logger.info("Stopping API Gateway...")
            await app.state.gateway.stop()
            logger.info("API Gateway stopped.")

        # Finally, cancel the shutdown watcher if it exists
        if hasattr(app.state, 'shutdown_watcher_task') and not app.state.shutdown_watcher_task.done():
            logger.info("Cancelling shutdown watcher task...")
            app.state.shutdown_watcher_task.cancel()
            try:
                await app.state.shutdown_watcher_task
            except asyncio.CancelledError:
                logger.info("Shutdown watcher task cancelled successfully.")
        
        logger.info("All components stopped gracefully.")
    
    # Create FastAPI app with lifespan
    fastapi_app = FastAPI(
        title="AICO Backend API",
        version=__version__,
        description="AICO Backend REST API with plugin-based middleware",
        lifespan=app_lifespan
    )
    
    # Add basic health endpoint
    @fastapi_app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy", "service": "aico-backend", "version": __version__}
    
    # Add echo router directly
    from backend.api.echo import router as echo_router
    fastapi_app.include_router(echo_router, prefix="/api/v1/echo", tags=["echo"])
    
    # Add scheduler router
    from backend.api.scheduler.router import router as scheduler_router
    fastapi_app.include_router(scheduler_router, prefix="/api/v1/scheduler", tags=["scheduler"])
    
    # Add logs router
    from backend.api.logs.router import router as logs_router
    fastapi_app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
    
    # Add users router
    from backend.api.users.router import router as users_router
    fastapi_app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    
    # Add admin router
    from backend.api.admin.router import router as admin_router
    fastapi_app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    
    # Add encryption middleware as ASGI middleware wrapper
    from fastapi import Request
    
    # Add simple request logging middleware
    @fastapi_app.middleware("http")
    async def log_requests(request: Request, call_next):
        if request.url.path == "/api/v1/users/authenticate":
            logger.info(f"FastAPI received request: {request.method} {request.url.path}")
            body = await request.body()
            logger.info(f"FastAPI request body length: {len(body)} bytes")
        response = await call_next(request)
        if request.url.path == "/api/v1/users/authenticate":
            logger.info(f"FastAPI response status: {response.status_code}")
            if hasattr(response, 'body'):
                logger.info(f"FastAPI response body: {response.body}")
        return response
    from backend.api_gateway.middleware.encryption import EncryptionMiddleware
    from aico.security.key_manager import AICOKeyManager
    from aico.core.config import ConfigurationManager
    
    # Initialize encryption middleware components
    config_manager = ConfigurationManager()
    config_manager.initialize()
    key_manager = AICOKeyManager(config_manager)
    
    # Wrap FastAPI app with encryption middleware
    app = EncryptionMiddleware(fastapi_app, key_manager)
    
    # Skip FastAPI integration to avoid middleware timing issues
    # Focus on keeping LogConsumer alive for log persistence
    # Handshake endpoint is now handled by the encryption middleware automatically
    
    return fastapi_app, app




async def main():
    """Run the application with robust signal handling."""
    # Create the app (components will be initialized in lifespan)
    fastapi_app, asgi_app = create_app()
    
    # Get server configuration
    core_config = config_manager.config_cache.get('core', {})
    api_gateway_config = core_config.get('api_gateway', {})
    rest_config = api_gateway_config.get('rest', {})
    
    host = rest_config.get('host', '127.0.0.1')
    port = rest_config.get('port', 8771)
    
    config = uvicorn.Config(
        asgi_app,
        host=host,
        port=port,
        log_level="info",
        lifespan="on",
        access_log=False
    )
    server = uvicorn.Server(config)

    # This is the key for cross-platform graceful shutdown.
    # We manually install signal handlers to tell the server to exit.
    # This works reliably on both Windows and Unix.
    def handle_exit(sig, frame):
        logger.warning(f"Received signal {sig}, shutting down.")
        shutdown_event.set()  # Trigger our application's shutdown logic
        server.handle_exit(sig, frame)  # Trigger uvicorn's shutdown

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Store server instance in app state to allow programmatic shutdown
    fastapi_app.state.server = server

    print("[MAIN] Starting uvicorn server...")
    try:
        await server.serve()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Server operation was cancelled.")
    finally:
        if process_manager:
            process_manager.cleanup_pid_files()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[MAIN] Application error: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        sys.exit(1)
