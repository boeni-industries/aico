from fastapi import FastAPI
import asyncio
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

# Import API Gateway
from api_gateway import AICOAPIGateway

# Import Message Bus Host
from message_bus_host import AICOMessageBusHost

__version__ = "0.0.1"

# Initialize logger for backend
logger = get_logger("backend.main")

# Global instances
config_manager = None
message_bus_host = None
api_gateway = None

app = FastAPI(
    title="AICO Backend",
    description="AICO AI Companion Backend Service",
    version=__version__
)

@app.on_event("startup")
async def startup_event():
    """Initialize and start all backend services"""
    global config_manager, message_bus_host, api_gateway
    
    try:
        logger.info("AICO backend server starting up", extra={
            "version": __version__,
            "component": "fastapi_server"
        })
        
        # Initialize configuration
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=False)
        logger.info("Configuration system initialized")
        
        # Start message bus host
        message_bus_host = AICOMessageBusHost()
        await message_bus_host.start()
        logger.info("Message bus host started")
        
        # Start API Gateway if enabled
        gateway_config = config_manager.get("api_gateway", {})
        if gateway_config.get("enabled", True):
            api_gateway = AICOAPIGateway(config_manager)
            await api_gateway.start()
            logger.info("API Gateway started")
        else:
            logger.info("API Gateway disabled in configuration")
        
        logger.info("AICO backend fully initialized")
        
    except Exception as e:
        logger.error(f"Failed to start backend services: {e}")
        raise

@app.on_event("shutdown") 
async def shutdown_event():
    """Shutdown all backend services"""
    global message_bus_host, api_gateway
    
    try:
        logger.info("AICO backend server shutting down", extra={
            "version": __version__,
            "component": "fastapi_server"
        })
        
        # Stop API Gateway
        if api_gateway:
            await api_gateway.stop()
            logger.info("API Gateway stopped")
        
        # Stop message bus host
        if message_bus_host:
            await message_bus_host.stop()
            logger.info("Message bus host stopped")
        
        logger.info("AICO backend shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during backend shutdown: {e}")

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
    """Detailed health check endpoint"""
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
