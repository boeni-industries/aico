import asyncio
import sys
import signal
from datetime import datetime

# Fix ZeroMQ compatibility on Windows - must be set before any ZMQ imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from pathlib import Path
from contextlib import asynccontextmanager

# Shared modules now installed via UV editable install

from aico.core.logging import initialize_logging, get_logger
from aico.core.config import ConfigurationManager

__version__ = "0.1.1"

# Initialize configuration FIRST
config_manager = ConfigurationManager()
config_manager.initialize(lightweight=True)

# Initialize logging system - will use bootstrap buffering until message bus is ready
initialize_logging(config_manager)

# Now we can safely get loggers
logger = get_logger("backend", "main")

# Register signal handlers EARLY - before any blocking operations
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
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

# Import API Gateway AFTER logging is initialized
from api_gateway import AICOAPIGateway

# Import Message Bus Host
from message_bus_host import AICOMessageBusHost

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
        
        # Start log consumer IMMEDIATELY after message bus - before API Gateway
        try:
            from log_consumer import AICOLogConsumer
            log_consumer = AICOLogConsumer(config_manager)
            logger.info("Log consumer created, starting...")
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
        gateway_config = config_manager.get("api_gateway", {})
        logger.info(f"Gateway config loaded: enabled={gateway_config.get('enabled', True)}")
        
        if gateway_config.get("enabled", True):
            logger.info("Starting API Gateway...")
            api_gateway = AICOAPIGateway(config_manager)
            logger.info("API Gateway created, calling start()...")
            
            # Check for shutdown signal before the potentially blocking start() call
            if shutdown_event.is_set():
                logger.info("Shutdown requested before API Gateway start, aborting...")
                return
                
            await api_gateway.start()
            logger.info("API Gateway started")
            
            # Register admin endpoints after gateway is initialized
            from api_gateway.admin.endpoints import create_admin_app
            admin_app = create_admin_app(
                auth_manager=api_gateway.auth_manager,
                authz_manager=api_gateway.authz_manager,
                message_router=api_gateway.message_router,
                gateway=api_gateway
            )
            # Mount admin endpoints to main app
            app.mount("/admin", admin_app)
            logger.info("Admin endpoints registered")
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
    title="AICO Backend",
    description="AICO AI Companion Backend Service",
    version=__version__,
    lifespan=lifespan
)

# Modern FastAPI uses lifespan events only

# Admin endpoints will be registered after gateway initialization

@app.get("/")
def read_root():
    """Root health check endpoint"""
    logger.debug("Health check endpoint accessed")
    
    status = {
        "service": "AICO Backend",
        "version": __version__,
        "status": "running"
    }
    
    # Add component status if available
    if message_bus_host:
        status["message_bus"] = "running" if message_bus_host.running else "stopped"
    
    if api_gateway:
        status["api_gateway"] = "running" if api_gateway.running else "stopped"
    
    return status

@app.get("/health")
def health_check():
    health_logger = get_logger("backend", "health")
    health_logger.debug("Health endpoint accessed", extra={
        "endpoint": "/health",
        "method": "GET",
        "component": "fastapi_health"
    })
    
    health_status = {
        "status": "healthy",
        "version": __version__,
        "components": {}
    }
    
    # Check message bus health
    if message_bus_host:
        health_status["components"]["message_bus"] = {
            "status": "running" if message_bus_host.running else "stopped",
            "modules": len(message_bus_host.modules),
            "address": message_bus_host.bind_address
        }
    
    # Check API Gateway health
    if api_gateway:
        health_status["components"]["api_gateway"] = api_gateway.get_health_status()
    
    return health_status


async def main():
    """Main async function with proper signal handling"""
    import uvicorn
    import os
    
    # Initialize config_manager before accessing it
    global config_manager
    if config_manager is None:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=False)
    
    # Get configuration for server settings
    host = config_manager.get("api_gateway.host", "127.0.0.1")
    port = config_manager.get("api_gateway.protocols.rest.port", 8771)
    
    # Check if we're in gateway service mode
    service_mode = os.environ.get("AICO_SERVICE_MODE", "backend")
    
    logger.info(f"Starting AICO backend server in {service_mode} mode", extra={
        "host": host,
        "port": port,
        "version": __version__
    })
    
    # Create server config
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_config=None,  # Use our custom logging
        access_log=False  # Disable uvicorn access logs (we have our own)
    )
    
    server = uvicorn.Server(config)
    
    # Start server in background task
    server_task = asyncio.create_task(server.serve())
    
    try:
        # Wait for shutdown signal
        await shutdown_event.wait()
        logger.info("Shutdown signal received, stopping server...")
        
        # Graceful shutdown
        server.should_exit = True
        await server_task
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping server...")
        server.should_exit = True
        await server_task
    
    logger.info("Server shutdown complete")


if __name__ == "__main__":
    """Start the server when run directly"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)
