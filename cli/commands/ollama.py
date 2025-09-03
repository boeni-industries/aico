"""
CLI commands for Ollama management and model operations.

This module provides direct Ollama management commands following AICO's CLI visual style guide.
Commands interact with the modelservice API and OllamaManager for consistency.
"""

import typer
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.api_client import get_modelservice_client
from ..utils.formatting import format_error, format_success
from ..utils.help_formatter import format_subcommand_help
from aico.security.exceptions import EncryptionError

console = Console()


def _format_model_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def _format_connection_error(error_str: str, command_context: str = "general") -> str:
    """Format connection errors to be more helpful and platform-independent."""
    error_lower = error_str.lower()
    
    # Connection refused errors
    if "connection" in error_lower and ("refused" in error_lower or "10061" in error_str):
        if command_context == "lifecycle":
            return (
                "Modelservice is not running - required for Ollama management.\n"
                "Start modelservice first: aico modelservice start"
            )
        else:
            return (
                "Cannot connect to modelservice (Ollama) - is it running?\n"
                "Try: aico modelservice start"
            )
    
    # Timeout errors
    if "timeout" in error_lower or "timed out" in error_lower:
        return (
            "Connection to modelservice timed out - service may be starting up or overloaded.\n"
            "Wait a moment and try again, or check: aico modelservice status"
        )
    
    # Network unreachable
    if "network" in error_lower and "unreachable" in error_lower:
        return (
            "Network unreachable - check your network connection and modelservice configuration.\n"
            "Verify modelservice host/port in config: aico config show"
        )
    
    # Generic connection error
    if "connection" in error_lower:
        if command_context == "lifecycle":
            return (
                "Cannot reach modelservice - required for Ollama management.\n"
                "Ensure modelservice is running: aico modelservice start"
            )
        else:
            return (
                "Failed to connect to modelservice (Ollama).\n"
                "Ensure modelservice is running: aico modelservice start"
            )
    
    # Return original error if no specific pattern matches
    return f"Ollama operation failed: {error_str}"


def ollama_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        format_subcommand_help(
            console=console,
            command_name="ollama",
            description="Ollama model management and operations",
            subcommands=[
                ("status", "Show Ollama status and running models"),
                ("install", "Install Ollama binary if not present"),
                ("start", "Start Ollama server"),
                ("stop", "Stop Ollama server"),
                ("restart", "Restart Ollama server"),
                ("logs", "View Ollama server logs"),
                ("models", "Model management commands (list, pull, remove)")
            ],
            examples=[
                "aico ollama status",
                "aico ollama install",
                "aico ollama start",
                "aico ollama stop",
                "aico ollama restart",
                "aico ollama models list",
                "aico ollama models pull llama3.2:3b"
            ]
        )
        raise typer.Exit()


app = typer.Typer(
    help="🤖 Ollama model management and operations",
    callback=ollama_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


@app.command("status")
def status():
    """Show Ollama status and running models."""
    asyncio.run(_status_async())

async def _status_async():
    """Async implementation of status command."""
    console.print("\n✨ [bold cyan]Ollama Status[/bold cyan]")
    
    try:
        # Get Ollama status from modelservice
        async with get_modelservice_client() as client:
            status_data = await client.request("GET", "/ollama/status")
        
        # Create status table
        table = Table(
            title="✨ [bold cyan]Ollama System Status[/bold cyan]",
            title_style="bold cyan",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        table.add_column("Component", style="bold white", justify="left")
        table.add_column("Status", style="green", justify="left")
        table.add_column("Details", style="dim", justify="left")
        
        # Add status rows
        installed_status = "[green]Installed[/green]" if status_data.get("installed") else "[red]Not Installed[/red]"
        table.add_row("Binary", installed_status, status_data.get("binary_path", "N/A"))
        
        running_status = "[green]Running[/green]" if status_data.get("running") else "[red]Stopped[/red]"
        process_info = f"PID: {status_data.get('process_id', 'N/A')}" if status_data.get("running") else ""
        table.add_row("Service", running_status, process_info)
        
        healthy_status = "[green]Healthy[/green]" if status_data.get("healthy") else "[red]Unhealthy[/red]"
        version_info = f"v{status_data.get('version', 'unknown')}"
        table.add_row("API", healthy_status, version_info)
        
        models_dir = status_data.get("models_dir", "N/A")
        table.add_row("Models Directory", "[bold white]Active[/bold white]", models_dir)
        
        console.print(table)
        
        # Show running models if available
        if status_data.get("healthy"):
            await _show_running_models_async()
        
        console.print()
        
    except EncryptionError as e:
        error_msg = f"Authentication failed: {str(e)}"
        console.print(format_error(error_msg))
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))


async def _show_running_models_async():
    """Show currently running models."""
    try:
        async with get_modelservice_client() as client:
            models_data = await client.request("GET", "/ollama/models")
        
        if models_data.get("models"):
            console.print("\n✨ [bold cyan]Running Models[/bold cyan]")
            
            models_table = Table(
                border_style="bright_blue",
                header_style="bold yellow",
                show_lines=False,
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            
            models_table.add_column("Model", style="bold white", justify="left")
            models_table.add_column("Size", style="green", justify="left")
            models_table.add_column("Modified", style="dim", justify="left")
            
            for model in models_data["models"]:
                name = model.get("name", "unknown")
                # Convert size to string - handle both integer bytes and string formats
                size_raw = model.get("size", 0)
                if isinstance(size_raw, int):
                    size = _format_model_size(size_raw)
                else:
                    size = str(size_raw) if size_raw else "N/A"
                modified = str(model.get("modified_at", "N/A"))
                models_table.add_row(name, size, modified)
            
            console.print(models_table)
    
    except Exception:
        # Don't show error for running models - it's supplementary info
        pass


@app.command("install")
def install(force: bool = typer.Option(False, "--force", help="Force reinstall even if already installed")):
    """Force reinstall/update Ollama binary."""
    console.print("\n✨ [bold cyan]Ollama Installation[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Installing Ollama...", total=None)
        
        try:
            with get_modelservice_client() as client:
                params = {"force": force} if force else {}
                response = client.post("/api/v1/ollama/install", params=params)
                response.raise_for_status()
                result = response.json()
            
            progress.update(task, description="Installation complete")
            
            if result.get("success"):
                console.print(format_success("Ollama installed successfully"))
                if result.get("version"):
                    console.print(f"[dim]Version: {result['version']}[/dim]")
            else:
                console.print(format_error(f"Installation failed: {result.get('error', 'Unknown error')}"))
        
        except Exception as e:
            progress.update(task, description="Installation failed")
            error_msg = _format_connection_error(str(e))
            console.print(format_error(error_msg))
    
    console.print()


@app.command("serve")
def serve():
    """Start Ollama directly (debug mode)."""
    console.print("\n✨ [bold cyan]Ollama Direct Mode[/bold cyan]")
    console.print("[dim]Starting Ollama server directly for debugging...[/dim]\n")
    
    try:
        with get_modelservice_client() as client:
            response = client.post("/api/v1/ollama/serve")
            response.raise_for_status()
            result = response.json()
        
        if result.get("success"):
            console.print(format_success("Ollama server started in debug mode"))
            console.print("[dim]Use 'aico ollama status' to check server health[/dim]")
        else:
            console.print(format_error(f"Failed to start Ollama: {result.get('error', 'Unknown error')}"))
    
    except Exception as e:
        console.print(format_error(f"Failed to start Ollama server: {e}"))
    
    console.print()


@app.command("logs")
def logs(lines: int = typer.Option(50, "--lines", "-n", help="Number of log lines to show")):
    """View Ollama-specific logs."""
    console.print(f"\n✨ [bold cyan]Ollama Logs (last {lines} lines)[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            response = client.get(f"/api/v1/ollama/logs?lines={lines}")
            response.raise_for_status()
            logs_data = response.json()
        
        if logs_data.get("logs"):
            for log_entry in logs_data["logs"]:
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "INFO")
                message = log_entry.get("message", "")
                
                # Color code by level
                level_color = {
                    "ERROR": "red",
                    "WARNING": "yellow", 
                    "INFO": "white",
                    "DEBUG": "dim"
                }.get(level, "white")
                
                console.print(f"[dim]{timestamp}[/dim] [{level_color}]{level}[/{level_color}] {message}")
        else:
            console.print("[dim]No logs available[/dim]")
    
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
    
    console.print()


# Model management subcommands with callback
def models_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        format_subcommand_help(
            console=console,
            command_name="ollama models",
            description="Model management operations",
            subcommands=[
                ("list", "List available and installed models"),
                ("pull", "Download specific models"),
                ("remove", "Remove models to free space")
            ],
            examples=[
                "aico ollama models list",
                "aico ollama models pull hermes3:8b",
                "aico ollama models pull llama3.2-vision:11b",
                "aico ollama models remove old-model:latest"
            ]
        )
        raise typer.Exit()


models_app = typer.Typer(
    help="📦 Model management operations",
    callback=models_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
app.add_typer(models_app, name="models")


@models_app.command("list")
def models_list():
    """List available and installed models."""
    console.print("\n✨ [bold cyan]Available Models[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            models_data = client.get("/ollama/models")
        
        if models_data.get("models"):
            table = Table(
                border_style="bright_blue",
                header_style="bold yellow", 
                show_lines=False,
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            
            table.add_column("Model", style="bold white", justify="left")
            table.add_column("Size", style="green", justify="left")
            table.add_column("Modified", style="dim", justify="left")
            table.add_column("Status", style="bold white", justify="left")
            
            for model in models_data["models"]:
                name = model.get("name", "unknown")
                # Convert size to string - handle both integer bytes and string formats
                size_raw = model.get("size", 0)
                if isinstance(size_raw, int):
                    size = _format_model_size(size_raw)
                else:
                    size = str(size_raw) if size_raw else "N/A"
                modified = str(model.get("modified_at", "N/A"))
                
                # Determine status
                status = "[green]Ready[/green]"
                
                table.add_row(name, size, modified, status)
            
            console.print(table)
        else:
            console.print("[dim]No models installed[/dim]")
            console.print("[dim]Use 'aico ollama models pull <model>' to download models[/dim]")
    
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
    
    console.print()


@models_app.command("pull")
def models_pull(model_name: str = typer.Argument(..., help="Name of the model to download")):
    """Download specific models."""
    console.print(f"\n✨ [bold cyan]Downloading Model: {model_name}[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(f"Pulling {model_name}...", total=None)
        
        try:
            with get_modelservice_client() as client:
                response = client.post(f"/api/v1/ollama/models/pull", json={"name": model_name})
                response.raise_for_status()
                result = response.json()
            
            progress.update(task, description="Download complete")
            
            if result.get("success"):
                console.print(format_success(f"Model '{model_name}' downloaded successfully"))
            else:
                console.print(format_error(f"Download failed: {result.get('error', 'Unknown error')}"))
        
        except Exception as e:
            progress.update(task, description="Download failed")
            error_msg = _format_connection_error(str(e))
            console.print(format_error(error_msg))
    
    console.print()


@models_app.command("remove")
def models_remove(
    model_name: str = typer.Argument(..., help="Name of the model to remove"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """Remove models to free space."""
    if not confirm:
        confirmed = typer.confirm(f"Are you sure you want to remove model '{model_name}'?")
        if not confirmed:
            console.print("[dim]Operation cancelled[/dim]")
            return
    
    console.print(f"\n✨ [bold cyan]Removing Model: {model_name}[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            response = client.delete(f"/api/v1/ollama/models/{model_name}")
            response.raise_for_status()
            result = response.json()
        
        if result.get("success"):
            console.print(format_success(f"Model '{model_name}' removed successfully"))
        else:
            console.print(format_error(f"Removal failed: {result.get('error', 'Unknown error')}"))
    
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
    
    console.print()


@app.command("start")
def start():
    """Start Ollama server."""
    console.print("\n✨ [bold cyan]Starting Ollama Server[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            response = client.post("/api/v1/ollama/start")
            response.raise_for_status()
            result = response.json()
        
        if result.get("success"):
            console.print(format_success("Ollama server started successfully"))
        else:
            console.print(format_error(f"Failed to start Ollama: {result.get('error', 'Unknown error')}"))
    
    except Exception as e:
        error_msg = _format_connection_error(str(e), "lifecycle")
        console.print(format_error(error_msg))
    
    console.print()


@app.command("stop")
def stop():
    """Stop Ollama server."""
    console.print("\n✨ [bold cyan]Stopping Ollama Server[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            response = client.post("/api/v1/ollama/stop")
            response.raise_for_status()
            result = response.json()
        
        if result.get("success"):
            console.print(format_success("Ollama server stopped successfully"))
        else:
            console.print(format_error(f"Failed to stop Ollama: {result.get('error', 'Unknown error')}"))
    
    except Exception as e:
        error_msg = _format_connection_error(str(e), "lifecycle")
        console.print(format_error(error_msg))
    
    console.print()


@app.command("restart")
def restart():
    """Restart Ollama server."""
    console.print("\n✨ [bold cyan]Restarting Ollama Server[/bold cyan]")
    
    try:
        with get_modelservice_client() as client:
            # Stop first
            response = client.post("/api/v1/ollama/stop")
            response.raise_for_status()
            
            # Start again
            response = client.post("/api/v1/ollama/start")
            response.raise_for_status()
            result = response.json()
        
        if result.get("success"):
            console.print(format_success("Ollama server restarted successfully"))
        else:
            console.print(format_error(f"Failed to restart Ollama: {result.get('error', 'Unknown error')}"))
    
    except Exception as e:
        error_msg = _format_connection_error(str(e), "lifecycle")
        console.print(format_error(error_msg))
    
    console.print()


if __name__ == "__main__":
    app()
