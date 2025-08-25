import asyncio
import os
import sys
import signal
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path


# Fix ZeroMQ compatibility on Windows - must be set before any ZMQ imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Shared modules now available via editable install - no manual path manipulation needed

try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("FastAPI imports successful")

    # Shared modules now installed via UV editable install
    from aico.core.logging import initialize_logging, get_logger
    from aico.core.config import ConfigurationManager
    print("AICO core imports successful")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Import version from VERSIONS file
from aico.core.version import get_backend_version
__version__ = get_backend_version()

# Initialize configuration FIRST
try:
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=True)
    print("Configuration manager initialized")

    # Initialize logging system - will use bootstrap buffering until message bus is ready
    initialize_logging(config_manager)
    print("Logging system initialized")
except Exception as e:
    print(f"Configuration/logging error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Now we can safely get loggers
try:
    logger = get_logger("backend", "main")
    print("Logger initialized")

    # Register signal handlers EARLY - before any blocking operations
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"Signal handler called with signal {signum}")
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers immediately
    if sys.platform != "win32":
        # Unix-like systems
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    else:
        # Windows
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    logger.info("Signal handlers registered for graceful shutdown")
    print("Signal handlers registered")

    # Import API Gateway AFTER logging is initialized
    from api_gateway.models.core.gateway import AICOAPIGateway
    print("API Gateway imported successfully")

    # Import Message Bus Host
    from message_bus_host import AICOMessageBusHost
    print("Message Bus Host imported")
except Exception as e:
    print(f"Logger/import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Global instances (config_manager already initialized above)
message_bus_host = None
api_gateway = None
rest_adapter_app = None
shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan event handler"""
    global config_manager, message_bus_host, api_gateway
    
    # Startup
    try:
        logger.info("Starting AICO backend server in gateway mode")
        
        logger.info("AICO backend server starting up", extra={
            "version": __version__,
            "component": "fastapi_server"
        })
        
        # Initialize configuration
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=False)
        logger.info("Configuration system initialized")
        
        # Update logger factory with full configuration
        from aico.core.logging import _logger_factory
        if _logger_factory:
            _logger_factory.config = config_manager
        
        # Start message bus host (now non-blocking with threaded proxy)
        logger.info("Starting message bus host...")
        message_bus_host = AICOMessageBusHost()
        logger.info("Message bus host created, calling start()...")
        await message_bus_host.start()
        logger.info("Message bus host started")
        
        # Create shared database connection for both LogConsumer and UserService
        shared_db_connection = None
        try:
            # Create single encrypted database connection
            from aico.security import AICOKeyManager
            from aico.core.paths import AICOPaths
            from aico.data.libsql.encrypted import EncryptedLibSQLConnection
            
            key_manager = AICOKeyManager(config_manager)
            paths = AICOPaths()
            db_path = paths.resolve_database_path("aico.db")
            
            # Get encryption key (handle case where no master key is set up yet)
            cached_key = key_manager._get_cached_session()
            if cached_key:
                key_manager._extend_session()
                db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            else:
                import keyring
                stored_key = keyring.get_password(key_manager.service_name, "master_key")
                logger.info(f"Keyring lookup: service_name='{key_manager.service_name}', stored_key={'[FOUND]' if stored_key else '[NOT FOUND]'}")
                if stored_key:
                    master_key = bytes.fromhex(stored_key)
                    db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
                else:
                    logger.error(f"No master key found in keyring for service '{key_manager.service_name}'")
                    raise RuntimeError("Master key not found. Run 'aico security setup' to initialize.")
            
            shared_db_connection = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
            logger.info("Created shared database connection for LogConsumer and UserService")
            
        except Exception as e:
            logger.error(f"Failed to create shared database connection: {e}")
            raise
        
        # Start log consumer with injected shared connection
        try:
            from log_consumer import AICOLogConsumer
            log_consumer = AICOLogConsumer(config_manager, db_connection=shared_db_connection)
            logger.info("Log consumer created with shared connection, starting...")
            await log_consumer.start()
            logger.info("Log consumer started - backend logs will now be persisted")
            
            # Activate proper logging now that log consumer is running
            from aico.core.logging import _logger_factory
            if _logger_factory:
                _logger_factory.mark_all_databases_ready()
                logger._db_ready = True
                logger.info("Logging system activated - bootstrap buffer flushed")
            else:
                logger.warning("Logger factory not available for activation")
                
        except Exception as e:
            logger.error(f"Failed to start log consumer: {e}")
        
        # Check for shutdown signal before starting API Gateway
        if shutdown_event.is_set():
            logger.info("Shutdown requested during startup, aborting...")
            return
        
        # Start API Gateway if enabled (after log consumer is running)
        logger.info("Checking API Gateway configuration...")
        gateway_config = config_manager.config_cache.get('core', {}).get('api_gateway', {})
        logger.info(f"Gateway config loaded: enabled={gateway_config.get('enabled', True)}")
        
        if gateway_config.get("enabled", True):
            logger.info("Starting API Gateway...")
            api_gateway = AICOAPIGateway(config_manager, db_connection=shared_db_connection)
            logger.info("API Gateway created with database connection and transport encryption")
            
            # Check for shutdown signal before the potentially blocking start() call
            if shutdown_event.is_set():
                logger.info("Shutdown requested before API Gateway start, aborting...")
                return
            
            try:
                await api_gateway.start()
                logger.info("API Gateway started successfully")
                
                # Create and configure REST adapter with encryption middleware
                rest_adapter = api_gateway.create_rest_adapter()
                logger.info("REST adapter created with encryption middleware")
                
                # Log transport encryption status for --no-detach mode visibility
                transport_config = config_manager.get("security", {}).get("transport_encryption", {})
                encryption_enabled = transport_config.get("enabled", True)
                
                # Read detach_mode from environment variable
                detach_mode = os.environ.get("AICO_DETACH_MODE", "true").lower() == "true"
                if not detach_mode:
                    if encryption_enabled:
                        print("INFO:     🔐 Transport encryption: ENABLED (XChaCha20-Poly1305)")
                        print("INFO:     🔑 Component identity: Ed25519 signing keys")
                        print("INFO:     🤝 Handshake endpoint: /api/v1/handshake")
                        print("INFO:     ⚡ Session timeout: {}s".format(transport_config.get("session", {}).get("timeout_seconds", 3600)))
                    else:
                        print("INFO:     ⚠️  Transport encryption: DISABLED")
                
                logger.info("Transport encryption status", extra={
                    "enabled": encryption_enabled,
                    "algorithm": transport_config.get("algorithm", "XChaCha20-Poly1305"),
                    "session_timeout": transport_config.get("session", {}).get("timeout_seconds", 3600)
                })
                
                # Mount the encrypted REST adapter's FastAPI app
                app.mount("/api/v1", rest_adapter.app)
                logger.info("Encrypted REST adapter mounted at /api/v1")
                
            except Exception as e:
                logger.error(f"Failed to start API Gateway: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Add console output for WebSocket in --no-detach mode (similar to Uvicorn)
            protocols = gateway_config.get('protocols', {})
            if protocols.get('websocket', {}).get('enabled', False):
                ws_port = protocols['websocket'].get('port', 8772)
                ws_host = gateway_config.get('host', '127.0.0.1')
                ws_path = protocols['websocket'].get('path', '/ws')
                
                detach_mode = os.environ.get("AICO_DETACH_MODE", "true").lower() == "true"
                if not detach_mode:
                    print(f"INFO:     WebSocket server running on ws://{ws_host}:{ws_port}{ws_path} (Press CTRL+C to quit)")
            
            # Mount domain-based API routers
            try:
                # Initialize admin router with dependencies
                try:
                    from api.admin.router import initialize_router
                    
                    # Initialize admin router with all dependencies including log repository
                    from aico.data.logs import LogRepository
                    
                    # Create log repository with shared database connection
                    log_repository = LogRepository(shared_db_connection)
                    
                    initialize_router(
                        api_gateway.auth_manager, 
                        api_gateway.authz_manager, 
                        api_gateway.message_router, 
                        api_gateway,
                        log_repository,
                        config_manager
                    )
                    logger.info("Admin router initialized with dependencies")
                except Exception as e:
                    logger.error(f"Failed to initialize admin router: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Initialize users router with existing UserService
                try:
                    from api.users.router import initialize_router as initialize_users_router
                    from aico.data.user import UserService
                    from aico.data import LibSQLConnection
                    
                    # Initialize UserService with shared database connection
                    user_service = UserService(shared_db_connection)
                    
                    # Create proper admin dependency that checks session service
                    from api.users.dependencies import create_user_auth_dependency
                    admin_dependency = create_user_auth_dependency(api_gateway.auth_manager)
                    
                    # Initialize users router with proper service
                    initialize_users_router(
                        user_service,
                        api_gateway.auth_manager,
                        admin_dependency
                    )
                    logger.info("Users router initialized with UserService")
                except Exception as e:
                    logger.error(f"Failed to initialize users router: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Initialize health router with dependencies
                try:
                    from api.health.router import initialize_router as initialize_health_router
                    initialize_health_router(api_gateway, message_bus_host)
                    logger.info("Health router initialized with dependencies")
                except Exception as e:
                    logger.error(f"Failed to initialize health router: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Now import and mount the unified API router to the REST adapter
                from api import api_router
                rest_adapter.mount_router(api_router, prefix="/api/v1")
                logger.info("Domain-based API routers mounted at /api/v1")
                
                # Store reference to REST adapter app for server.py to use
                global rest_adapter_app
                rest_adapter_app = rest_adapter.app
                print(f"DEBUG: Set rest_adapter_app to: {rest_adapter_app}")
                print(f"DEBUG: Type: {type(rest_adapter_app)}")
                print(f"DEBUG: App routes: {[route.path for route in rest_adapter_app.routes]}")
                logger.info("REST adapter app stored for server replacement")
                
                # Log available endpoints dynamically
                endpoint_paths = []
                for route in app.routes:
                    if hasattr(route, 'path'):
                        endpoint_paths.append(route.path)
                
                logger.info(f"Available API endpoints: {sorted(set(endpoint_paths))}")
                
                # Start the server with the REST adapter app
                print(f"DEBUG: Starting server with REST adapter app: {rest_adapter_app}")
                from server import run_server_async
                await run_server_async(app, config_manager, detach=detach_mode, rest_app=rest_adapter_app)
                
            except Exception as e:
                logger.error(f"Failed to start API Gateway: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        yield
        
        # Shutdown
        if api_gateway:
            logger.info("Shutting down API Gateway...")
            await api_gateway.stop()
            logger.info("API Gateway shutdown complete")
        
        if message_bus_host:
            logger.info("Shutting down Message Bus Host...")
            await message_bus_host.stop()
            logger.info("Message Bus Host shutdown complete")
        
        logger.info("AICO backend fully initialized")
        
        # Create a task to monitor shutdown signal during app runtime
        async def shutdown_monitor():
            await shutdown_event.wait()
            logger.info("Shutdown signal received during runtime")
        
        shutdown_task = asyncio.create_task(shutdown_monitor())
        
        try:
            # This is where the application runs - wait for shutdown signal
            await shutdown_task
        finally:
            # Cancel the shutdown monitor
            shutdown_task.cancel()
            try:
                await shutdown_task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.error(f"Failed to start backend services: {e}")
        raise
    finally:
        # Shutdown
        logger.info("AICO backend server shutting down")
        
        if api_gateway:
            await api_gateway.stop()
            logger.info("API Gateway stopped")
        
        if message_bus_host:
            await message_bus_host.stop()
            logger.info("Message bus host stopped")
        
        logger.info("AICO backend shutdown complete")


app = FastAPI(
    title="AICO Backend API",
    description="AICO AI Companion Backend Services",
    version=__version__,
    lifespan=lifespan
)


async def main():
    """Main async function with proper signal handling"""
    import os
    from server import run_server_async
    
    print("Main function called")
    
    # Initialize config_manager before accessing it
    global config_manager
    if config_manager is None:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=False)
    
    print("Config manager ready")
    
    # Check if we're in gateway service mode
    service_mode = os.environ.get("AICO_SERVICE_MODE", "backend")
    detach_mode = os.environ.get("AICO_DETACH_MODE", "true").lower() == "true"
    
    # Add console output for --no-detach mode
    if not detach_mode:
        print(f"Starting AICO backend server v{__version__}")
        print(f"Service mode: {service_mode}")
        print(f"Detach mode: {detach_mode}")
    
    logger.info(f"Starting AICO backend server in {service_mode} mode", extra={
        "detach": detach_mode,
        "version": __version__
    })
    
    # Set up proper signal handling for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nSIGNAL HANDLER: Received signal {signum}")
        print("SIGNAL HANDLER: Initiating shutdown...")
        if not detach_mode:
            print(f"Received signal {signum}, shutting down gracefully...")
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
        print("SIGNAL HANDLER: Shutdown event set")
    
    # Install signal handlers in main() - these will be the final handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    if not detach_mode:
        print("Signal handlers installed for SIGTERM and SIGINT")
        print(f"Main process PID: {os.getpid()}")
    
    # Start the FastAPI app with lifespan - server startup happens in lifespan function
    import uvicorn
    
    # Get host and port from configuration
    core_config = config_manager.config_cache.get('core', {})
    api_gateway_config = core_config.get('api_gateway', {})
    rest_config = api_gateway_config.get('rest', {})
    
    host = rest_config.get('host', '127.0.0.1')
    port = rest_config.get('port', 8771)
    
    # Run uvicorn with the main app - lifespan function will handle server startup
    await uvicorn.Server(
        uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info" if not detach_mode else "warning"
        )
    ).serve()


if __name__ == "__main__":
    """Start the server when run directly"""
    try:
        print("Starting asyncio.run(main())")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted by user")
        logger.info("Application interrupted by user")
    except Exception as e:
        print(f"Application failed: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Application failed: {e}")
        sys.exit(1)
