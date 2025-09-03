"""
Modelservice main application entry point.
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Note: sys.path hacks removed; rely on proper package configuration per pyproject.toml

# Initialize configuration and logging before any imports that get loggers
from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging
config_manager = ConfigurationManager()
config_manager.initialize()
initialize_logging(config_manager)
from aico.core.version import get_modelservice_version
from aico.security.key_manager import AICOKeyManager
from .api.router import router

# Get version from VERSIONS file
__version__ = get_modelservice_version()

# Track encryption middleware initialization for banner display
_encryption_enabled = False


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
        global _encryption_enabled
        _encryption_enabled = True
        
    except Exception as e:
        # No fallback - encryption is mandatory
        raise RuntimeError(f"Failed to initialize encryption middleware: {e}. Secure communication is required.")
    
    # Include API router
    app.include_router(router)
    
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan for startup/shutdown logging and hooks."""
    # Load configuration
    cfg = ConfigurationManager()
    cfg.initialize()
    
    # Initialize logging in lifespan context
    initialize_logging(cfg)
    
    modelservice_config = cfg.get("modelservice", {})
    rest_config = modelservice_config.get("rest", {})
    host = rest_config.get("host", "127.0.0.1")
    port = rest_config.get("port", 8773)
    env = os.getenv("AICO_ENV", "development")

    # Initialize OllamaManager (now that logging is initialized)
    from .core.ollama_manager import OllamaManager
    ollama_manager = OllamaManager()
    
    # Initialize process management for graceful shutdown
    process_manager = None
    if os.getenv("AICO_DETACH_MODE") == "true":
        from aico.core.process import ProcessManager
        process_manager = ProcessManager("modelservice")
        process_manager.write_pid(os.getpid())

    # Initialize logger for startup messages
    from aico.core.logging import AICOLogger
    logger = AICOLogger("modelservice", "startup", cfg)
    
    # Startup: Ensure Ollama is installed and start it
    startup_msg = "\n" + "=" * 60 + "\n[*] AICO Modelservice\n" + "=" * 60
    print(startup_msg)
    logger.info("AICO Modelservice starting up")
    
    server_info = f"[>] Server: http://{host}:{port}\n[>] Environment: {env}\n[>] Version: v{__version__}\n[>] Encryption: {'Enabled (XChaCha20-Poly1305)' if _encryption_enabled else 'Disabled'}"
    print(server_info)
    logger.info(f"Server configuration - Host: {host}, Port: {port}, Environment: {env}, Version: {__version__}, Encryption: {'Enabled' if _encryption_enabled else 'Disabled'}")
    
    print("=" * 60)
    
    # Initialize Ollama with beautiful status messages
    print("🔧 Initializing Ollama")
    logger.info("Starting Ollama initialization")
    
    try:
        if await ollama_manager.ensure_installed():
            print("✅ Ollama binary ready")
            logger.info("Ollama binary installation verified")
            
            if await ollama_manager.start_ollama():
                print("✅ Ollama server started")
                logger.info("Ollama server started successfully")
                
                ollama_status = await ollama_manager.get_status()
                if ollama_status:
                    version = ollama_status.get('version', 'unknown')
                    print(f"✅ Ollama v{version} ready at http://127.0.0.1:11434")
                    logger.info(f"Ollama v{version} ready at http://127.0.0.1:11434")
                    
                    # Auto-pull and start default models
                    started_models = await ollama_manager._ensure_default_models()
                    
                    # Report started models
                    if started_models:
                        print(f"✅ Started {len(started_models)} model(s): {', '.join(started_models)}")
                        logger.info(f"Started {len(started_models)} model(s): {', '.join(started_models)}")
                    else:
                        print("ℹ️ No models configured for auto-start")
                        logger.info("No models configured for auto-start")
                else:
                    print("⚠️ Could not verify Ollama status")
                    logger.warning("Could not verify Ollama status")
            else:
                print("❌ Ollama server failed to start")
                logger.error("Ollama server failed to start")
        else:
            print("❌ Ollama installation failed")
            logger.error("Ollama installation failed")
                
    except Exception as e:
        print(f"❌ Ollama initialization error: {e}")
        logger.error(f"Ollama initialization error: {e}")
        # Log the full exception for debugging
        import traceback
        full_traceback = traceback.format_exc()
        print(f"Full traceback:\n{full_traceback}")
        logger.error(f"Full traceback: {full_traceback}")
    
    print("=" * 60)
    print("[+] Starting server... (Press Ctrl+C to stop)\n")
    logger.info("Modelservice startup complete, server starting")

    # Store ollama_manager in app state for API access
    app.state.ollama_manager = ollama_manager

    try:
        yield
    except (KeyboardInterrupt, SystemExit):
        print("\n[-] Graceful shutdown initiated...")
        logger.info("Graceful shutdown initiated")
    finally:
        print("[~] Stopping services...")
        logger.info("Stopping services")
        
        # Stop Ollama gracefully
        try:
            await ollama_manager.stop_ollama()
            print("[+] Ollama stopped")
            logger.info("Ollama stopped successfully")
        except Exception as e:
            print(f"[!] Error stopping Ollama: {e}")
            logger.error(f"Error stopping Ollama: {e}")
            
        if process_manager:
            process_manager.cleanup_pid_files()
        print("[+] Shutdown complete.")
        logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan, title="AICO Modelservice", version=__version__)
# Reapply middleware and router to the app created above
try:
    cfg_for_mw = ConfigurationManager()
    cfg_for_mw.initialize()
    key_manager_for_mw = AICOKeyManager(cfg_for_mw)
    from backend.api_gateway.middleware.encryption import EncryptionMiddleware
    app.add_middleware(EncryptionMiddleware, key_manager=key_manager_for_mw)
    _encryption_enabled = True
except Exception as e:
    raise RuntimeError(f"Failed to initialize encryption middleware: {e}. Secure communication is required.")
app.include_router(router)


def main():
    """Main entry point for the modelservice."""
    # Load configuration for host/port
    cfg = ConfigurationManager()
    cfg.initialize()
    rest = (cfg.get("modelservice", {}) or {}).get("rest", {})
    host = rest.get("host", "127.0.0.1")
    port = rest.get("port", 8773)
    
    # Test authentication to API Gateway before starting server
    try:
        from .api.dependencies import get_modelservice_config, get_service_auth_manager
        from .api.logging_client import AICOLoggingClient
        import asyncio
        
        config = get_modelservice_config()
        service_auth = get_service_auth_manager()
        logging_client = AICOLoggingClient(config)
        
        # Test logging functionality
        print("[+] Using AICO internal logging system")
    except Exception as e:
        print(f"[!] Authentication test failed: {e}")
    
    # Determine if we should enable reload based on environment
    env = os.getenv("AICO_ENV", "development")
    detach_mode = os.getenv("AICO_DETACH_MODE", "false") == "true"
    
    # Disable reload entirely to prevent restart loops
    # Auto-reload causes issues with file watching and process management
    enable_reload = False

    uvicorn.run(
        "modelservice.main:app",
        host=host,
        port=port,
        reload=enable_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()