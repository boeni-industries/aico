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

    # Setup signal handlers and process management
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_event.set()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Write PID file for process management
    from aico.core.process import ProcessManager
    process_manager = ProcessManager("gateway")
    process_manager.write_pid(os.getpid())
    
    print("Signal handlers registered and PID file written")

    # Import refactored API Gateway AFTER logging is initialized
    from api_gateway.gateway_v2 import AICOAPIGatewayV2
    print("API Gateway V2 imported successfully")

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

async def monitor_shutdown_file():
    """Monitor for shutdown file created by CLI stop command"""
    from aico.core.paths import AICOPaths
    paths = AICOPaths()
    shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
    
    while not shutdown_event.is_set():
        try:
            if shutdown_file.exists():
                logger.info("Shutdown file detected, initiating graceful shutdown")
                shutdown_file.unlink()  # Remove the shutdown file
                shutdown_event.set()
                break
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error monitoring shutdown file: {e}")
            await asyncio.sleep(1)

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
        
        async def setup_backend_components():
            """Setup backend components following proper architecture"""
            # Initialize logging system properly
            from aico.core.logging import _logger_factory
            if _logger_factory:
                _logger_factory.config = config_manager
            
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
            
            # Create and initialize API Gateway
            gateway_config = config_manager.config_cache.get('core', {}).get('api_gateway', {})
            logger.info(f"Gateway config loaded: enabled={gateway_config.get('enabled', True)}")
            
            api_gateway = None
            if gateway_config.get("enabled", True):
                logger.info("Creating API Gateway...")
                api_gateway = AICOAPIGatewayV2(config_manager, db_connection=shared_db_connection)
                logger.info("API Gateway created with database connection and transport encryption")
                
                # Initialize gateway (this sets up adapters but doesn't start separate servers)
                await api_gateway.start()
                logger.info("API Gateway initialized successfully")
                
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
                        print("INFO:     ⚡ Session timeout: 3600s")
                    else:
                        print("INFO:     🔓 Transport encryption: DISABLED")
                        print("INFO:     ⚠️  WARNING: Running without encryption in development mode")
            
            return api_gateway, log_consumer, shared_db_connection
        
        # Initialize configuration
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=False)
        logger.info("Configuration system initialized")
        
        # Update logger factory with full configuration
        from aico.core.logging import _logger_factory
        if _logger_factory:
            _logger_factory.config = config_manager
        
        # Message bus will be started by API Gateway's MessageBusPlugin
        logger.info("Message bus will be started by API Gateway's MessageBusPlugin")
        
        api_gateway, log_consumer, shared_db_connection = await setup_backend_components()
        
        # Start shutdown file monitor task
        shutdown_monitor_task = asyncio.create_task(monitor_shutdown_file())
        
        # Check for shutdown signal before starting API Gateway
        if shutdown_event.is_set():
            logger.info("Shutdown requested during startup, aborting...")
            return
        
        # Create FastAPI app
        app = FastAPI(
            title="AICO Backend API",
            version=__version__,
            description="AICO Backend REST API with plugin-based middleware"
        )
        
        # Setup FastAPI integration with API Gateway (proper architecture)
        if api_gateway:
            api_gateway.setup_fastapi_integration(app)
            logger.info("FastAPI integration setup complete")
        
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
                    api_gateway.gateway_core.auth_manager if api_gateway else None, 
                    api_gateway.gateway_core.authz_manager if api_gateway else None, 
                    api_gateway.gateway_core.message_router if api_gateway else None, 
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
                
                # Initialize UserService with shared database connection
                user_service = UserService(shared_db_connection)
                
                # Create proper admin dependency that checks session service
                from api.users.dependencies import create_user_auth_dependency
                admin_dependency = create_user_auth_dependency(api_gateway.gateway_core.auth_manager if api_gateway else None)
                
                # Initialize users router with proper service
                initialize_users_router(
                    user_service,
                    api_gateway.gateway_core.auth_manager if api_gateway else None,
                    admin_dependency
                )
                logger.info("Users router initialized with UserService")
                
                # Mount domain API routers directly to main app
                from api import api_router
                app.include_router(api_router, prefix="/api/v1")
                logger.info("Domain-based API routers mounted to main app at /api/v1")
                
                # Log available endpoints dynamically
                endpoint_paths = []
                for route in app.routes:
                    if hasattr(route, 'path'):
                        endpoint_paths.append(route.path)
                
                logger.info(f"Available API endpoints: {sorted(set(endpoint_paths))}")
                
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
        
        logger.info("AICO backend fully initialized")
        
        # Create a task to monitor shutdown signal during app runtime
        async def shutdown_monitor():
            await shutdown_event.wait()
            logger.info("Shutdown signal received during runtime")
        shutdown_monitor_task = asyncio.create_task(shutdown_monitor())
        
    except Exception as e:
        logger.error(f"Failed to start backend services: {e}")
        raise
    finally:
        # Shutdown cleanup
        logger.info("AICO backend server shutting down")
        
        # Cancel shutdown monitor task if it exists
        if 'shutdown_monitor_task' in locals():
            shutdown_monitor_task.cancel()
            try:
                await shutdown_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop API Gateway
        if api_gateway:
            logger.info("Shutting down API Gateway...")
            try:
                await api_gateway.stop()
                logger.info("API Gateway shutdown complete")
            except Exception as e:
                logger.error(f"Error stopping API Gateway: {e}")
        
        # Clean up PID files
        try:
            process_manager.cleanup_pid_files()
            logger.info("PID files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up PID files: {e}")
        
        logger.info("AICO backend shutdown complete")


# Create FastAPI app instance
app = FastAPI(
    title="AICO Backend API",
    description="AICO AI Companion Backend Services",
    version=__version__,
    lifespan=lifespan
)

# Middleware will be configured by API Gateway plugins - no manual configuration needed


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
    
    # Start uvicorn server directly - lifespan handles all startup
    import uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info" if not detach_mode else "warning"
    )
    server = uvicorn.Server(config)
    
    if detach_mode:
        # Background mode - start server task and return
        server_task = asyncio.create_task(server.serve())
        await asyncio.sleep(1)  # Give it time to start
        logger.info("Server started in background mode")
    else:
        # Foreground mode - block until shutdown
        await server.serve()


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
