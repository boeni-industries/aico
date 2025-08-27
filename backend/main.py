#!/usr/bin/env python3
"""
AICO Backend Server - Clean Implementation Following REFACTOR_SUMMARY.md

This implements the proper architecture:
- Main FastAPI Backend (port 8771): Handles ALL REST API endpoints
- API Gateway provides FastAPI integration via setup_fastapi_integration()
- WebSocket and ZeroMQ adapters run on separate ports
"""

import asyncio
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
shutdown_event = asyncio.Event()

try:
    # Initialize configuration and logging
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=False)
    initialize_logging(config_manager)
    logger = get_logger("backend", "main")
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
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
    
    # Log consumer is already started by the API Gateway plugin system
    # No need to start it separately here
    
    return api_gateway, None, shared_db_connection


async def main():
    """Main function following REFACTOR_SUMMARY.md architecture"""
    logger.info(f"Starting AICO backend server v{__version__}")
    
    # Setup backend components
    api_gateway, log_consumer, shared_db_connection = await setup_backend_components()
    
    # Create FastAPI app with lifespan
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        # Startup - gateway already integrated in main()
        print("[LIFESPAN] App startup - gateway already integrated")

        # Synchronous heartbeat log to immediately test logging
        hb_logger = get_logger("backend", "heartbeat")
        hb_logger.info(
            "[HEARTBEAT TEST] Synchronous emit at startup",
            extra={
                "event_type": "heartbeat_test",
                "sequence": 0,
                "source": "backend.main",
            },
        )

        # Heartbeat: emit 3 prominent log messages through normal logging paths (ZMQ -> DB)
        async def _emit_heartbeat_logs():
            try:
                hb_logger = get_logger("backend", "heartbeat")
                for i in range(1, 4):
                    hb_logger.info(
                        f"[HEARTBEAT TEST] Emitting heartbeat log {i}/3",
                        extra={
                            "event_type": "heartbeat_test",
                            "sequence": i,
                            "source": "backend.main",
                        },
                    )
                    await asyncio.sleep(1.0)
            except Exception as e:
                # Ensure any issues are visible on console
                print(f"[HEARTBEAT TEST] Error emitting heartbeat logs: {e}")

        # Schedule the heartbeat on the running server loop so it survives return from main()
        app.state.heartbeat_task = asyncio.create_task(_emit_heartbeat_logs())
        yield
        # Shutdown
        print("[LIFESPAN] App shutdown - stopping gateway")
        if hasattr(app.state, 'gateway'):
            await app.state.gateway.stop()
    
    app = FastAPI(
        title="AICO Backend API",
        version=__version__,
        description="AICO Backend REST API with plugin-based middleware",
        lifespan=app_lifespan
    )
    
    # NOTE: Request logging middleware intentionally disabled.
    # Function-based HTTP middleware can intercept before ASGI middleware
    # and may interfere with encryption enforcement/logging. The REST
    # adapter and unified logging already provide sufficient visibility.
    
    # Setup FastAPI integration with API Gateway (REFACTOR_SUMMARY.md pattern)
    print("[DEBUG MAIN] About to call api_gateway.setup_fastapi_integration()")
    print(f"[DEBUG MAIN] api_gateway object: {api_gateway}")
    print(f"[DEBUG MAIN] api_gateway type: {type(api_gateway)}")
    try:
        api_gateway.setup_fastapi_integration(app)
        print("[DEBUG MAIN] setup_fastapi_integration() completed successfully")
        logger.info("FastAPI integration setup complete")
    except Exception as e:
        print(f"[DEBUG MAIN] ERROR in setup_fastapi_integration(): {e}")
        logger.error(f"FastAPI integration setup failed: {e}")
        raise
    
    # Store gateway in app state for lifespan management
    app.state.gateway = api_gateway
    print("[DEBUG MAIN] Stored gateway in app.state")
    
    # Add basic health endpoint
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy", "service": "aico-backend", "version": __version__}
    
    return app




if __name__ == "__main__":
    """Start the server when run directly"""
    try:
        # Get the app from main()
        app = asyncio.run(main())
        
        # Get server configuration
        core_config = config_manager.config_cache.get('core', {})
        api_gateway_config = core_config.get('api_gateway', {})
        rest_config = api_gateway_config.get('rest', {})
        
        host = rest_config.get('host', '127.0.0.1')
        port = rest_config.get('port', 8771)
        
        print("[MAIN] Starting uvicorn server...")
        
        # Start uvicorn server with proper app reference
        import uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        sys.exit(1)
        sys.exit(1)
