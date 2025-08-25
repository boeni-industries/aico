"""
AICO CLI Gateway Commands

Provides API Gateway management, protocol control, and JWT authentication.
"""

import typer
import json
import requests
import os
import sys
import time
import yaml
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add shared module to path for CLI usage FIRST
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

# Import decorators AFTER shared path is set
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive, destructive

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager

# Import platform-aware characters
from cli.utils.platform import get_platform_chars

console = Console()

# Get platform-appropriate characters
chars = get_platform_chars()

def _get_jwt_token() -> Optional[str]:
    """Get stored JWT token for CLI authentication from secure keyring"""
    try:
        key_manager = AICOKeyManager()
        return key_manager.get_jwt_token("api_gateway")
    except Exception:
        return None

def _store_jwt_token(token: str) -> None:
    """Store JWT token for CLI authentication in secure keyring"""
    try:
        key_manager = AICOKeyManager()
        key_manager.store_jwt_token("api_gateway", token)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to store JWT token in keyring: {e}[/yellow]")
        console.print("[dim]Token generated but not persisted - you may need to login again[/dim]")


def _is_gateway_running() -> bool:
    """Check if API Gateway is currently running"""
    try:
        # First check via PID file
        from pathlib import Path
        import sys
        
        # Add shared module to path
        if getattr(sys, 'frozen', False):
            shared_path = Path(sys._MEIPASS) / 'shared'
        else:
            shared_path = Path(__file__).parent.parent.parent / "shared"
        sys.path.insert(0, str(shared_path))
        
        from aico.core.process import ProcessManager
        
        process_manager = ProcessManager("gateway")
        status = process_manager.get_service_status()
        
        if status["running"]:
            # Double-check with HTTP health check
            config = _get_gateway_config()
            host = config.get('host', '127.0.0.1')
            port = config.get('protocols', {}).get('rest', {}).get('port', 8771)
            
            try:
                response = requests.get(f"http://{host}:{port}/health", timeout=2)
                return response.status_code == 200
            except requests.exceptions.RequestException:
                # Process running but not responding - might be starting up
                return True
        
        return False
        
    except Exception as e:
        # Fallback to simple HTTP check
        try:
            config = _get_gateway_config()
            host = config.get('host', '127.0.0.1')
            port = config.get('protocols', {}).get('rest', {}).get('port', 8771)
            
            response = requests.get(f"http://{host}:{port}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False

def _make_authenticated_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make authenticated request to API Gateway"""
    token = _get_jwt_token()
    if not token:
        raise requests.RequestException("No authentication token available")
    
    config = _get_gateway_config()
    base_url = f"http://{config.get('host', '127.0.0.1')}:{config.get('protocols', {}).get('rest', {}).get('port', 8771)}"
    url = f"{base_url}{endpoint}"
    
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    
    response = getattr(requests, method.lower())(url, headers=headers, **kwargs)
    if response.status_code == 401:
        raise requests.RequestException("Authentication failed - token may be expired")
    return response

def gateway_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("start", "Start the API Gateway service"),
            ("stop", "Stop the API Gateway service"),
            ("restart", "Restart the API Gateway service"),
            ("status", "Show API Gateway status and health"),
            ("config", "Show API Gateway configuration"),
            ("protocols", "List available protocol adapters"),
            ("test", "Test API Gateway connectivity"),
            ("enable", "Enable a protocol adapter"),
            ("disable", "Disable a protocol adapter"),
            ("auth", "JWT authentication management"),
            ("admin", "Administrative operations")
        ]
        
        examples = [
            "aico gateway start",
            "aico gateway status",
            "aico gateway auth login",
            "aico gateway restart"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="gateway",
            description="API Gateway management, protocol control, and JWT authentication",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="API Gateway management, protocol control, and JWT authentication.",
    callback=gateway_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


def _get_gateway_config() -> dict:
    """Get API Gateway configuration from core config"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("api_gateway", {})
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to load gateway configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("start")
def start(
    dev: bool = typer.Option(False, "--dev", help="Start in development mode using UV"),
    detach: bool = typer.Option(True, "--detach/--no-detach", help="Run as background service (default: True)")
):
    """Start the API Gateway service"""
    try:
        # Load config directly inline (WORKING VERSION - DO NOT CHANGE)
        import yaml
        from pathlib import Path
        
        current = Path(__file__).parent.parent.parent
        config_dir = current / "config"
        core_yaml_path = config_dir / "defaults" / "core.yaml"
        
        if core_yaml_path.exists():
            with open(core_yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            config = yaml_content.get("api_gateway", {})
        else:
            config = {}
        
        console.print("[yellow]⏳ Starting API Gateway...[/yellow]")
        
        # Check if already running
        if _is_gateway_running():
            console.print(f"[yellow]{chars['warning']} API Gateway is already running[/yellow]")
            console.print("[dim]Use 'aico gateway status' to check or 'aico gateway restart' to restart[/dim]")
            return
        
        import subprocess
        import sys
        from pathlib import Path
        
        # Path to backend directory
        backend_dir = Path(__file__).parent.parent.parent / "backend"
        backend_main = backend_dir / "main.py"
        
        if not backend_main.exists():
            console.print(f"[red]{chars['cross']} Backend service not found at: {backend_main}[/red]")
            raise typer.Exit(1)
        
        # Get cross-platform Python executable for headless execution
        def get_headless_python(force_visible=False):
            """Get appropriate Python executable for headless execution per platform
            
            Args:
                force_visible: If True, always return visible python (for foreground mode)
            """
            if force_visible or not detach:
                # Foreground mode: Always use regular python to show output
                return sys.executable
            elif sys.platform == "win32":
                # Windows background mode: Use pythonw.exe to avoid console window
                python_dir = Path(sys.executable).parent
                pythonw_exe = python_dir / "pythonw.exe"
                return str(pythonw_exe) if pythonw_exe.exists() else sys.executable
            else:
                # macOS/Linux: Use regular python (process will be detached)
                return sys.executable
        
        # Determine startup method
        if dev:
            # Development mode: Use UV
            use_uv = True
            if use_uv:
                # For UV, use python executable name (UV will resolve the path)
                if detach and sys.platform == "win32":
                    headless_python = "pythonw"  # UV will find pythonw.exe
                else:
                    headless_python = "python"   # UV will find python.exe/python
                cmd = ["uv", "run", "--active", headless_python, str(backend_main)]
                console.print("[yellow]🔧 Starting in development mode (UV)[/yellow]")
            else:
                try:
                    # For UV, use python executable name (UV will resolve the path)
                    if detach and sys.platform == "win32":
                        headless_python = "pythonw"  # UV will find pythonw.exe
                    else:
                        headless_python = "python"   # UV will find python.exe/python
                    cmd = ["uv", "run", headless_python, str(backend_main)]
                    console.print(f"[yellow]{chars['wrench']} Starting in development mode (UV)[/yellow]")
                except FileNotFoundError:
                    console.print(f"[red]{chars['cross']} UV not found. Install UV or use production mode[/red]")
                    raise typer.Exit(1)
        else:
            # Production mode: Try UV first, fallback to pip install
            console.print(f"[blue]{chars['rocket']} Starting in production mode[/blue]")
            
            # Check if UV is available for production use
            try:
                import subprocess
                subprocess.run(["uv", "--version"], capture_output=True, check=True)
                
                # Use UV from root directory to access monorepo shared modules
                # Run backend/main.py from the root directory where pyproject.toml is
                if detach and sys.platform == "win32":
                    headless_python = "pythonw"  # UV will find pythonw.exe
                else:
                    headless_python = "python"   # UV will find python.exe/python
                cmd = ["uv", "run", headless_python, "backend/main.py"]
                console.print("[dim]Using UV for dependency management[/dim]")
                
            except (FileNotFoundError, subprocess.CalledProcessError):
                # Fallback: Install dependencies and use system Python
                console.print(f"[yellow]{chars['warning']} UV not available, installing dependencies with pip[/yellow]")
                
                # Install backend dependencies
                try:
                    install_result = subprocess.run([
                        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
                    ], cwd=str(backend_dir), capture_output=True, text=True)
                    
                    if install_result.returncode != 0:
                        console.print(f"[red]{chars['cross']} Failed to install dependencies: {install_result.stderr}[/red]")
                        raise typer.Exit(1)
                    
                    console.print(f"[green]{chars['check']} Dependencies installed[/green]")
                except Exception as e:
                    console.print(f"[red]{chars['cross']} Failed to install dependencies: {e}[/red]")
                    console.print(f"[yellow]{chars['lightbulb']} Try: 'aico gateway start --dev' or install UV[/yellow]")
                    raise typer.Exit(1)
                
                # Use appropriate Python executable (respects detach mode)
                headless_python = get_headless_python()
                cmd = [headless_python, str(backend_main)]
        
        # Configure process options
        env = dict(os.environ, 
                  AICO_SERVICE_MODE="gateway",
                  AICO_DETACH_MODE="true" if detach else "false")
        
        process_kwargs = {
            "cwd": str(current),  # Run from root directory for monorepo access
            "env": env
        }
        
        if detach:
            # Background service mode (non-blocking)
            if sys.platform == "win32":
                # Windows: Use STARTUPINFO with STARTF_USESHOWWINDOW to hide console
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                process_kwargs.update({
                    "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    "startupinfo": startupinfo,
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "stdin": subprocess.DEVNULL
                })
            else:
                # Unix-like: Standard background process
                process_kwargs.update({
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "stdin": subprocess.DEVNULL,
                    "start_new_session": True
                })
            
            process = subprocess.Popen(cmd, **process_kwargs)
            
            # Give it a moment to start
            import time
            time.sleep(3)
            
            # Verify it started successfully
            if _is_gateway_running():
                host = config.get('host', '127.0.0.1')
                protocols = config.get('protocols', {})
                
                console.print(f"[green]{chars['check']} API Gateway started as background service[/green]")
                console.print()
                
                # Show all enabled protocol endpoints
                console.print(f"[bold blue]{chars['globe']} Available Endpoints:[/bold blue]")
                
                if protocols.get('rest', {}).get('enabled', True):
                    rest_port = protocols.get('rest', {}).get('port', 8771)
                    prefix = protocols.get('rest', {}).get('prefix', '/api/v1')
                    console.print(f"  • REST API: [cyan]http://{host}:{rest_port}{prefix}[/cyan]")
                    console.print(f"  • Health Check: [cyan]http://{host}:{rest_port}/health[/cyan]")
                
                if protocols.get('websocket', {}).get('enabled', False):
                    ws_port = protocols.get('websocket', {}).get('port', 8772)
                    ws_path = protocols.get('websocket', {}).get('path', '/ws')
                    console.print(f"  • WebSocket: [cyan]ws://{host}:{ws_port}{ws_path}[/cyan]")
                
                if protocols.get('grpc', {}).get('enabled', False):
                    grpc_port = protocols.get('grpc', {}).get('port', 8774)
                    console.print(f"  • gRPC: [cyan]grpc://{host}:{grpc_port}[/cyan]")
                
                if protocols.get('zeromq_ipc', {}).get('enabled', True):
                    console.print(f"  • ZeroMQ IPC: [cyan]Platform-specific socket[/cyan]")
                
                console.print()
                console.print(f"[dim]{chars['lightbulb']} Test connection: 'aico gateway test' or 'aico gateway status'[/dim]")
            else:
                console.print(f"[red]{chars['cross']} Failed to start API Gateway service[/red]")
                console.print("[dim]Check logs with 'aico logs cat' for details[/dim]")
                raise typer.Exit(1)
        else:
            # Foreground mode (blocking) - for debugging
            console.print(f"[yellow]{chars['warning']} Running in foreground mode (blocking)[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            console.print()
            
            # Remove background-specific process options for foreground mode
            fg_env = dict(os.environ, 
                         AICO_SERVICE_MODE="gateway",
                         AICO_DETACH_MODE="false")
            
            fg_process_kwargs = {
                "cwd": str(current),  # Run from root directory for monorepo access
                "env": fg_env
            }
            
            # Show the exact command being run
            console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]")
            console.print(f"[dim]Working directory: {current}[/dim]")
            console.print()
            
            # Run in foreground (this should block and show output)
            try:
                console.print("[dim]Starting backend process...[/dim]")
                
                # Use subprocess.run without capture_output to show live output
                # This should block until the process exits
                result = subprocess.run(
                    cmd, 
                    cwd=str(current),
                    env=fg_env,
                    # Don't capture output - let it stream to console
                    stdout=None,
                    stderr=None
                )
                
                console.print(f"[yellow]Backend process exited with code {result.returncode}[/yellow]")
                
                if result.returncode != 0:
                    console.print(f"[red]{chars['cross']} Gateway exited with code {result.returncode}[/red]")
                    raise typer.Exit(result.returncode)
                    
            except FileNotFoundError as e:
                console.print(f"[red]{chars['cross']} Command not found: {e}[/red]")
                console.print(f"[yellow]{chars['lightbulb']} Check if UV is properly installed and backend dependencies are available[/yellow]")
                raise typer.Exit(1)
            except KeyboardInterrupt:
                console.print(f"\n[yellow]{chars['warning']} Backend process interrupted by user[/yellow]")
                raise typer.Exit(0)
            
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{chars['warning']} Gateway startup interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to start gateway: {e}[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """Stop the API Gateway service"""
    try:
        console.print(f"[yellow]{chars['hourglass']} Stopping API Gateway...[/yellow]")
        
        # Use our ProcessManager for proper shutdown
        from pathlib import Path
        import sys
        
        # Add shared module to path
        if getattr(sys, 'frozen', False):
            shared_path = Path(sys._MEIPASS) / 'shared'
        else:
            shared_path = Path(__file__).parent.parent.parent / "shared"
        sys.path.insert(0, str(shared_path))
        
        from aico.core.process import ProcessManager
        
        process_manager = ProcessManager("gateway")
        
        # Try graceful shutdown first
        success = process_manager.stop_service(timeout=30)
        
        if success:
            console.print(f"[green]{chars['check']} API Gateway stopped gracefully[/green]")
        else:
            console.print(f"[yellow]{chars['warning']} Graceful shutdown failed, trying process cleanup...[/yellow]")
            
            # Fallback: Find and terminate gateway processes
            try:
                import psutil
                stopped_count = process_manager.cleanup_stale_processes()
                
                if stopped_count > 0:
                    console.print(f"[green]{chars['check']} Stopped {stopped_count} stale process(es)[/green]")
                else:
                    console.print(f"[yellow]{chars['warning']} No running API Gateway processes found[/yellow]")
                    
            except ImportError:
                console.print(f"[red]{chars['cross']} psutil not available. Cannot stop processes automatically.[/red]")
                console.print("[yellow]Please stop the gateway process manually[/yellow]")
            
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to stop gateway: {e}[/red]")
        raise typer.Exit(1)


@app.command("restart")
def restart():
    """Restart the API Gateway service"""
    console.print(f"[yellow]{chars['restart']} Restarting API Gateway...[/yellow]")
    
    # Stop first
    try:
        stop()
    except typer.Exit:
        pass  # Continue with start even if stop failed
    
    # Wait a moment
    import time
    time.sleep(1)
    
    # Start again
    start()


@app.command("status")
def status():
    """Show API Gateway status and configuration"""
    try:
        # Load config directly inline (WORKING VERSION - DO NOT CHANGE)
        import yaml
        from pathlib import Path
        
        current = Path(__file__).parent.parent.parent
        config_dir = current / "config"
        core_yaml_path = config_dir / "defaults" / "core.yaml"
        
        if core_yaml_path.exists():
            with open(core_yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            config = yaml_content.get("api_gateway", {})
        else:
            config = {}
        
        # Get live status first for primary display
        host = config.get('host', '127.0.0.1')
        rest_port = config.get('rest', {}).get('port', 8771)
        is_running = False
        health_data = {}
        
        try:
            health_response = requests.get(f"http://{host}:{rest_port}/api/v1/health", timeout=3)
            if health_response.status_code == 200:
                is_running = True
                health_data = health_response.json()
        except requests.RequestException:
            # Expected when gateway is not running - status will show as OFFLINE
            # This is not a silent failure - user gets clear feedback via status display
            pass  # Expected failure when gateway not running - status display handles this gracefully
        
        # Enhanced status with process monitoring
        from pathlib import Path
        import sys
        
        # Add shared module to path for ProcessManager
        if getattr(sys, 'frozen', False):
            shared_path = Path(sys._MEIPASS) / 'shared'
        else:
            shared_path = Path(__file__).parent.parent.parent / "shared"
        sys.path.insert(0, str(shared_path))
        
        from aico.core.process import ProcessManager
        
        process_manager = ProcessManager("gateway")
        process_status = process_manager.get_service_status()
        
        # Primary status header with enhanced process info
        if is_running:
            console.print(f"{chars['globe']} [bold green]API Gateway Status: RUNNING[/bold green]")
            if process_status.get("process_info"):
                proc_info = process_status["process_info"]
                uptime = time.time() - proc_info.get("create_time", time.time())
                uptime_str = f"{int(uptime//3600)}h {int((uptime%3600)//60)}m" if uptime > 3600 else f"{int(uptime//60)}m {int(uptime%60)}s"
                console.print(f"   [dim]PID {process_status['pid']} • Uptime {uptime_str} • {host}:{rest_port}[/dim]")
            else:
                console.print(f"   [dim]Version {health_data.get('version', 'Unknown')} • {host}:{rest_port}[/dim]")
        else:
            enabled = config.get("enabled", False)
            if process_status.get("stale_pid"):
                console.print(f"{chars['globe']} [bold yellow]API Gateway Status: STALE PROCESS[/bold yellow]")
                console.print(f"   [dim]PID file exists but process not running • {host}:{rest_port}[/dim]")
            elif enabled:
                console.print(f"{chars['globe']} [bold yellow]API Gateway Status: OFFLINE[/bold yellow]")
                console.print(f"   [dim]Configured but not responding • {host}:{rest_port}[/dim]")
            else:
                console.print(f"{chars['globe']} [bold red]API Gateway Status: DISABLED[/bold red]")
                console.print(f"   [dim]Not enabled in configuration • {host}:{rest_port}[/dim]")
        
        console.print()
        
        # Protocol endpoints table - clean and focused
        protocols = config.get("protocols", {})
        
        # Add REST protocol from separate config section (put first)
        if config.get("rest", {}).get("port"):
            rest_config = {
                "enabled": True,  # REST is always enabled if configured
                "port": config.get("rest", {}).get("port", 8771)
            }
            # Put REST first by creating new ordered dict
            protocols = {"rest": rest_config, **protocols}
        
        if protocols:
            table = Table(title="Protocol Endpoints", show_header=True, header_style="bold blue")
            table.add_column("Protocol", style="cyan", no_wrap=True)
            table.add_column("Status", justify="left")
            table.add_column("Endpoint", style="dim")
            
            for protocol, proto_config in protocols.items():
                proto_enabled = proto_config.get("enabled", False)
                
                if proto_enabled and is_running:
                    status_icon = chars['check']
                    status_text = "Running"
                    status_color = "green"
                elif proto_enabled:
                    status_icon = "○"
                    status_text = "Stopped"
                    status_color = "blue"
                else:
                    status_icon = chars['cross']
                    status_text = "Disabled"
                    status_color = "dim"
                
                # Format endpoint info
                if protocol == "rest":
                    endpoint = f"http://{host}:{proto_config.get('port', 'N/A')}"
                elif protocol == "websocket":
                    endpoint = f"ws://{host}:{proto_config.get('port', 'N/A')}"
                elif protocol == "zeromq_ipc":
                    endpoint = "IPC Socket"
                elif protocol == "grpc":
                    endpoint = f"grpc://{host}:{proto_config.get('port', 'N/A')}"
                else:
                    endpoint = "N/A"
                
                table.add_row(
                    protocol.upper(),
                    f"[{status_color}]{status_icon} {status_text}[/{status_color}]",
                    endpoint
                )
            
            console.print(table)
            console.print()
        
        # Transport Encryption Status
        try:
            # Load security configuration for transport encryption
            security_config_path = config_dir / "defaults" / "security.yaml"
            transport_config = {}
            
            if security_config_path.exists():
                with open(security_config_path, 'r', encoding='utf-8') as f:
                    security_yaml = yaml.safe_load(f)
                transport_config = security_yaml.get("transport_encryption", {})
            
            transport_enabled = transport_config.get("enabled", True)
            algorithm = transport_config.get("algorithm", "XChaCha20-Poly1305")
            
            if transport_enabled:
                console.print(f"{chars['shield']} [bold green]Transport Encryption: ENABLED[/bold green]")
                console.print(f"   [dim]{algorithm} • Ed25519 identity • X25519 sessions[/dim]")
                
                # Session timeout info
                session_timeout = transport_config.get("session", {}).get("timeout_seconds", 3600)
                console.print(f"   [dim]Session timeout: {session_timeout//60}m • Handshake: /api/v1/handshake[/dim]")
            else:
                console.print(f"{chars['shield']} [bold yellow]Transport Encryption: DISABLED[/bold yellow]")
                console.print("   [dim]Using TLS only • No end-to-end encryption[/dim]")
                
        except Exception as e:
            console.print(f"{chars['shield']} [bold red]Transport Encryption: ERROR[/bold red]")
            console.print(f"   [dim]Failed to load config: {e}[/dim]")
        
        console.print()
        
        # Authentication status - clear and actionable
        token = _get_jwt_token()
        if token:
            # Validate token locally using the same JWT secret
            token_valid = False
            try:
                import jwt
                from aico.security.key_manager import AICOKeyManager
                
                key_manager = AICOKeyManager()
                jwt_secret = key_manager.get_jwt_secret("api_gateway")
                
                # Decode and validate the token (skip audience validation for CLI)
                decoded = jwt.decode(
                    token, 
                    jwt_secret, 
                    algorithms=["HS256"],
                    options={"verify_aud": False}  # Skip audience validation for CLI tokens
                )
                token_valid = True
            except jwt.ExpiredSignatureError:
                # Token is actually expired
                token_valid = False
            except Exception:
                # Token is invalid for other reasons
                token_valid = False
            
            if token_valid:
                console.print(f"{chars['key']} [bold green]CLI Authentication: AUTHENTICATED[/bold green]")
                console.print("   [dim]Token is valid and working[/dim]")
            elif is_running:
                console.print(f"{chars['key']} [bold yellow]CLI Authentication: TOKEN EXPIRED[/bold yellow]")
                console.print("   [dim]Run [cyan]aico gateway auth login[/cyan] to refresh[/dim]")
            else:
                console.print(f"{chars['key']} [bold blue]CLI Authentication: READY[/bold blue]")
                console.print("   [dim]Token stored (gateway offline for verification)[/dim]")
        else:
            console.print(f"{chars['key']} [bold red]CLI Authentication: NOT AUTHENTICATED[/bold red]")
            console.print("   [dim]Run [cyan]aico gateway auth login[/cyan] to authenticate[/dim]")
        
        # Process details section
        if process_status.get("metadata") or process_status.get("process_info"):
            console.print()
            console.print(f"{chars['chart']} [bold blue]Process Information:[/bold blue]")
            
            if process_status.get("process_info"):
                proc_info = process_status["process_info"]
                console.print(f"   • CPU Usage: {proc_info.get('cpu_percent', 0):.1f}%")
                console.print(f"   • Memory Usage: {proc_info.get('memory_percent', 0):.1f}%")
                console.print(f"   • Status: {proc_info.get('status', 'Unknown')}")
            
            if process_status.get("metadata"):
                metadata = process_status["metadata"]
                console.print(f"   • Started: {metadata.get('started_at', 'Unknown')}")
                console.print(f"   • Platform: {metadata.get('platform', 'Unknown')}")
                console.print(f"   • Working Dir: {metadata.get('working_directory', 'Unknown')}")
        
        # Quick actions based on status
        console.print()
        if process_status.get("stale_pid"):
            console.print("💡 [bold]Quick Actions:[/bold]")
            console.print("   • [cyan]aico gateway stop[/cyan] - Clean up stale process")
            console.print("   • [cyan]aico gateway start[/cyan] - Start fresh gateway service")
        elif not is_running and config.get("enabled", False):
            console.print("💡 [bold]Quick Actions:[/bold]")
            console.print("   • [cyan]aico gateway start[/cyan] - Start the gateway service")
            console.print("   • [cyan]aico gateway test[/cyan] - Test connectivity")
        elif not config.get("enabled", False):
            console.print("💡 [bold]Quick Actions:[/bold]")
            console.print("   • [cyan]aico config set api_gateway.enabled true[/cyan] - Enable gateway")
            console.print("   • [cyan]aico gateway start[/cyan] - Start the gateway service")
        elif is_running and not token:
            console.print("💡 [bold]Quick Actions:[/bold]")
            console.print("   • [cyan]aico gateway auth login[/cyan] - Authenticate CLI access")
            console.print("   • [cyan]aico gateway test[/cyan] - Test API endpoints")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to get gateway status: {e}[/red]")
        raise typer.Exit(1)


@app.command("config")
def show_config(
    section: Optional[str] = typer.Argument(None, help="Configuration section to show")
):
    """⚙️ Show API Gateway configuration"""
    try:
        # Load config directly inline (WORKING VERSION - DO NOT CHANGE)
        import yaml
        from pathlib import Path
        
        current = Path(__file__).parent.parent.parent
        config_dir = current / "config"
        core_yaml_path = config_dir / "defaults" / "core.yaml"
        
        if core_yaml_path.exists():
            with open(core_yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            config = yaml_content.get("api_gateway", {})
        else:
            config = {}
        
        if section:
            if section in config:
                console.print(Panel(
                    json.dumps(config[section], indent=2),
                    title=f"🔧 Gateway Config: {section}",
                    border_style="blue"
                ))
            else:
                console.print(f"[red]{chars['cross']} Configuration section '{section}' not found[/red]")
                available_sections = list(config.keys())
                console.print(f"Available sections: {', '.join(available_sections)}")
                raise typer.Exit(1)
        else:
            console.print(Panel(
                json.dumps(config, indent=2),
                title="🔧 Gateway Configuration",
                border_style="blue"
            ))
    
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to show configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("protocols")
def list_protocols():
    """🔌 List available protocol adapters"""
    try:
        # Load config directly inline (same pattern as status command)
        import yaml
        from pathlib import Path
        
        current = Path(__file__).parent.parent.parent
        config_dir = current / "config"
        core_yaml_path = config_dir / "defaults" / "core.yaml"
        
        if core_yaml_path.exists():
            with open(core_yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            config = yaml_content.get("api_gateway", {})
        else:
            config = {}
        
        protocols = config.get("protocols", {})
        host = config.get('host', '127.0.0.1')
        
        # Print title following AICO CLI style guide
        console.print("✨ [bold cyan]Protocol Adapters[/bold cyan]\n")
        
        # Use AICO CLI style guide - no emojis in table, SIMPLE_HEAD box
        from rich import box
        table = Table(
            show_header=True, 
            header_style="bold yellow",
            box=box.SIMPLE_HEAD
        )
        table.add_column("Protocol", style="cyan")
        table.add_column("Status")
        table.add_column("Endpoint", style="white")
        table.add_column("Features", style="green")
        
        if not protocols:
            console.print("[yellow]No protocol configuration found[/yellow]")
            return
        
        for protocol_name, protocol_config in protocols.items():
            enabled = protocol_config.get("enabled", False)
            status = "Enabled" if enabled else "Disabled"
            status_color = "green" if enabled else "red"
            
            # Build endpoint
            if protocol_name == "rest":
                port = protocol_config.get("port", 8771)
                prefix = protocol_config.get("prefix", "/api/v1")
                endpoint = f"http://{host}:{port}{prefix}"
                features = "HTTP/JSON, CORS, OpenAPI"
            elif protocol_name == "websocket":
                port = protocol_config.get("port", 8081)
                path = protocol_config.get("path", "/ws")
                endpoint = f"ws://{host}:{port}{path}"
                features = "Real-time, Bidirectional, Subscriptions"
            elif protocol_name == "zeromq_ipc":
                endpoint = "Platform-specific IPC"
                features = "High-performance, Local-only"
            elif protocol_name == "grpc":
                port = protocol_config.get("port", 8083)
                endpoint = f"grpc://{host}:{port}"
                features = "Binary, Streaming, Type-safe"
            else:
                endpoint = "Unknown"
                features = ""
            
            table.add_row(
                protocol_name.upper(), 
                f"[{status_color}]{status}[/{status_color}]", 
                endpoint, 
                features
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to list protocols: {e}[/red]")
        raise typer.Exit(1)


@app.command("test")
def test_gateway():
    """🧪 Test API Gateway connectivity and health"""
    try:
        config = _get_gateway_config()
        
        if not config.get("enabled", True):
            console.print("[yellow]⚠ API Gateway is disabled in configuration[/yellow]")
            return
        
        host = config.get('host', '127.0.0.1')
        protocols = config.get('protocols', {})
        
        console.print("[bold blue]🧪 Testing API Gateway Connectivity[/bold blue]")
        console.print()
        
        # Test if gateway is running
        if not _is_gateway_running():
            console.print(f"[red]{chars['cross']} API Gateway is not running[/red]")
            console.print("[dim]Start it with: 'aico gateway start'[/dim]")
            raise typer.Exit(1)
        
        console.print(f"[green]{chars['check']} API Gateway is running[/green]")
        
        # Test REST API endpoints
        if protocols.get('rest', {}).get('enabled', True):
            rest_port = protocols.get('rest', {}).get('port', 8771)
            prefix = protocols.get('rest', {}).get('prefix', '/api/v1')
            
            try:
                # Test health endpoint
                health_response = requests.get(f"http://{host}:{rest_port}/health", timeout=5)
                if health_response.status_code == 200:
                    console.print(f"[green]{chars['check']} Health endpoint responding: http://{host}:{rest_port}/health[/green]")
                else:
                    console.print(f"[yellow]{chars['warning']} Health endpoint returned {health_response.status_code}[/yellow]")
                
                # Test API root
                api_response = requests.get(f"http://{host}:{rest_port}{prefix}", timeout=5)
                if api_response.status_code in [200, 404]:  # 404 is OK for root API endpoint
                    console.print(f"[green]{chars['check']} REST API responding: http://{host}:{rest_port}{prefix}[/green]")
                else:
                    console.print(f"[yellow]{chars['warning']} REST API returned {api_response.status_code}[/yellow]")
                    
            except requests.RequestException as e:
                console.print(f"[red]{chars['cross']} REST API connection failed: {e}[/red]")
        
        # Test authentication if configured
        auth_config = config.get('auth', {})
        if auth_config:
            console.print(f"[green]{chars['check']} Authentication configured[/green]")
            
            # Check if we have a stored token
            token = _get_jwt_token()
            if token:
                console.print(f"[green]{chars['check']} CLI authentication token found[/green]")
                
                # Test authenticated endpoint
                try:
                    response = _make_authenticated_request("GET", "/api/v1/system/status")
                    if response.status_code == 200:
                        console.print(f"[green]{chars['check']} Authenticated API access working[/green]")
                    else:
                        console.print(f"[yellow]{chars['warning']} Authenticated API returned {response.status_code}[/yellow]")
                except:
                    console.print(f"[yellow]{chars['warning']} Authenticated API test failed (token may be expired)[/yellow]")
            else:
                console.print(f"[yellow]{chars['warning']} No CLI authentication token found[/yellow]")
                console.print("[dim]Run 'aico gateway auth login' to authenticate[/dim]")
        
        # Show enabled protocols summary
        enabled_protocols = [name.upper() for name, cfg in protocols.items() if cfg.get("enabled", name == "rest")]
        if enabled_protocols:
            console.print(f"[green]{chars['check']} Enabled protocols: {', '.join(enabled_protocols)}[/green]")
        
        console.print()
        console.print(f"[green]{chars['party']} API Gateway connectivity test completed![/green]")
        
    except Exception as e:
        console.print(f"[red]{chars['cross']} Gateway test failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("enable")
def enable_protocol(
    protocol: str = typer.Argument(..., help="Protocol to enable (rest, websocket, zeromq_ipc, grpc)")
):
    """🔌 Enable a protocol adapter"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        # Check if protocol exists
        protocols = config_manager.get("api_gateway.protocols", {})
        if protocol not in protocols:
            console.print(f"[red]{chars['cross']} Unknown protocol: {protocol}[/red]")
            available = list(protocols.keys())
            console.print(f"Available protocols: {', '.join(available)}")
            raise typer.Exit(1)
        
        # Enable the protocol
        config_manager.set(f"api_gateway.protocols.{protocol}.enabled", True)
        console.print(f"[green]{chars['check']} {protocol.upper()} protocol enabled[/green]")
        console.print("[yellow]Note: Restart the backend service to apply changes[/yellow]")
        
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to enable protocol: {e}[/red]")
        raise typer.Exit(1)


@app.command("disable")
def disable_protocol(
    protocol: str = typer.Argument(..., help="Protocol to disable (rest, websocket, zeromq_ipc, grpc)")
):
    """Disable a protocol adapter"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        # Check if protocol exists
        protocols = config_manager.get("api_gateway.protocols", {})
        if protocol not in protocols:
            console.print(f"[red]{chars['cross']} Unknown protocol: {protocol}[/red]")
            available = list(protocols.keys())
            console.print(f"Available protocols: {', '.join(available)}")
            raise typer.Exit(1)
        
        # Disable the protocol
        config_manager.set(f"api_gateway.protocols.{protocol}.enabled", False)
        console.print(f"[yellow]{chars['check']} Protocol '{protocol}' disabled[/yellow]")
        console.print("[yellow]Note: Restart the backend service to apply changes[/yellow]")
        
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to disable protocol: {e}[/red]")
        raise typer.Exit(1)


# Authentication subcommand group
auth_app = typer.Typer(help="JWT authentication management")
app.add_typer(auth_app, name="auth")

def admin_callback(ctx: typer.Context):
    """Show help when no admin subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("sessions", "List active user sessions"),
            ("revoke-session", "Revoke a user session")
        ]
        
        examples = [
            "aico gateway admin sessions",
            "aico gateway admin sessions --admin-only",
            "aico gateway admin revoke-session abc123..."
        ]
        
        format_subcommand_help(
            console=console,
            command_name="gateway admin",
            description="Administrative operations for the API Gateway",
            subcommands=subcommands,
            examples=examples
        )

# Admin subcommand group
admin_app = typer.Typer(
    help="Administrative operations", 
    callback=admin_callback,
    invoke_without_command=True
)
app.add_typer(admin_app, name="admin")

@auth_app.command("login")
def auth_login():
    """Generate and store JWT token for CLI authentication (zero-effort security)"""
    try:
        # Check if master password is set up first
        key_manager = AICOKeyManager()
        if not key_manager.has_stored_key():
            console.print("[red]✗ Master password not set up. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
        
        # Generate CLI JWT token directly without backend dependencies
        import jwt
        import time
        from datetime import datetime, timedelta
        
        # Load gateway config to get JWT secret
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        gateway_config = config_manager.get("api_gateway", {})
        auth_config = gateway_config.get("auth", {})
        jwt_config = auth_config.get("jwt", {})
        
        # Get or generate JWT secret using key manager
        jwt_secret = key_manager.get_jwt_secret("api_gateway")
        
        # Get CLI roles from configuration - CLI gets admin access by default
        # This is intentional: CLI operations require admin privileges for system management
        cli_roles = ["cli", "admin"]  # CLI role includes admin privileges
        
        # Create CLI token payload (matching backend admin endpoint expectations)
        now = datetime.utcnow()
        payload = {
            "sub": "aico-cli",  # Subject: AICO CLI
            "username": "aico-cli",  # Username field expected by backend
            "iss": "aico-gateway",  # Issuer: AICO Gateway
            "aud": "aico-api",  # Audience: AICO API
            "iat": int(now.timestamp()),  # Issued at
            "exp": int((now + timedelta(days=7)).timestamp()),  # Expires in 7 days
            "roles": cli_roles,  # CLI gets admin access for system operations
            "type": "cli_token"  # Token type
        }
        
        # Generate JWT token
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        # Store token securely
        _store_jwt_token(token)
        
        console.print("[green]✓ CLI authentication token generated and stored[/green]")
        console.print("[dim]Token valid for 7 days with admin privileges[/dim]")
        
    except ImportError:
        console.print("[red]✗ JWT library not available. Run 'uv pip install -r requirements.txt' in CLI directory[/red]")
        raise typer.Exit(1)
    except Exception as e:
        if "JWT secret" in str(e) or "key" in str(e).lower():
            console.print(f"[red]✗ JWT secrets not initialized: {e}[/red]")
            console.print("[yellow]Run 'aico security setup' to initialize security keys[/yellow]")
        else:
            console.print(f"[red]✗ Failed to generate authentication token: {e}[/red]")
        raise typer.Exit(1)

@auth_app.command("logout")
def auth_logout():
    """Remove stored JWT token"""
    try:
        key_manager = AICOKeyManager()
        if key_manager.remove_jwt_token("api_gateway"):
            console.print("[green]✓ Authentication token removed from secure keyring[/green]")
        else:
            console.print("[yellow]⚠ No authentication token found or failed to remove[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to remove token: {e}[/red]")

@auth_app.command("status")
def auth_status():
    """Check authentication status"""
    token = _get_jwt_token()
    if token:
        try:
            console.print("[green]✓ Authentication token found in secure keyring[/green]")
            
            # Validate token locally using the same logic as status command
            try:
                import jwt
                from aico.security.key_manager import AICOKeyManager
                
                key_manager = AICOKeyManager()
                jwt_secret = key_manager.get_jwt_secret("api_gateway")
                
                # Decode and validate the token (skip audience validation for CLI)
                decoded = jwt.decode(
                    token, 
                    jwt_secret, 
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
                
                # Show token details
                from datetime import datetime
                exp_time = datetime.fromtimestamp(decoded.get('exp', 0))
                console.print(f"[green]✓ Token is valid and properly signed[/green]")
                console.print(f"[dim]Subject: {decoded.get('sub', 'Unknown')}[/dim]")
                console.print(f"[dim]Username: {decoded.get('username', 'Unknown')}[/dim]")
                console.print(f"[dim]Roles: {', '.join(decoded.get('roles', []))}[/dim]")
                console.print(f"[dim]Expires: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                
            except jwt.ExpiredSignatureError:
                console.print("[red]✗ Token has expired[/red]")
                console.print("[dim]Run 'aico gateway auth login' to refresh[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Token validation error: {e}[/yellow]")
                
        except Exception as e:
            console.print(f"[red]✗ Error checking token: {e}[/red]")
    else:
        console.print("[red]✗ No authentication token found in keyring[/red]")
        console.print("[dim]Run 'aico gateway auth login' to authenticate[/dim]")


# Admin commands
@admin_app.command("sessions")
def admin_list_sessions(
    user_uuid: Optional[str] = typer.Option(None, "--user", help="Filter by specific user UUID"),
    admin_only: bool = typer.Option(False, "--admin-only", help="Show only admin sessions"),
    include_stats: bool = typer.Option(True, "--stats/--no-stats", help="Include session statistics")
):
    """📋 List active user sessions"""
    try:
        # Build query parameters
        params = {}
        if user_uuid:
            params["user_uuid"] = user_uuid
        if admin_only:
            params["admin_only"] = "true"
        if not include_stats:
            params["include_stats"] = "false"
        
        # Make authenticated request to admin endpoint
        response = _make_authenticated_request("get", "/admin/auth/sessions", params=params)
        data = response.json()
        
        console.print("\n🔐 [bold cyan]Active Sessions[/bold cyan]\n")
        
        # Display sessions
        sessions = data.get("sessions", [])
        if not sessions:
            console.print("[yellow]No active sessions found[/yellow]")
            return
        
        # Create sessions table
        table = Table(
            title=f"Sessions ({data.get('total', 0)} total)",
            show_header=True,
            header_style="bold magenta",
            border_style="blue"
        )
        
        table.add_column("Session ID", style="cyan", width=12)
        table.add_column("User", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")
        table.add_column("Last Active", style="dim")
        table.add_column("IP Address", style="blue")
        
        for session in sessions:
            # Truncate session ID for display
            session_id = session.get("session_id", "")[:8] + "..."
            user_uuid = session.get("user_uuid", "Unknown")
            status = session.get("status", "unknown").title()
            created = session.get("created_at", "")[:19] if session.get("created_at") else "Unknown"
            last_active = session.get("last_accessed_at", "")[:19] if session.get("last_accessed_at") else "Unknown"
            ip_address = session.get("ip_address", "Unknown")
            
            # Color code status
            if status.lower() == "active":
                status = f"[green]{status}[/green]"
            elif status.lower() == "expired":
                status = f"[red]{status}[/red]"
            
            table.add_row(session_id, user_uuid, status, created, last_active, ip_address)
        
        console.print(table)
        
        # Display statistics if included
        if include_stats and "stats" in data:
            stats = data["stats"]
            console.print(f"\n{chars['chart']} [bold cyan]Session Statistics[/bold cyan]")
            
            stats_table = Table(show_header=False, border_style="dim")
            stats_table.add_column("Metric", style="bold white")
            stats_table.add_column("Count", style="cyan")
            
            stats_table.add_row("Total Sessions", str(stats.get("total_sessions", 0)))
            stats_table.add_row("Active Sessions", str(stats.get("active_sessions", 0)))
            stats_table.add_row("Admin Sessions", str(stats.get("admin_sessions", 0)))
            stats_table.add_row("Expired Sessions", str(stats.get("expired_sessions", 0)))
            stats_table.add_row("Revoked Sessions", str(stats.get("revoked_sessions", 0)))
            
            console.print(stats_table)
        
    except requests.RequestException as e:
        if "No authentication token" in str(e):
            console.print("[red]✗ Not authenticated. Run 'aico gateway auth login' first[/red]")
        elif "Authentication failed" in str(e):
            console.print("[red]✗ Authentication failed. Token may be expired[/red]")
            console.print("[dim]Run 'aico gateway auth login' to refresh token[/dim]")
        else:
            console.print(f"[red]✗ Request failed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to list sessions: {e}[/red]")
        raise typer.Exit(1)

@admin_app.command("revoke-session") 
def admin_revoke_session(
    session_id: str = typer.Argument(..., help="Session ID to revoke")
):
    """Revoke a user session"""
    try:
        # Make authenticated request to revoke session
        response = _make_authenticated_request("delete", f"/admin/auth/sessions/{session_id}")
        
        if response.status_code == 200:
            console.print(f"[green]✓ Session {session_id} revoked successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to revoke session: {response.text}[/red]")
            raise typer.Exit(1)
            
    except requests.RequestException as e:
        if "No authentication token" in str(e):
            console.print("[red]✗ Not authenticated. Run 'aico gateway auth login' first[/red]")
        elif "Authentication failed" in str(e):
            console.print("[red]✗ Authentication failed. Token may be expired[/red]")
            console.print("[dim]Run 'aico gateway auth login' to refresh token[/dim]")
        else:
            console.print(f"[red]✗ Request failed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to revoke session: {e}[/red]")
        raise typer.Exit(1)




if __name__ == "__main__":
    app()
