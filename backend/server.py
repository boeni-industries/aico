"""
AICO Embedded Server

Custom server wrapper that provides proper lifecycle management, graceful shutdown,
and multi-platform compatibility for AICO backend services.
"""

import asyncio
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Import AICO modules
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
from aico.core.logging import get_logger
from aico.core.process import ServiceContext
from aico.core.config import ConfigurationManager

logger = get_logger("backend", "server")


class AICOServer:
    """
    Custom embedded server with simple shutdown mechanism.
    
    Uses a shutdown file approach for reliable cross-platform termination.
    """
    
    def __init__(self, app: FastAPI, host: str = "127.0.0.1", port: int = 8771):
        self.app = app
        self.host = host
        self.port = port
        self.server = None
        self.server_task = None
        self.running = False
        
        # Shutdown coordination
        self.shutdown_event = asyncio.Event()
        self._shutdown_initiated = False
        
        # Simple shutdown file approach
        from aico.core.paths import AICOPaths
        paths = AICOPaths()
        self.shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
        
    def _install_signal_handlers(self):
        """Install simple signal handlers"""
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, creating shutdown file...")
            self.shutdown_file.touch()
        
        # Install basic signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        print(f"Signal handlers installed")
    
    async def _check_shutdown_file(self):
        """Monitor for shutdown file"""
        while self.running:
            if self.shutdown_file.exists():
                print("Shutdown file detected, initiating shutdown...")
                self.shutdown_event.set()
                break
            await asyncio.sleep(0.5)
    
    async def _async_shutdown(self):
        """Async shutdown helper"""
        if self.shutdown_event and not self.shutdown_event.is_set():
            self.shutdown_event.set()
    
    async def start(self, detach: bool = False) -> bool:
        """
        Start the AICO server with simple shutdown mechanism.
        
        Args:
            detach: If True, run in background. If False, block until shutdown.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Clean up any existing shutdown file
            if self.shutdown_file.exists():
                self.shutdown_file.unlink()
            
            # Install signal handlers
            self._install_signal_handlers()
            
            # Configure Uvicorn server
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,
                server_header=False,
                date_header=False
            )
            
            # Create server instance
            self.server = uvicorn.Server(config)
            
            logger.info(f"Starting AICO server on {self.host}:{self.port}")
            
            if detach:
                # Background mode - start server task and return immediately
                self.server_task = asyncio.create_task(self._run_server())
                
                # Give it a moment to start
                await asyncio.sleep(1)
                
                if self.running:
                    logger.info("Server started successfully in background")
                    return True
                else:
                    logger.error("Failed to start server in background")
                    return False
            else:
                # Foreground mode - block until shutdown
                await self._run_server()
                return True
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    async def _run_server(self):
        """Internal server runner with simple shutdown monitoring"""
        try:
            # Use ServiceContext for PID file management
            with ServiceContext("gateway"):
                # Start the server in a task
                server_task = asyncio.create_task(self.server.serve())
                
                # Start shutdown file monitoring
                shutdown_monitor = asyncio.create_task(self._check_shutdown_file())
                
                self.running = True
                logger.info("Server is running")
                
                # Wait for shutdown signal or server completion
                done, pending = await asyncio.wait(
                    [server_task, shutdown_monitor, asyncio.create_task(self.shutdown_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # If shutdown was requested
                if self.shutdown_event.is_set():
                    logger.info("Shutdown requested, stopping server...")
                    print("Graceful shutdown in progress...")
                    
                    # Graceful shutdown
                    self.server.should_exit = True
                    
                    # Wait for server to stop gracefully
                    try:
                        await asyncio.wait_for(server_task, timeout=30)
                        logger.info("Server stopped gracefully")
                        print("Server shutdown complete")
                    except asyncio.TimeoutError:
                        logger.warning("Server shutdown timeout, cancelling...")
                        print("Shutdown timeout, forcing stop...")
                        server_task.cancel()
                        try:
                            await server_task
                        except asyncio.CancelledError:
                            pass
                
                # Cancel any remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False
            # Clean up shutdown file
            if self.shutdown_file.exists():
                self.shutdown_file.unlink()
            logger.info("Server shutdown complete")
    
    async def stop(self, timeout: int = 30) -> bool:
        """
        Stop the server gracefully
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if not self.running:
                return True
                
            logger.info("Stopping server...")
            print("🛑 Initiating server shutdown...")
            self.shutdown_event.set()
            
            if self.server_task:
                try:
                    await asyncio.wait_for(self.server_task, timeout=30)
                    print("✅ Server stopped successfully")
                except asyncio.TimeoutError:
                    logger.warning("Server stop timeout")
                    print("⚠ Server stop timeout, forcing shutdown...")
                    self.server_task.cancel()
            
            self.running = False
            self._restore_signal_handlers()
            logger.info("Server stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status information"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "process_status": self.process_manager.get_service_status()
        }


async def run_server_async(app: FastAPI, config_manager, detach: bool = True, rest_app: FastAPI = None):
    """
    Asynchronous server runner with proper lifecycle management
    
    Args:
        app: FastAPI application instance (may be replaced by REST adapter app)
        config_manager: Configuration manager
        detach: Whether to run in background mode
    """
    # Get host and port from configuration
    core_config = config_manager.config_cache.get('core', {})
    api_gateway_config = core_config.get('api_gateway', {})
    rest_config = api_gateway_config.get('rest', {})
    
    host = rest_config.get('host', '127.0.0.1')
    port = rest_config.get('port', 8771)
    
    # Use REST adapter app if passed directly as parameter
    print(f"DEBUG: About to check for REST adapter app replacement")
    if rest_app is not None:
        print(f"DEBUG: REST adapter app passed as parameter: {rest_app}")
        print(f"DEBUG: Type: {type(rest_app)}")
        print("DEBUG: Using REST adapter app instead of main app for server")
        logger.info("Using REST adapter app instead of main app for server")
        app = rest_app
    else:
        print("DEBUG: No REST adapter app passed, using main app")
        logger.warning("REST adapter app not provided, using main app")
    
    try:
        # Create and start server
        server = AICOServer(app, host, port)
        success = await server.start(detach=detach)
        if not success:
            logger.error("Failed to start server")
            sys.exit(1)
        
        if not detach:
            # In foreground mode, add console output and wait for shutdown
            print(f"✅ Server started successfully on {server.host}:{server.port}")
            print("Press Ctrl+C to stop the server")
            
            # Wait for shutdown event
            try:
                while server.running and not server.shutdown_event.is_set():
                    await asyncio.sleep(0.1)
                
                if server.shutdown_event.is_set():
                    print("🛑 Graceful shutdown initiated...")
                    await server.stop()
                    print("✅ Server stopped gracefully")
                
            except KeyboardInterrupt:
                print("\n🛑 Keyboard interrupt received")
                await server.stop()
                print("✅ Server stopped gracefully")
            
            logger.info("Server finished")
            sys.exit(0)
        else:
            # In background mode, keep the process alive
            try:
                while server.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
            finally:
                await server.stop()
                sys.exit(0)
                
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


def run_server_sync(app: FastAPI, config_manager: ConfigurationManager, detach: bool = True):
    """
    Synchronous entry point for running the server
    
    Args:
        app: FastAPI application instance  
        config_manager: Configuration manager
        detach: Whether to run in background mode
    """
    try:
        # Fix Windows event loop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run the async server
        asyncio.run(run_server_async(app, config_manager, detach))
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)
