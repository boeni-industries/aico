"""
Modelservice main application entry point - ZMQ Message Bus Implementation.

This module implements a pure ZeroMQ message bus service that replaces the
FastAPI/uvicorn HTTP server. All communication is via ZMQ with encryption.
"""

import sys
import os
import asyncio
import signal
from pathlib import Path

# Fix Windows asyncio event loop compatibility with ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize configuration and logging before any imports that get loggers
from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger
config_manager = ConfigurationManager()
config_manager.initialize()
initialize_logging(config_manager)
from aico.core.version import get_modelservice_version
from .core.zmq_service import ModelserviceZMQService

# Get version from VERSIONS file
__version__ = get_modelservice_version()

logger = get_logger("modelservice", "main")

# Global service instance for signal handling
_zmq_service = None


async def initialize_modelservice():
    """Initialize modelservice with Ollama and return configuration."""
    # Load configuration
    cfg = ConfigurationManager()
    cfg.initialize()
    
    # Initialize logging in lifespan context
    logger_factory = initialize_logging(cfg)
    
    modelservice_config = cfg.get("modelservice", {})
    env = os.getenv("AICO_ENV", "development")

    # Startup: Display initial info and use standard AICO logging
    startup_msg = "\n" + "=" * 60 + "\n[*] AICO Modelservice (ZMQ)\n" + "=" * 60
    print(startup_msg)
    logger.info("AICO Modelservice starting up")
    
    server_info = f"[>] Communication: ZeroMQ Message Bus\n[>] Environment: {env}\n[>] Version: v{__version__}\n[>] Encryption: Enabled"
    print(server_info)
    logger.info(f"Server configuration - Communication: ZMQ, Environment: {env}, Version: {__version__}, Encryption: Enabled")
    
    print("=" * 60)
    
    # Check if backend is running before starting ZMQ service
    print("🔍 Checking backend availability...")
    backend_available = await _check_backend_health(cfg)
    if not backend_available:
        print("⚠️  Backend not available - logs will use fallback storage")
        logger.warning("Backend not available at startup - using fallback logging")
    else:
        print("✅ Backend is available")
        logger.info("Backend confirmed available at startup")
    
    # Start ZMQ service EARLY to capture all subsequent logs
    print("🔌 Starting ZMQ logging service...")
    logger.info("Starting ZMQ service early for log capture")
    
    zmq_service = ModelserviceZMQService(cfg, None)  # No ollama_manager yet
    await zmq_service.start_early()  # New method for early startup
    
    # Initialize ZMQ logging transport now that message bus is available
    if logger_factory._transport:
        logger_factory._transport.mark_broker_ready()
        
        # Wait for client connection AND LogConsumer to be ready
        max_wait = 10  # 10 seconds max wait
        wait_time = 0
        while wait_time < max_wait:
            await asyncio.sleep(0.1)
            wait_time += 0.1
            
            # Check if client is connected
            client = getattr(logger_factory._transport, '_message_bus_client', None)
            if client and getattr(client, 'connected', False):
                break
        else:
            print(f"⚠️  ZMQ client connection timeout after {max_wait}s")
        
        # Additional wait for LogConsumer to be ready
        await asyncio.sleep(0.5)  # Give LogConsumer time to subscribe
        
        # Flush buffer after both client connection and LogConsumer are ready
        if hasattr(logger_factory, '_log_buffer'):
            buffer_size = len(logger_factory._log_buffer._buffer)
            logger_factory._log_buffer.flush_to_transport(logger_factory._transport)
    else:
        print("⚠️  Logger factory has no transport!")
    
    # Also test without the extra topic to see if that works
    logger.info("Testing modelservice log without extra topic")
    
    # Initialize OllamaManager (now that ZMQ logging is available)
    from .core.ollama_manager import OllamaManager
    ollama_manager = OllamaManager()
    
    # Set the ollama_manager in the ZMQ service
    zmq_service.set_ollama_manager(ollama_manager)
    
    # Initialize process management for graceful shutdown
    process_manager = None
    if os.getenv("AICO_DETACH_MODE") == "true":
        from aico.core.process import ProcessManager
        process_manager = ProcessManager("modelservice")
        process_manager.write_pid(os.getpid())
    
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
    print("[+] ZMQ service ready... (Press Ctrl+C to stop)\n")
    logger.info("Modelservice startup complete, ZMQ service ready")

    return cfg, ollama_manager, process_manager, zmq_service


async def _check_backend_health(cfg: ConfigurationManager) -> bool:
    """Check if the backend is running and accessible."""
    try:
        import httpx
        
        # Get backend configuration
        backend_config = cfg.get("core.api_gateway", {})
        host = backend_config.get("host", "localhost")
        port = backend_config.get("port", 8771)
        
        # Try to connect to backend health endpoint
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"http://{host}:{port}/api/v1/health")
            return response.status_code == 200
            
    except Exception as e:
        return False


async def shutdown_modelservice(ollama_manager, process_manager):
    """Gracefully shutdown modelservice and Ollama."""
    print("\n[-] Graceful shutdown initiated...")
    logger.info("Graceful shutdown initiated")
    
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


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _zmq_service
    logger.info(f"Received signal {signum}, initiating shutdown")
    if _zmq_service:
        asyncio.create_task(_zmq_service.stop())


async def main():
    """Main entry point for the modelservice ZMQ service."""
    global _zmq_service
    
    try:
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize modelservice and Ollama (ZMQ service started early)
        config, ollama_manager, process_manager, _zmq_service = await initialize_modelservice()
        
        # Continue running the ZMQ service (already started early)
        await _zmq_service.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Modelservice error: {str(e)}")
        raise
    finally:
        # Cleanup
        if _zmq_service:
            await _zmq_service.stop()
        await shutdown_modelservice(ollama_manager, process_manager)


def run_main():
    """Synchronous wrapper for the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Modelservice stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_main()