"""
AICO CLI Gateway Commands

Provides API Gateway management, protocol control, and JWT authentication.
"""

import typer
import json
import requests
import os
import sys
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
from sensitive import sensitive, destructive

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager

# Windows CMD Unicode handling - must be after imports
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

console = Console()

# JWT token storage path
JWT_TOKEN_FILE = Path.home() / ".aico" / "gateway_token"

def _get_jwt_token() -> Optional[str]:
    """Get stored JWT token for CLI authentication"""
    try:
        if JWT_TOKEN_FILE.exists():
            return JWT_TOKEN_FILE.read_text().strip()
        return None
    except Exception:
        return None

def _store_jwt_token(token: str) -> None:
    """Store JWT token for CLI authentication"""
    try:
        JWT_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        JWT_TOKEN_FILE.write_text(token)
    except Exception:
        pass


def _is_gateway_running() -> bool:
    """Check if API Gateway is currently running"""
    try:
        config = _get_gateway_config()
        host = config.get('host', '127.0.0.1')
        port = config.get('protocols', {}).get('rest', {}).get('port', 8771)
        
        # Simple health check without authentication
        response = requests.get(f"http://{host}:{port}/health", timeout=2)
        return response.status_code == 200
    except:
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

def gateway_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
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
            ("auth", "JWT authentication management")
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
    invoke_without_command=True
)


def _get_gateway_config() -> dict:
    """Get API Gateway configuration from core config"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("api_gateway", {})
    except Exception as e:
        console.print(f"[red]✗ Failed to load gateway configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("start")
def start(
    dev: bool = typer.Option(False, "--dev", help="Start in development mode using UV"),
    detach: bool = typer.Option(True, "--detach/--no-detach", help="Run as background service (default: True)")
):
    """🚀 Start the API Gateway service"""
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
            console.print("[yellow]⚠ API Gateway is already running[/yellow]")
            console.print("[dim]Use 'aico gateway status' to check or 'aico gateway restart' to restart[/dim]")
            return
        
        import subprocess
        import sys
        from pathlib import Path
        
        # Path to backend directory
        backend_dir = Path(__file__).parent.parent.parent / "backend"
        backend_main = backend_dir / "main.py"
        
        if not backend_main.exists():
            console.print(f"[red]✗ Backend service not found at: {backend_main}[/red]")
            raise typer.Exit(1)
        
        # Determine startup method
        if dev:
            # Development mode: Use UV
            use_uv = True
            if use_uv:
                cmd = ["uv", "run", "--active", "python", str(backend_main)]
                console.print("[yellow]🔧 Starting in development mode (UV)[/yellow]")
            else:
                try:
                    cmd = ["uv", "run", "python", str(backend_main)]
                    console.print("[yellow]🔧 Starting in development mode (UV)[/yellow]")
                except FileNotFoundError:
                    console.print("[red]✗ UV not found. Install UV or use production mode[/red]")
                    raise typer.Exit(1)
        else:
            # Production mode: Try UV first, fallback to pip install
            console.print("[blue]🚀 Starting in production mode[/blue]")
            
            # Check if UV is available for production use
            try:
                import subprocess
                subprocess.run(["uv", "--version"], capture_output=True, check=True)
                
                # Use UV without --active flag - let UV manage backend's own environment
                # The key is that UV will run in backend_dir, so it uses backend's pyproject.toml/requirements.txt
                cmd = ["uv", "run", "python", "main.py"]
                console.print("[dim]Using UV for dependency management[/dim]")
                
            except (FileNotFoundError, subprocess.CalledProcessError):
                # Fallback: Install dependencies and use system Python
                console.print("[yellow]⚠ UV not available, installing dependencies with pip[/yellow]")
                
                # Install backend dependencies
                try:
                    install_result = subprocess.run([
                        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
                    ], cwd=str(backend_dir), capture_output=True, text=True)
                    
                    if install_result.returncode != 0:
                        console.print(f"[red]✗ Failed to install dependencies: {install_result.stderr}[/red]")
                        raise typer.Exit(1)
                    
                    console.print("[green]✓ Dependencies installed[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Failed to install dependencies: {e}[/red]")
                    console.print("[yellow]💡 Try: 'aico gateway start --dev' or install UV[/yellow]")
                    raise typer.Exit(1)
                
                cmd = [sys.executable, str(backend_main)]
        
        # Configure process options
        process_kwargs = {
            "cwd": str(backend_dir),
            "env": dict(os.environ, AICO_SERVICE_MODE="gateway")
        }
        
        if detach:
            # Background service mode (non-blocking)
            if sys.platform == "win32":
                # Windows: Use DETACHED_PROCESS to run in background
                process_kwargs.update({
                    "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
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
                
                console.print("[green]✓ API Gateway started as background service[/green]")
                console.print()
                
                # Show all enabled protocol endpoints
                console.print("[bold blue]🌐 Available Endpoints:[/bold blue]")
                
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
                console.print("[dim]💡 Test connection: 'aico gateway test' or 'aico gateway status'[/dim]")
            else:
                console.print("[red]✗ Failed to start API Gateway service[/red]")
                console.print("[dim]Check logs with 'aico logs cat' for details[/dim]")
                raise typer.Exit(1)
        else:
            # Foreground mode (blocking) - for debugging
            console.print("[yellow]⚠ Running in foreground mode (blocking)[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            console.print()
            
            # Remove background-specific process options for foreground mode
            fg_process_kwargs = {
                "cwd": str(backend_dir),
                "env": dict(os.environ, AICO_SERVICE_MODE="gateway")
            }
            
            # Show the exact command being run
            console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]")
            console.print(f"[dim]Working directory: {backend_dir}[/dim]")
            console.print()
            
            # Run in foreground (this should block and show output)
            try:
                console.print("[dim]Starting backend process...[/dim]")
                
                # Use subprocess.run without capture_output to show live output
                # This should block until the process exits
                result = subprocess.run(
                    cmd, 
                    cwd=str(backend_dir),
                    env=dict(os.environ, AICO_SERVICE_MODE="gateway"),
                    # Don't capture output - let it stream to console
                    stdout=None,
                    stderr=None
                )
                
                console.print(f"[yellow]Backend process exited with code {result.returncode}[/yellow]")
                
                if result.returncode != 0:
                    console.print(f"[red]✗ Gateway exited with code {result.returncode}[/red]")
                    raise typer.Exit(result.returncode)
                    
            except FileNotFoundError as e:
                console.print(f"[red]✗ Command not found: {e}[/red]")
                console.print(f"[yellow]💡 Check if UV is properly installed and backend dependencies are available[/yellow]")
                raise typer.Exit(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠ Backend process interrupted by user[/yellow]")
                raise typer.Exit(0)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Gateway startup interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to start gateway: {e}[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """🛑 Stop the API Gateway service"""
    try:
        console.print("[yellow]⏳ Stopping API Gateway...[/yellow]")
        
        # Find and terminate gateway processes
        import psutil
        
        stopped_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('main.py' in arg and 'backend' in arg for arg in cmdline):
                    proc.terminate()
                    stopped_count += 1
                    console.print(f"[yellow]Terminated process {proc.info['pid']}[/yellow]")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if stopped_count > 0:
            console.print(f"[green]✓ Stopped {stopped_count} API Gateway process(es)[/green]")
        else:
            console.print("[yellow]⚠ No running API Gateway processes found[/yellow]")
            
    except ImportError:
        console.print("[red]✗ psutil not available. Cannot stop processes automatically.[/red]")
        console.print("[yellow]Please stop the gateway process manually[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to stop gateway: {e}[/red]")
        raise typer.Exit(1)


@app.command("restart")
def restart():
    """🔄 Restart the API Gateway service"""
    console.print("[yellow]🔄 Restarting API Gateway...[/yellow]")
    
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
        
        # Create status table
        table = Table(title="🌐 API Gateway Status", show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        # Gateway status
        enabled = config.get("enabled", False)
        status_color = "green" if enabled else "red"
        status_text = "✓ Enabled" if enabled else "✗ Disabled"
        table.add_row("Gateway", f"[{status_color}]{status_text}[/{status_color}]", f"Host: {config.get('host', 'N/A')}")
        
        # Try to get live status from running gateway (public health check first)
        try:
            # First try public health endpoint (no auth required)
            host = config.get('host', '127.0.0.1')
            rest_port = config.get('protocols', {}).get('rest', {}).get('port', 8771)
            health_response = requests.get(f"http://{host}:{rest_port}/health", timeout=3)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                table.add_row("Live Status", "[green]✓ Running[/green]", f"Version: {health_data.get('version', 'N/A')}")
                
                # Try authenticated status for more details (optional)
                token = _get_jwt_token()
                if token:
                    try:
                        auth_response = _make_authenticated_request("GET", "/api/v1/system/status")
                        if auth_response.status_code == 200:
                            auth_data = auth_response.json()
                            if 'uptime' in auth_data:
                                table.add_row("Uptime", "[green]✓ Available[/green]", f"{auth_data.get('uptime', 'N/A')}")
                    except:
                        pass  # Auth failed, but we already have basic status
            else:
                table.add_row("Live Status", "[red]✗ Not responding[/red]", f"HTTP {health_response.status_code}")
                
        except requests.RequestException:
            table.add_row("Live Status", "[yellow]○ Offline[/yellow]", "Cannot connect")
        
        # Protocol status
        protocols = config.get("protocols", {})
        for protocol, proto_config in protocols.items():
            proto_enabled = proto_config.get("enabled", False)
            proto_color = "green" if proto_enabled else "yellow"
            proto_status = "✓ Active" if proto_enabled else "○ Inactive"
            
            if protocol == "rest":
                details = f"Port: {proto_config.get('port', 'N/A')}"
            elif protocol == "websocket":
                details = f"Port: {proto_config.get('port', 'N/A')}"
            elif protocol == "zeromq_ipc":
                details = "IPC Socket"
            elif protocol == "grpc":
                details = f"Port: {proto_config.get('port', 'N/A')}"
            else:
                details = "N/A"
                
            table.add_row(f"{protocol.upper()}", f"[{proto_color}]{proto_status}[/{proto_color}]", details)
        
        console.print(table)
        
        # Show authentication status
        token = _get_jwt_token()
        auth_status = "[green]✓ Authenticated[/green]" if token else "[red]✗ Not authenticated[/red]"
        console.print(f"\n🔐 CLI Authentication: {auth_status}")
        if not token:
            console.print("[dim]Run 'aico gateway auth login' to authenticate[/dim]")
        
        # Show available authentication methods from config
        auth_config = config.get("auth", {})
        auth_methods = []
        if auth_config.get("jwt"):
            auth_methods.append("JWT")
        if auth_config.get("api_key"):
            auth_methods.append("API Key")
        if auth_config.get("session"):
            auth_methods.append("Session")
            
        if auth_methods:
            auth_panel = Panel(
                f"Authentication: {', '.join(auth_methods)}",
                title="🔒 Security",
                border_style="green"
            )
            console.print(auth_panel)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to get gateway status: {e}[/red]")
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
                console.print(f"[red]✗ Configuration section '{section}' not found[/red]")
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
        console.print(f"[red]✗ Failed to show configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("protocols")
def list_protocols():
    """🔌 List available protocol adapters"""
    try:
        config = _get_gateway_config()
        protocols = config.get("protocols", {})
        
        table = Table(title="🔌 Protocol Adapters", show_header=True, header_style="bold blue")
        table.add_column("Protocol", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Endpoint", style="dim")
        table.add_column("Features", style="green")
        
        for protocol_name, protocol_config in protocols.items():
            enabled = protocol_config.get("enabled", False)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            
            # Build endpoint
            if protocol_name == "rest":
                port = protocol_config.get("port", 8771)
                prefix = protocol_config.get("prefix", "/api/v1")
                endpoint = f"http://127.0.0.1:{port}{prefix}"
                features = "HTTP/JSON, CORS, OpenAPI"
            elif protocol_name == "websocket":
                port = protocol_config.get("port", 8081)
                path = protocol_config.get("path", "/ws")
                endpoint = f"ws://127.0.0.1:{port}{path}"
                features = "Real-time, Bidirectional, Subscriptions"
            elif protocol_name == "zeromq_ipc":
                endpoint = "Platform-specific IPC"
                features = "High-performance, Local-only"
            elif protocol_name == "grpc":
                port = protocol_config.get("port", 8083)
                endpoint = f"grpc://127.0.0.1:{port}"
                features = "Binary, Streaming, Type-safe"
            else:
                endpoint = "Unknown"
                features = ""
            
            table.add_row(protocol_name.upper(), status, endpoint, features)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to list protocols: {e}[/red]")
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
            console.print("[red]✗ API Gateway is not running[/red]")
            console.print("[dim]Start it with: 'aico gateway start'[/dim]")
            raise typer.Exit(1)
        
        console.print("[green]✓ API Gateway is running[/green]")
        
        # Test REST API endpoints
        if protocols.get('rest', {}).get('enabled', True):
            rest_port = protocols.get('rest', {}).get('port', 8771)
            prefix = protocols.get('rest', {}).get('prefix', '/api/v1')
            
            try:
                # Test health endpoint
                health_response = requests.get(f"http://{host}:{rest_port}/health", timeout=5)
                if health_response.status_code == 200:
                    console.print(f"[green]✓ Health endpoint responding: http://{host}:{rest_port}/health[/green]")
                else:
                    console.print(f"[yellow]⚠ Health endpoint returned {health_response.status_code}[/yellow]")
                
                # Test API root
                api_response = requests.get(f"http://{host}:{rest_port}{prefix}", timeout=5)
                if api_response.status_code in [200, 404]:  # 404 is OK for root API endpoint
                    console.print(f"[green]✓ REST API responding: http://{host}:{rest_port}{prefix}[/green]")
                else:
                    console.print(f"[yellow]⚠ REST API returned {api_response.status_code}[/yellow]")
                    
            except requests.RequestException as e:
                console.print(f"[red]✗ REST API connection failed: {e}[/red]")
        
        # Test authentication if configured
        auth_config = config.get('auth', {})
        if auth_config:
            console.print(f"[green]✓ Authentication configured[/green]")
            
            # Check if we have a stored token
            token = _get_jwt_token()
            if token:
                console.print("[green]✓ CLI authentication token found[/green]")
                
                # Test authenticated endpoint
                try:
                    response = _make_authenticated_request("GET", "/api/v1/system/status")
                    if response.status_code == 200:
                        console.print("[green]✓ Authenticated API access working[/green]")
                    else:
                        console.print(f"[yellow]⚠ Authenticated API returned {response.status_code}[/yellow]")
                except:
                    console.print("[yellow]⚠ Authenticated API test failed (token may be expired)[/yellow]")
            else:
                console.print("[yellow]⚠ No CLI authentication token found[/yellow]")
                console.print("[dim]Run 'aico gateway auth login' to authenticate[/dim]")
        
        # Show enabled protocols summary
        enabled_protocols = [name.upper() for name, cfg in protocols.items() if cfg.get("enabled", name == "rest")]
        if enabled_protocols:
            console.print(f"[green]✓ Enabled protocols: {', '.join(enabled_protocols)}[/green]")
        
        console.print()
        console.print("[green]🎉 API Gateway connectivity test completed![/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Gateway test failed: {e}[/red]")
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
            console.print(f"[red]✗ Unknown protocol: {protocol}[/red]")
            available = list(protocols.keys())
            console.print(f"Available protocols: {', '.join(available)}")
            raise typer.Exit(1)
        
        # Enable the protocol
        config_manager.set(f"api_gateway.protocols.{protocol}.enabled", True)
        console.print(f"[green]✓ {protocol.upper()} protocol enabled[/green]")
        console.print("[yellow]Note: Restart the backend service to apply changes[/yellow]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to enable protocol: {e}[/red]")
        raise typer.Exit(1)


@app.command("disable")
def disable_protocol(
    protocol: str = typer.Argument(..., help="Protocol to disable (rest, websocket, zeromq_ipc, grpc)")
):
    """🚫 Disable a protocol adapter"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        # Check if protocol exists
        protocols = config_manager.get("api_gateway.protocols", {})
        if protocol not in protocols:
            console.print(f"[red]✗ Unknown protocol: {protocol}[/red]")
            available = list(protocols.keys())
            console.print(f"Available protocols: {', '.join(available)}")
            raise typer.Exit(1)
        
        # Disable the protocol
        config_manager.set(f"api_gateway.protocols.{protocol}.enabled", False)
        console.print(f"[yellow]✓ Protocol '{protocol}' disabled[/yellow]")
        console.print("[yellow]Note: Restart the backend service to apply changes[/yellow]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to disable protocol: {e}[/red]")
        raise typer.Exit(1)


# Authentication subcommand group
auth_app = typer.Typer(help="JWT authentication management")
app.add_typer(auth_app, name="auth")

@auth_app.command("login")
def auth_login():
    """Generate and store JWT token for CLI authentication (zero-effort security)"""
    try:
        # Check if JWT secrets are initialized first
        key_manager = AICOKeyManager()
        if not key_manager.has_stored_key():
            console.print("[red]✗ Master password not set up. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
        
        # Import auth manager to generate CLI token
        import sys
        from pathlib import Path
        
        # Add backend to path temporarily for import
        backend_dir = Path(__file__).parent.parent.parent / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        try:
            from api_gateway.core.auth import AuthenticationManager
        except ImportError as ie:
            console.print(f"[red]✗ Cannot import AuthenticationManager: {ie}[/red]")
            console.print("[yellow]💡 Make sure backend dependencies are installed with 'uv sync' in backend directory[/yellow]")
            raise typer.Exit(1)
        
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        auth_manager = AuthenticationManager(config_manager.get_all())
        token = auth_manager.generate_cli_token()
        
        # Store token securely
        _store_jwt_token(token)
        
        console.print("[green]✓ CLI authentication token generated and stored[/green]")
        console.print("[dim]Token valid for 7 days with admin privileges[/dim]")
        
    except Exception as e:
        if "JWT secret" in str(e):
            console.print(f"[red]✗ JWT secrets not initialized: {e}[/red]")
            console.print("[yellow]Run 'aico security setup --jwt-only' to initialize JWT secrets[/yellow]")
        else:
            console.print(f"[red]✗ Failed to generate authentication token: {e}[/red]")
        raise typer.Exit(1)

@auth_app.command("logout")
def auth_logout():
    """Remove stored JWT token"""
    try:
        if JWT_TOKEN_FILE.exists():
            JWT_TOKEN_FILE.unlink()
            console.print("[green]✓ Authentication token removed[/green]")
        else:
            console.print("[yellow]⚠ No authentication token found[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to remove token: {e}[/red]")

@auth_app.command("status")
def auth_status():
    """Check authentication status"""
    token = _get_jwt_token()
    if token:
        try:
            console.print("[green]✓ Authentication token found[/green]")
            console.print(f"[dim]Token stored at: {JWT_TOKEN_FILE}[/dim]")
            
            # Test token by making a simple request
            try:
                response = _make_authenticated_request("GET", "/api/v1/system/status")
                if response.status_code == 200:
                    console.print("[green]✓ Token is valid and working[/green]")
                else:
                    console.print("[yellow]⚠ Token may be expired or invalid[/yellow]")
            except:
                console.print("[yellow]⚠ Could not verify token (gateway may be offline)[/yellow]")
                
        except Exception as e:
            console.print(f"[red]✗ Error checking token: {e}[/red]")
    else:
        console.print("[red]✗ No authentication token found[/red]")
        console.print("[dim]Run 'aico gateway auth login' to authenticate[/dim]")


if __name__ == "__main__":
    app()
