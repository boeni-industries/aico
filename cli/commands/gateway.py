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
from cli.utils.docker_client import DockerClient

console = Console()

# Get platform-appropriate characters
chars = get_platform_chars()

def _get_jwt_token() -> Optional[str]:
    """Get stored JWT token for CLI authentication from secure keyring"""
    try:
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        return key_manager.get_jwt_token("api_gateway")
    except Exception:
        return None

def _store_jwt_token(token: str) -> None:
    """Store JWT token for CLI authentication in secure keyring"""
    try:
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        key_manager.store_jwt_token("api_gateway", token)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to store JWT token in keyring: {e}[/yellow]")
        console.print("[dim]Token generated but not persisted - you may need to login again[/dim]")


def _is_gateway_running() -> bool:
    """Check if API Gateway is currently running"""
    try:
        # Docker-first: check container status
        if DockerClient.is_docker_available() and DockerClient.is_docker_running():
            if DockerClient.is_service_running("gateway"):
                return True

        # Fallback: HTTP check (useful when running outside Docker)
        config = _get_gateway_config()
        host = config.get('host', '127.0.0.1')
        port = config.get('protocols', {}).get('rest', {}).get('port', 8771)

        response = requests.get(f"http://{host}:{port}/api/v1/health", timeout=2)
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
            "aico gateway status",
            "aico gateway auth login",
            "aico gateway test",
            "aico deploy up  # Start services"
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


@app.command("status")
def status():
    """Show API Gateway status and configuration"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        config = config_manager.get("api_gateway", {})
        
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

        container_info = None
        if DockerClient.is_docker_available() and DockerClient.is_docker_running():
            container_info = DockerClient.get_container_status(DockerClient.AICO_SERVICES.get("gateway", ""))

        process_status: dict = {"metadata": None, "process_info": None, "stale_pid": False}

        # Primary status header
        if is_running:
            console.print(f"{chars['globe']} [bold green]API Gateway Status: RUNNING[/bold green]")
            if container_info and container_info.container_id:
                console.print(f"   [dim]Container {container_info.container_id} • {host}:{rest_port}[/dim]")
            else:
                console.print(f"   [dim]Version {health_data.get('version', 'Unknown')} • {host}:{rest_port}[/dim]")
        else:
            enabled = config.get("enabled", False)
            if enabled:
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
            # Use ConfigurationManager instead of direct YAML access
            config_manager = ConfigurationManager()
            config_manager.initialize(lightweight=True)
            transport_config = config_manager.get("security.transport", {})
            
            transport_enabled = transport_config.get("encryption_enabled", True)
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
                
                config = ConfigurationManager()
                key_manager = AICOKeyManager(config)
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
        # Use ConfigurationManager instead of direct YAML access
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        config = config_manager.get("api_gateway", {})
        
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
        # Use ConfigurationManager instead of direct YAML access
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        config = config_manager.get("api_gateway", {})
        
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
        console.print(f"[green]{chars.get('party', chars['check'])} API Gateway connectivity test completed![/green]")
        
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
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
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
        
        # Auto-detect active user from database
        from cli.utils.pg_connection import get_pg_connection
        try:
            db = get_pg_connection()
            cursor = db.cursor()
            cursor.execute("SELECT uuid FROM aico_core.user_profiles WHERE is_active = true LIMIT 1")
            user_row = cursor.fetchone()
            
            if user_row:
                user_id = user_row["uuid"]
            else:
                user_id = config_manager.get("core.user.id", "aico-cli")
        except Exception:
            # Fallback to config on any DB error
            user_id = config_manager.get("core.user.id", "aico-cli")
        
        # Get CLI roles from configuration - CLI gets admin access by default
        # This is intentional: CLI operations require admin privileges for system management
        cli_roles = ["cli", "admin"]  # CLI role includes admin privileges
        
        # Create CLI token payload (matching backend admin endpoint expectations)
        now = datetime.utcnow()
        payload = {
            "sub": user_id,  # Subject: configured user or CLI
            "user_uuid": user_id,  # User identifier from config
            "username": user_id,
            "roles": cli_roles,
            "permissions": [],  # CLI has full access via admin role
            "iat": int(now.timestamp()),  # Issued at
            "exp": int((now + timedelta(days=7)).timestamp()),  # Expires in 7 days
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
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
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
                
                config = ConfigurationManager()
                key_manager = AICOKeyManager(config)
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
