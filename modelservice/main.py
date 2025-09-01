"""
Modelservice main application entry point.
"""

import sys
from pathlib import Path
from fastapi import FastAPI
import uvicorn

# Add shared module to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.version import get_modelservice_version
from aico.security.key_manager import AICOKeyManager
from .api.router import router

# Get version from VERSIONS file
__version__ = get_modelservice_version()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AICO Modelservice",
        description="Model management and inference service",
        version=__version__
    )
    
    # Initialize configuration and key manager for encryption middleware
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        key_manager = AICOKeyManager(config_manager)
        
        # Import and add encryption middleware (same pattern as API Gateway)
        from backend.api_gateway.middleware.encryption import EncryptionMiddleware
        app.add_middleware(EncryptionMiddleware, key_manager=key_manager)
        
    except Exception as e:
        # No fallback - encryption is mandatory
        raise RuntimeError(f"Failed to initialize encryption middleware: {e}. Secure communication is required.")
    
    # Include API router
    app.include_router(router)
    
    return app


app = create_app()


def main():
    """Main entry point for the modelservice."""
    # Load configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    modelservice_config = config_manager.get("modelservice", {})
    rest_config = modelservice_config.get("rest", {})
    
    host = rest_config.get("host", "127.0.0.1")
    port = rest_config.get("port", 8773)
    
    print(f"Starting AICO Modelservice v{__version__} on {host}:{port}")
    
    uvicorn.run(
        "modelservice.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()