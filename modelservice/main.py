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

    # Startup: Ensure Ollama is installed and start it
    print("\n" + "=" * 60)
    print("[*] AICO Modelservice")
    print("=" * 60)
    print(f"[>] Server: http://{host}:{port}")
    print(f"[>] Environment: {env}")
    print(f"[>] Version: v{__version__}")
    print(f"[>] Encryption: {'Enabled (XChaCha20-Poly1305)' if _encryption_enabled else 'Disabled'}")
    print("=" * 60)
    
    # Initialize Ollama with rich progress indicators
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.panel import Panel
    from rich.text import Text
    
    console = Console()
    console.print(Panel.fit("[bold cyan]Initializing Ollama[/bold cyan]", border_style="cyan"))
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True
        ) as progress:
            
            # Check installation
            install_task = progress.add_task("Checking Ollama installation...", total=100)
            progress.update(install_task, advance=20)
            
            if await ollama_manager.ensure_installed():
                progress.update(install_task, completed=100, description="✓ Ollama binary ready")
                
                # Start server
                start_task = progress.add_task("Starting Ollama server...", total=100)
                progress.update(start_task, advance=30)
                
                if await ollama_manager.start_ollama():
                    progress.update(start_task, completed=100, description="✓ Ollama server started")
                    
                    # Get status
                    status_task = progress.add_task("Verifying server status...", total=100)
                    progress.update(status_task, advance=50)
                    
                    ollama_status = await ollama_manager.get_status()
                    if ollama_status:
                        version = ollama_status.get('version', 'unknown')
                        progress.update(status_task, completed=100, description=f"✓ Ollama v{version} ready")
                        console.print(f"[green]✓[/green] Ollama server: http://127.0.0.1:11434")
                    else:
                        progress.update(status_task, completed=100, description="⚠ Status check incomplete")
                        console.print("[yellow]⚠[/yellow] Could not verify Ollama status")
                else:
                    progress.update(start_task, completed=100, description="✗ Server start failed")
                    console.print("[red]✗[/red] Ollama server failed to start")
            else:
                progress.update(install_task, completed=100, description="✗ Installation failed")
                console.print("[red]✗[/red] Ollama installation failed")
                
    except Exception as e:
        console.print(f"[red]✗ Ollama initialization error:[/red] {e}")
        # Log the full exception for debugging
        import traceback
        console.print(f"[dim]Full traceback:[/dim]\n{traceback.format_exc()}")
    
    print("=" * 60)
    print("[+] Starting server... (Press Ctrl+C to stop)\n")

    # Store ollama_manager in app state for API access
    app.state.ollama_manager = ollama_manager

    try:
        yield
    except (KeyboardInterrupt, SystemExit):
        print("\n[-] Graceful shutdown initiated...")
    finally:
        print("[~] Stopping services...")
        
        # Stop Ollama gracefully
        try:
            await ollama_manager.stop_ollama()
            print("[+] Ollama stopped")
        except Exception as e:
            print(f"[!] Error stopping Ollama: {e}")
            
        if process_manager:
            process_manager.cleanup_pid_files()
        print("[+] Shutdown complete.")


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
        from .api.logging_client import APIGatewayLoggingClient
        import asyncio
        
        config = get_modelservice_config()
        service_auth = get_service_auth_manager()
        logging_client = APIGatewayLoggingClient(config, service_auth)
        
        # Force authentication attempt
        async def test_auth():
            try:
                await logging_client._get_service_token()
                print("[+] API Gateway authentication: SUCCESS")
            except Exception as e:
                print(f"[!] API Gateway authentication: FAILED - {e}")
        
        asyncio.run(test_auth())
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