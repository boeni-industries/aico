import asyncio
import sys
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

# Import API Gateway AFTER logging is initialized
from api_gateway import AICOAPIGateway

# Import Message Bus Host
from message_bus_host import AICOMessageBusHost

# Global instances (config_manager already initialized above)
message_bus_host = None
api_gateway = None


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
        
        # Start API Gateway if enabled (after log consumer is running)
        logger.info("Checking API Gateway configuration...")
        gateway_config = config_manager.get("api_gateway", {})
        logger.info(f"Gateway config loaded: enabled={gateway_config.get('enabled', True)}")
        
        if gateway_config.get("enabled", True):
            logger.info("Starting API Gateway...")
            api_gateway = AICOAPIGateway(config_manager)
            logger.info("API Gateway created, calling start()...")
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
        
        yield  # This is where the application runs
        
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
    """Health check endpoint"""
    # Create a fresh logger (after log consumer is ready)
    health_logger = get_logger("backend", "health")
    
    # Manually ensure database ready flag is set
    health_logger._db_ready = True
    
    # Log health check access at debug level for normal operation
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


if __name__ == "__main__":
    """Start the server when run directly"""
    import uvicorn
    import os
    
    # Initialize config_manager before accessing it
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
    
    # Start the Uvicorn server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_config=None,  # Use our custom logging
        access_log=False  # Disable uvicorn access logs (we have our own)
    )
