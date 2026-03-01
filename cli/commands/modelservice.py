"""
AICO CLI Modelservice Commands

Provides model service management and control.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box

# Add shared module to path for CLI usage FIRST
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from cli.utils.formatting import get_status_chars
from cli.utils.nats_client import get_modelservice_health
from cli.utils.docker_client import DockerClient

console = Console()

# Get platform-appropriate characters
chars = get_status_chars()


def _is_modelservice_running() -> bool:
    """Check if Modelservice is currently running"""
    try:
        # Primary check: message bus health request
        health_response = get_modelservice_health()
        if health_response.get("success"):
            return True

        # Docker-first fallback: check container status
        if DockerClient.is_docker_available() and DockerClient.is_docker_running():
            return DockerClient.is_service_running("modelservice")
        
        return False
        
    except Exception:
        return False


def _get_modelservice_config() -> dict:
    """Get Modelservice configuration from core config"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("modelservice", {})
    except Exception:
        return {}


async def _enhance_health_data(health_data: dict):
    """Enhance health data with actual service checks."""
    import httpx
    import time
    
    if "checks" not in health_data:
        health_data["checks"] = {}
    
    # Run both health checks concurrently with reduced timeout
    async def check_api_gateway():
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get("http://127.0.0.1:8771/api/v1/health")
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "reachable": True,
                        "response_time_ms": round(response_time)
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "reachable": True,
                        "error": f"HTTP {response.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "reachable": False,
                "error": "connection_refused"
            }
        except Exception as e:
            return {
                "status": "unknown",
                "reachable": False,
                "error": str(e)
            }
    
    # Only check API Gateway (vLLM is deployed separately)
    gateway_result = await check_api_gateway()
    
    # Handle result
    if isinstance(gateway_result, Exception):
        health_data["checks"]["api_gateway"] = {
            "status": "unknown",
            "reachable": False,
            "error": str(gateway_result)
        }
    else:
        health_data["checks"]["api_gateway"] = gateway_result


async def _show_service_details(health_data: dict):
    """Show additional service details for healthy services."""
    try:
        # vLLM models are managed separately via 'aico vllm' commands
        
        # Show configuration summary
        config = _get_modelservice_config()
        if config:
            console.print()
            table = Table(title="Service Configuration", show_header=True, header_style="bold blue")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="dim")
            
            # Show key configuration values
            rest_config = config.get("rest", {})
            
            table.add_row("REST API", f"{rest_config.get('host', '127.0.0.1')}:{rest_config.get('port', 8773)}")
            
            console.print(table)
            
    except Exception:
        pass  # Silently skip if details can't be shown


def _format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def modelservice_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("status", "Show service status and health"),
            ("embeddings", "Test embedding generation")
        ]
        
        examples = [
            "aico modelservice status",
            "aico modelservice embeddings 'test text'",
            "aico deploy up  # Start services"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="modelservice",
            description="Model service management and control",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()


app = typer.Typer(
    help="Model service management and control.",
    callback=modelservice_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


@app.command(help="Show Modelservice status and health")
def status():
    """Show Modelservice status and health."""
    try:
        # Check if running
        is_running = _is_modelservice_running()
        health_data = {}
        
        # Get health data if running via message bus
        if is_running:
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    # Step 1: Get basic health via message bus
                    task = progress.add_task("Checking modelservice health...", total=None)
                    health_response = get_modelservice_health()
                    
                    if health_response.get("success"):
                        health_data = health_response.get("data", {})
                        
                        # Step 2: Enhanced health checks
                        progress.update(task, description="Checking API Gateway...")
                        asyncio.run(_enhance_health_data(health_data))
                        
                        progress.update(task, description="Health checks complete!")
                        progress.stop()
                    else:
                        # Service is running but health endpoint failed - still show basic info
                        health_data = {
                            "status": "connection_failed", 
                            "version": "0.0.2", 
                            "checks": {
                                "api_gateway": {"status": "unknown", "reachable": False, "error": "connection_failed"}
                            }, 
                            "issues": ["Health endpoint unreachable via message bus"]
                        }
            except Exception as e:
                # Fallback health data for display
                health_data = {
                    "status": "connection_failed", 
                    "version": "0.0.2", 
                    "checks": {
                        "api_gateway": {"status": "unknown", "reachable": False, "error": "bus_connection_failed"}
                    }, 
                    "issues": [f"Message bus health check failed: {str(e)}"]
                }
        
        # Primary status header (matching gateway format)
        if is_running:
            health_status = health_data.get("status", "unknown")
            if health_status == "healthy":
                console.print(f"{chars['globe']} [bold green]Modelservice Status: HEALTHY[/bold green]")
            else:
                console.print(f"{chars['globe']} [bold yellow]Modelservice Status: RUNNING (Unhealthy)[/bold yellow]")
            
            version = health_data.get("version", "Unknown")
            console.print(f"   [dim]Version {version} • Message Bus[/dim]")
        else:
            console.print(f"{chars['globe']} [bold red]Modelservice Status: OFFLINE[/bold red]")
            console.print(f"   [dim]Not responding via message bus[/dim]")
        
        console.print()
        
        # Health details if running (show for both healthy and unhealthy)
        if is_running and health_data:
            checks = health_data.get("checks", {})
            errors = health_data.get("issues", [])
            
            if checks:
                table = Table(title="Health Checks", show_header=True, header_style="bold blue")
                table.add_column("Component", style="cyan", no_wrap=True)
                table.add_column("Status", justify="left")
                table.add_column("Details", style="dim")
                
                for component, check_data in checks.items():
                    if isinstance(check_data, dict):
                        # Handle different status field names for backward compatibility
                        status = check_data.get("status", "unknown")
                        is_healthy = (status == "healthy" or 
                                    check_data.get("healthy", False) or
                                    check_data.get("reachable", False))
                        
                        if status == "healthy" or (check_data.get("healthy", False) and check_data.get("reachable", False)):
                            status_display = f"[green]{chars['check']} Healthy[/green]"
                            response_time = check_data.get('response_time_ms')
                            if response_time:
                                details = f"{response_time}ms"
                            else:
                                details = "Running"
                        elif status == "running" or check_data.get("status") == "running":
                            status_display = f"[green]{chars['check']} Running[/green]"
                            response_time = check_data.get('response_time_ms')
                            if response_time:
                                details = f"{response_time}ms"
                            else:
                                details = "Service active"
                        elif status == "offline" or check_data.get("error") == "connection_refused":
                            status_display = f"[red]{chars['cross']} Offline[/red]"
                            details = "Service not running"
                        elif status == "timeout" or check_data.get("error") == "timeout":
                            status_display = f"[yellow]{chars['warning']} Timeout[/yellow]"
                            details = "Connection timeout"
                        else:
                            status_display = f"[red]{chars['cross']} Unhealthy[/red]"
                            error = check_data.get("error", "Unknown error")
                            # Clean up common error messages
                            if error == "connection_refused":
                                details = "Service not running"
                            elif error == "connection_failed":
                                details = "Connection failed"
                            elif len(error) > 60:
                                # Wrap long error messages
                                import textwrap
                                wrapped_lines = textwrap.wrap(error, width=60)
                                details = "\n".join(wrapped_lines)
                            else:
                                details = error
                    else:
                        status_display = f"[yellow]{chars['warning']} Unknown[/yellow]"
                        details = str(check_data)
                    
                    table.add_row(component.replace("_", " ").title(), status_display, details)
                
                console.print(table)
                console.print()
            
            if errors:
                console.print(f"[red]{chars['cross']} Issues Found:[/red]")
                for error in errors:
                    console.print(f"  • {error}")
                console.print()
        
        # Additional service information if healthy
        if is_running and health_data.get("status") == "healthy":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Loading service details...", total=None)
                asyncio.run(_show_service_details(health_data))
                progress.stop()
        
        # Topics table
        if is_running:
            table = Table(title="Available Topics", show_header=True, header_style="bold blue")
            table.add_column("Topic", style="cyan", no_wrap=True)
            table.add_column("Purpose", style="dim")
            
            topics = [
                ("modelservice/health/request", "Service health and status"),
                ("modelservice/completions/request", "Text generation"),
                ("modelservice/models/request", "List available models"),
                ("modelservice/status/request", "Service status information")
            ]
            
            for topic, purpose in topics:
                table.add_row(topic, purpose)
            
            console.print(table)
        
    except Exception as e:
        console.print(f"{chars['cross']} [red]Error checking Modelservice status: {e}[/red]")
        raise typer.Exit(1)


# Ollama-specific commands removed - use 'aico vllm' for LLM model management


@app.command("embeddings")
def embeddings(
    text: str = typer.Argument(..., help="Text to generate embeddings for"),
    model: str = typer.Option("paraphrase-multilingual", "--model", "-m", help="Embedding model to use")
):
    """Test embedding generation."""
    try:
        if not _is_modelservice_running():
            console.print(f"[red]{chars['cross']} Modelservice is not running[/red]")
            console.print("[dim]Start it with: aico modelservice start[/dim]")
            raise typer.Exit(1)
        
        console.print(f"[yellow]🧠 Generating embeddings for: '{text[:50]}{'...' if len(text) > 50 else ''}'[/yellow]")
        console.print(f"[dim]Using model: {model}[/dim]")
        
        from cli.utils.nats_client import get_embeddings
        response = get_embeddings(model, text)
        
        if response.get("success"):
            embeddings = response.get("data", {}).get("embedding", [])
            console.print(f"[green]{chars['check']} Generated embeddings successfully[/green]")
            console.print(f"[dim]Dimensions: {len(embeddings)}[/dim]")
            console.print(f"[dim]Sample values: {embeddings[:5]}...[/dim]")
        else:
            console.print(f"[red]{chars['cross']} Failed to generate embeddings: {response.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]{chars['cross']} Error generating embeddings: {e}[/red]")
        raise typer.Exit(1)
