import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Optional
import json
import os
import requests
from pathlib import Path

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.security.key_manager import AICOKeyManager

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
import sys
sys.path.insert(0, str(decorators_path))
from sensitive import sensitive, destructive

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

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
        JWT_TOKEN_FILE.chmod(0o600)  # Secure permissions
    except Exception as e:
        console.print(f"[red]✗ Failed to store JWT token: {e}[/red]")

def _make_authenticated_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make authenticated request to API Gateway"""
    token = _get_jwt_token()
    if not token:
        console.print("[red]✗ No authentication token found. Run 'aico gateway auth login' first.[/red]")
        raise typer.Exit(1)
    
    config = _get_gateway_config()
    base_url = f"http://{config.get('host', '127.0.0.1')}:{config.get('protocols', {}).get('rest', {}).get('port', 8771)}"
    url = f"{base_url}{endpoint}"
    
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = getattr(requests, method.lower())(url, headers=headers, **kwargs)
        if response.status_code == 401:
            console.print("[red]✗ Authentication failed. Token may be expired. Run 'aico gateway auth login' again.[/red]")
            raise typer.Exit(1)
        return response
    except requests.RequestException as e:
        console.print(f"[red]✗ Request failed: {e}[/red]")
        raise typer.Exit(1)

def gateway_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("status", "Show API Gateway status and health"),
            ("config", "Show API Gateway configuration"),
            ("protocols", "List available protocol adapters"),
            ("test", "Test API Gateway connectivity"),
            ("enable", "Enable a protocol adapter"),
            ("disable", "Disable a protocol adapter")
        ]
        
        format_subcommand_help(
            console=console,
            title="🌐 API Gateway Commands",
            subtitle="Manage the AICO API Gateway and protocol adapters",
            subcommands=subcommands,
            examples=[
                "aico gateway status",
                "aico gateway protocols", 
                "aico gateway enable websocket",
                "aico gateway test"
            ]
        )

app = typer.Typer(callback=gateway_callback)


def _get_gateway_config() -> dict:
    """Get API Gateway configuration from core config"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("api_gateway", {})
    except Exception as e:
        console.print(f"[red]✗ Failed to load gateway configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status():
    """Show API Gateway status and configuration"""
    try:
        config = _get_gateway_config()
        
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
        
        # Try to get live status from running gateway
        try:
            response = _make_authenticated_request("GET", "/api/v1/system/status")
            if response.status_code == 200:
                live_status = response.json()
                table.add_row("Live Status", "[green]✓ Running[/green]", f"Uptime: {live_status.get('uptime', 'N/A')}")
            else:
                table.add_row("Live Status", "[red]✗ Not responding[/red]", f"HTTP {response.status_code}")
        except:
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
        config = _get_gateway_config()
        
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
    """🧪 Test API Gateway connectivity"""
    try:
        config = _get_gateway_config()
        
        if not config.get("enabled", True):
            console.print("[yellow]⚠ API Gateway is disabled in configuration[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Test configuration loading
            task = progress.add_task("Testing configuration...", total=None)
            progress.update(task, description="✅ Configuration loaded")
            
            # Test protocol endpoints
            protocols = config.get("protocols", {})
            enabled_protocols = [name for name, cfg in protocols.items() if cfg.get("enabled")]
            
            if enabled_protocols:
                progress.update(task, description=f"✅ Found {len(enabled_protocols)} enabled protocols")
                console.print(f"[green]✓ Enabled protocols: {', '.join(enabled_protocols)}[/green]")
            else:
                console.print("[yellow]⚠ No protocols enabled[/yellow]")
            
            # Test admin interface
            admin_config = config.get("admin", {})
            if admin_config.get("enabled", True):
                admin_port = admin_config.get("port", 8090)
                console.print(f"[green]✓ Admin interface configured on port {admin_port}[/green]")
            
            progress.update(task, description="✅ Gateway test completed")
        
        console.print("[green]🎉 API Gateway configuration test passed![/green]")
        
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
        from aico.backend.api_gateway.core.auth import AuthenticationManager
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
