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


def create_app():
    """Create FastAPI app with proper lifespan management"""
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        # Startup - initialize components in uvicorn's event loop
        logger.info(f"Starting AICO backend server v{__version__}")
        api_gateway, _, shared_db_connection = await setup_backend_components()
        
        # Store components in app state
        app.state.gateway = api_gateway
        app.state.db_connection = shared_db_connection
        
        # Skip FastAPI integration to avoid middleware timing issues
        # Routes will be handled directly by the health endpoint below
        logger.info("Backend components initialized - LogConsumer active")
        
        # Heartbeat test logs
        hb_logger = get_logger("backend", "heartbeat")
        hb_logger.info(
            "[HEARTBEAT TEST] Synchronous emit at startup",
            extra={
                "event_type": "heartbeat_test",
                "sequence": 0,
                "source": "backend.main",
            },
        )

        async def _emit_heartbeat_logs():
            try:
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
                print(f"[HEARTBEAT TEST] Error emitting heartbeat logs: {e}")

        app.state.heartbeat_task = asyncio.create_task(_emit_heartbeat_logs())
        
        yield
        
        # Shutdown - cleanup async resources
        print("[LIFESPAN] App shutdown - stopping gateway")
        if hasattr(app.state, 'gateway'):
            await app.state.gateway.stop()
        if hasattr(app.state, 'heartbeat_task'):
            app.state.heartbeat_task.cancel()
    
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
    from backend.api.echo.router import router as echo_router
    fastapi_app.include_router(echo_router, prefix="/api/v1/echo", tags=["echo"])
    
    # Add encryption middleware as ASGI middleware wrapper
    from fastapi import Request
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
    
    return app




if __name__ == "__main__":
    """Start the server when run directly"""
    try:
        # Create the app (components will be initialized in lifespan)
        app = create_app()
        
        # Get server configuration
        core_config = config_manager.config_cache.get('core', {})
        api_gateway_config = core_config.get('api_gateway', {})
        rest_config = api_gateway_config.get('rest', {})
        
        host = rest_config.get('host', '127.0.0.1')
        port = rest_config.get('port', 8771)
        
        print("[MAIN] Starting uvicorn server...")
        
        # Start uvicorn server - it will handle the async lifecycle via lifespan
        import uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("[MAIN] Application interrupted by user")
    except Exception as e:
        print(f"[MAIN] Application error: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        sys.exit(1)
