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
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from fastapi import FastAPI
from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger
from aico.core.version import get_backend_version

__version__ = get_backend_version()

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
    
    # Start log consumer after API Gateway (which starts the message bus)
    from log_consumer import AICOLogConsumer
    log_consumer = AICOLogConsumer(config_manager, db_connection=shared_db_connection)
    await log_consumer.start()
    logger.info("Log consumer started")
    
    return api_gateway, log_consumer, shared_db_connection


async def main():
    """Main function following REFACTOR_SUMMARY.md architecture"""
    logger.info(f"Starting AICO backend server v{__version__}")
    
    # Setup backend components
    api_gateway, log_consumer, shared_db_connection = await setup_backend_components()
    
    # Create FastAPI app
    app = FastAPI(
        title="AICO Backend API",
        version=__version__,
        description="AICO Backend REST API with plugin-based middleware"
    )
    
    # Setup FastAPI integration with API Gateway (REFACTOR_SUMMARY.md pattern)
    api_gateway.setup_fastapi_integration(app)
    logger.info("FastAPI integration setup complete")
    
    # Add basic health endpoint
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy", "service": "aico-backend", "version": __version__}
    
    return app


async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler"""
    # Startup
    try:
        print("[MAIN] Starting lifespan startup...")
        # Initialize and start API Gateway
        print("[MAIN] Creating APIGateway instance...")
        gateway = APIGateway()
        print("[MAIN] Starting gateway...")
        await gateway.start()
        
        # Store gateway reference for shutdown
        app.state.gateway = gateway
        
        print("[MAIN] Backend startup complete")
        logger.info("Backend startup complete")
        yield
        
    except Exception as e:
        print(f"[MAIN] Failed to start backend: {e}")
        import traceback
        print(f"[MAIN] Traceback: {traceback.format_exc()}")
        logger.error(f"Failed to start backend: {e}")
        raise
    
    # Shutdown
    try:
        print("[MAIN] Starting shutdown...")
        if hasattr(app.state, 'gateway'):
            await app.state.gateway.stop()
        print("[MAIN] Backend shutdown complete")
        logger.info("Backend shutdown complete")
    except Exception as e:
        print(f"[MAIN] Error during shutdown: {e}")
        logger.error(f"Error during shutdown: {e}")
        sys.exit(1)


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
