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

# Add shared/aico/proto to sys.path for generated proto imports
sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "aico" / "proto"))

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

# Backend version - this is the canonical source for backend version
__version__ = "0.3.0"

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
    from api_gateway import AICOAPIGateway
    print("API Gateway imported")

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
            
            key_manager = AICOKeyManager()
            paths = AICOPaths()
            db_path = paths.resolve_database_path("aico.db")
            
            # Get encryption key (same logic as before)
            cached_key = key_manager._get_cached_session()
            if cached_key:
                key_manager._extend_session()
                db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            else:
                import keyring
                stored_key = keyring.get_password(key_manager.service_name, "master_key")
                master_key = bytes.fromhex(stored_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            
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
            logger.info("API Gateway created with database connection")
            
            # Check for shutdown signal before the potentially blocking start() call
            if shutdown_event.is_set():
                logger.info("Shutdown requested before API Gateway start, aborting...")
                return
            
            try:
                await api_gateway.start()
                logger.info("API Gateway started successfully")
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
                
                # Now import and mount the unified API router
                from api import api_router
                app.include_router(api_router, prefix="/api/v1")
                logger.info("Domain-based API routers mounted at /api/v1")
                
                # Log available endpoints
                logger.info("Available API endpoints:", extra={
                    "users": "/api/v1/users/*",
                    "admin": "/api/v1/admin/*", 
                    "health": "/api/v1/health/*"
                })
                
            except Exception as e:
                logger.error(f"Failed to initialize API routers: {e}")
                import traceback
                traceback.print_exc()
                logger.info("Falling back to basic health endpoint only")
        else:
            logger.info("API Gateway disabled in configuration")
        
        logger.info("AICO backend fully initialized")
        
        # Create a task to monitor shutdown signal during app runtime
        async def shutdown_monitor():
            await shutdown_event.wait()
            logger.info("Shutdown signal received during runtime")
        
        shutdown_task = asyncio.create_task(shutdown_monitor())
        
        try:
            yield  # This is where the application runs
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
    
    # Use our custom server wrapper
    await run_server_async(app, config_manager, detach=detach_mode)


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
