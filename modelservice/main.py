"""
Modelservice main application entry point - ZMQ Message Bus Implementation.

This module implements a pure ZeroMQ message bus service that replaces the
FastAPI/uvicorn HTTP server. All communication is via ZMQ with CurveZMQ encryption.
"""

import sys
import os
import asyncio
import signal
from pathlib import Path

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
    initialize_logging(cfg)
    
    modelservice_config = cfg.get("modelservice", {})
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
    
    # Startup: Ensure Ollama is installed and start it
    startup_msg = "\n" + "=" * 60 + "\n[*] AICO Modelservice (ZMQ)\n" + "=" * 60
    print(startup_msg)
    logger.info("AICO Modelservice starting up")
    
    server_info = f"[>] Communication: ZeroMQ Message Bus\n[>] Environment: {env}\n[>] Version: v{__version__}\n[>] Encryption: CurveZMQ Enabled"
    print(server_info)
    logger.info(f"Server configuration - Communication: ZMQ, Environment: {env}, Version: {__version__}, Encryption: CurveZMQ")
    
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
    print("[+] Starting ZMQ service... (Press Ctrl+C to stop)\n")
    logger.info("Modelservice startup complete, ZMQ service starting")

    return cfg, ollama_manager, process_manager


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
        
        # Initialize modelservice and Ollama
        config, ollama_manager, process_manager = await initialize_modelservice()
        
        # Create and start ZMQ service
        _zmq_service = ModelserviceZMQService(config, ollama_manager)
        
        # Start the ZMQ service (this will run until stopped)
        await _zmq_service.start()
        
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