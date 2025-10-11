"""
CLI commands for Ollama management and model operations.

This module provides direct Ollama management commands following AICO's CLI visual style guide.
Commands interact directly with Ollama API endpoints for maximum resilience.
"""

import typer
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import sys

import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from cli.decorators.sensitive import sensitive

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from ..utils.formatting import format_error, format_success
from ..utils.help_formatter import format_subcommand_help

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


def _get_ollama_config() -> Dict[str, Any]:
    """Get Ollama configuration from core config."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("modelservice.ollama", {})
    except Exception:
        return {}


def _get_ollama_base_url() -> str:
    """Get Ollama base URL from configuration."""
    config = _get_ollama_config()
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 11434)
    return f"http://{host}:{port}"


def _format_connection_error(error_str: str, command_context: str = "general") -> str:
    """Format connection errors to be more helpful and platform-independent."""
    error_lower = error_str.lower()
    
    # Connection refused errors
    if "connection" in error_lower and ("refused" in error_lower or "10061" in error_str):
        return (
            "Cannot connect to Ollama - is it running?\n"
            "Try: ollama serve (or check if Ollama is installed)"
        )
    
    # Timeout errors
    if "timeout" in error_lower or "timed out" in error_lower:
        return (
            "Connection to Ollama timed out - service may be starting up or overloaded.\n"
            "Wait a moment and try again"
        )
    
    # Network unreachable
    if "network" in error_lower and "unreachable" in error_lower:
        return (
            "Network unreachable - check your network connection and Ollama configuration.\n"
            "Verify Ollama host/port in config"
        )
    
    # Generic connection error
    if "connection" in error_lower:
        return (
            "Failed to connect to Ollama.\n"
            "Ensure Ollama is running: ollama serve"
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
                ("status", "Show Ollama status and available models"),
                ("generate", "Generate AI character model from Modelfile"),
                ("install", "Install Ollama binary (manual process)"),
                ("serve", "Start Ollama server daemon"),
                ("shutdown", "Stop Ollama server daemon"),
                ("run", "Run a model interactively"),
                ("show", "Show detailed model information"),
                ("logs", "View Ollama server logs"),
                ("models", "Model management commands (list, pull, remove)")
            ],
            examples=[
                "aico ollama status",
                "aico ollama generate eve",
                "aico ollama serve",
                "aico ollama run llama3.2:3b",
                "aico ollama show hermes3:8b",
                "aico ollama models pull hermes3:8b",
                "aico ollama models list"
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
    
    base_url = _get_ollama_base_url()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test basic connectivity
            try:
                response = await client.get(f"{base_url}/api/version")
                version_data = response.json() if response.status_code == 200 else {}
                is_running = True
            except Exception:
                is_running = False
                version_data = {}
        
        # Create status table
        table = Table(
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
        running_status = "[green]Running[/green]" if is_running else "[red]Stopped[/red]"
        table.add_row("Service", running_status, base_url)
        
        if is_running:
            version_info = version_data.get("version", "unknown")
            table.add_row("Version", "[green]Available[/green]", f"v{version_info}")
        else:
            table.add_row("Version", "[red]Unavailable[/red]", "Service not running")
        
        console.print(table)
        
        # Show running models if available
        if is_running:
            console.print("\n✨ [bold cyan]Available Models[/bold cyan]")
            await _show_running_models_async(show_title=False)
        
        console.print()
        
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))


async def _show_running_models_async(show_title: bool = True):
    """Show available models with running status.
    
    Args:
        show_title: Whether to show the "Available Models" title
    """
    base_url = _get_ollama_base_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all models
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
            else:
                return
            
            # Get running models
            running_models = set()
            try:
                ps_response = await client.get(f"{base_url}/api/ps")
                if ps_response.status_code == 200:
                    ps_data = ps_response.json()
                    running_models = {model.get("name", "") for model in ps_data.get("models", [])}
            except Exception:
                pass  # Continue without running status if ps fails
        
        if models_data.get("models"):
            if show_title:
                console.print("\n✨ [bold cyan]Available Models[/bold cyan]")
            
            models_table = Table(
                border_style="bright_blue",
                header_style="bold yellow",
                show_lines=False,
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            
            models_table.add_column("Model", style="bold white", justify="left")
            models_table.add_column("Size", style="green", justify="left")
            models_table.add_column("Parameters", style="cyan", justify="left")
            models_table.add_column("Family", style="yellow", justify="left")
            models_table.add_column("Status", style="white", justify="left")
            models_table.add_column("Modified", style="dim", justify="left")
            
            for model in models_data["models"]:
                name = model.get("name", "unknown")
                
                # Size
                size_raw = model.get("size", 0)
                if isinstance(size_raw, int):
                    size = _format_model_size(size_raw)
                else:
                    size = str(size_raw) if size_raw else "N/A"
                
                # Get detailed model information from tags response
                details = model.get("details", {})
                param_size = details.get("parameter_size", "N/A")
                family = details.get("family", "N/A")
                
                # Running status
                if name in running_models:
                    status = "[green]Running[/green]"
                else:
                    status = "[dim]Stopped[/dim]"
                
                # Modified date
                modified = str(model.get("modified_at", "N/A"))
                if modified != "N/A" and len(modified) > 19:
                    modified = modified[:19]  # Truncate timestamp
                
                models_table.add_row(name, size, param_size, family, status, modified)
            
            console.print(models_table)
    
    except Exception:
        pass  # Silently fail if models can't be retrieved


@app.command("generate")
def generate(
    character_name: Optional[str] = typer.Argument(None, help="Name of the character to generate (e.g., 'eve')"),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate character if it already exists")
):
    """Generate AI character model from Modelfile.
    
    This command reads a character definition from config/modelfiles/Modelfile.{character}
    and generates a custom Ollama model variant with the character's personality and parameters.
    
    Examples:
        aico ollama generate eve
        aico ollama generate eve --force
    """
    # Get Modelfile directory from user config
    try:
        config_dir = AICOPaths.get_config_directory()
        modelfiles_dir = config_dir / "modelfiles"
        
        # If no character name provided, list available characters
        if character_name is None:
            console.print("\n✨ [bold cyan]Available Characters[/bold cyan]")
            
            # Get all Modelfiles
            modelfiles = sorted(modelfiles_dir.glob("Modelfile.*"))
            
            if not modelfiles:
                console.print("[dim]No character Modelfiles found in user config directory[/dim]")
                console.print(f"[dim]Location: {modelfiles_dir}[/dim]\n")
                console.print("[yellow]Run the following command to copy default Modelfiles:[/yellow]")
                console.print("[bold]  aico config init[/bold]\n")
                console.print("[dim]Or create custom Modelfiles in the config directory[/dim]")
                console.print()
                return
            
            # Create table for characters
            table = Table(
                border_style="bright_blue",
                header_style="bold yellow",
                show_lines=False,
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            
            table.add_column("Character", style="bold white", justify="left")
            table.add_column("Modelfile", style="dim", justify="left")
            
            for modelfile in modelfiles:
                # Extract character name by removing "Modelfile." prefix from filename
                char_name = modelfile.name.replace("Modelfile.", "")
                table.add_row(char_name, str(modelfile.name))
            
            console.print(table)
            console.print("\n[dim]Usage: aico ollama generate <character>[/dim]")
            console.print("[dim]Example: aico ollama generate eve[/dim]")
            console.print()
            return
        
        modelfile_path = modelfiles_dir / f"Modelfile.{character_name}"
    except Exception as e:
        console.print(format_error(f"Failed to access Modelfile directory: {str(e)}"))
        return
    
    console.print(f"\n✨ [bold cyan]Generating Character Model: {character_name}[/bold cyan]")
    
    # Check if Modelfile exists
    if not modelfile_path.exists():
        console.print(format_error(
            f"Modelfile not found: {modelfile_path}\n"
            f"Expected location: config/modelfiles/Modelfile.{character_name}\n"
            f"Available characters: {', '.join([f.stem.replace('Modelfile.', '') for f in modelfiles_dir.glob('Modelfile.*')])}"
        ))
        return
    
    console.print(f"[dim]Reading Modelfile from: {modelfile_path}[/dim]")
    
    # Check if Ollama is running
    base_url = _get_ollama_base_url()
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/api/version")
            if response.status_code != 200:
                console.print(format_error(
                    "Ollama is not running.\n"
                    "Start Ollama first: ollama serve"
                ))
                return
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
        return
    
    # Check if character model already exists
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                existing_models = {model.get("name", "") for model in models_data.get("models", [])}
                
                if character_name in existing_models:
                    if not force:
                        console.print(f"[yellow]Character model '{character_name}' already exists.[/yellow]")
                        console.print("[dim]Use --force to recreate it.[/dim]")
                        return
                    else:
                        console.print(f"[yellow]Recreating existing character model '{character_name}'...[/yellow]")
    except Exception:
        pass  # Continue if we can't check existing models
    
    # Read and validate Modelfile
    try:
        modelfile_content = modelfile_path.read_text(encoding='utf-8')
        
        # Basic validation
        if not modelfile_content.strip():
            console.print(format_error("Modelfile is empty"))
            return
        
        if "FROM" not in modelfile_content:
            console.print(format_error("Modelfile missing required FROM instruction"))
            return
        
        console.print("[dim]Modelfile validated successfully[/dim]")
        
    except Exception as e:
        console.print(format_error(f"Failed to read Modelfile: {str(e)}"))
        return
    
    # Generate character model using Ollama API
    console.print(f"[dim]Generating character model '{character_name}' in Ollama...[/dim]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(f"Generating {character_name}...", total=None)
        
        try:
            with httpx.Client(timeout=120.0) as client:  # Longer timeout for model creation
                # Use Ollama's create API endpoint
                response = client.post(
                    f"{base_url}/api/create",
                    json={
                        "name": character_name,
                        "modelfile": modelfile_content
                    },
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    progress.update(task, description="Character model generated successfully")
                    console.print(format_success(
                        f"Character model '{character_name}' generated successfully!\n"
                        f"Test it with: ollama run {character_name}"
                    ))
                    
                    # Show model info
                    console.print(f"\n[bold cyan]Model Details:[/bold cyan]")
                    console.print(f"[dim]Name: {character_name}[/dim]")
                    console.print(f"[dim]Modelfile: {modelfile_path}[/dim]")
                    
                    # Extract base model from Modelfile
                    base_model = None
                    for line in modelfile_content.split('\n'):
                        if line.strip().startswith('FROM '):
                            base_model = line.strip().replace('FROM ', '')
                            console.print(f"[dim]Base Model: {base_model}[/dim]")
                            break
                    
                    # Update configuration to use the new character model
                    console.print(f"\n[bold cyan]Updating Configuration:[/bold cyan]")
                    try:
                        config_manager = ConfigurationManager()
                        config_manager.initialize()
                        
                        # Update the conversation model name
                        config_manager.set("modelservice.ollama.default_models.conversation.name", character_name, persist=True)
                        console.print(f"[green]✓[/green] Updated config: modelservice.ollama.default_models.conversation.name = {character_name}")
                        
                        # Update description if we have base model info
                        if base_model:
                            description = f"{character_name.title()} character based on {base_model}"
                            config_manager.set("modelservice.ollama.default_models.conversation.description", description, persist=True)
                            console.print(f"[green]✓[/green] Updated config: modelservice.ollama.default_models.conversation.description")
                        
                    except Exception as e:
                        console.print(f"[yellow]⚠[/yellow] Could not update config automatically: {e}")
                        console.print(f"[dim]You can manually update core.yaml to use model '{character_name}'[/dim]")
                    
                    # Prompt to restart modelservice
                    console.print(f"\n[bold yellow]⚠ Important:[/bold yellow]")
                    console.print(f"[yellow]Modelservice needs to be restarted to use the new character model.[/yellow]")
                    console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
                    console.print(f"  1. Restart modelservice: [bold]aico modelservice restart[/bold]")
                    console.print(f"  2. Or if not running: [bold]aico modelservice start[/bold]")
                    console.print(f"\n[dim]The new '{character_name}' model will be used for all conversations.[/dim]")
                    
                else:
                    progress.update(task, description="Generation failed")
                    error_text = response.text if response.text else "Unknown error"
                    console.print(format_error(
                        f"Failed to generate character model.\n"
                        f"Ollama API error: {error_text}"
                    ))
        
        except httpx.TimeoutException:
            progress.update(task, description="Generation timed out")
            console.print(format_error(
                "Character model generation timed out.\n"
                "This may happen if the base model needs to be downloaded.\n"
                "Check Ollama logs for progress."
            ))
        
        except Exception as e:
            progress.update(task, description="Generation failed")
            error_msg = _format_connection_error(str(e))
            console.print(format_error(error_msg))
    
    console.print()


@app.command("install")
def install(force: bool = typer.Option(False, "--force", help="Force reinstall even if already installed")):
    """Install Ollama binary (requires system installation)."""
    console.print("\n✨ [bold cyan]Ollama Installation[/bold cyan]")
    
    console.print("[yellow]Note: This command requires manual Ollama installation.[/yellow]")
    console.print("[dim]Please visit https://ollama.com/download to install Ollama for your platform.[/dim]")
    console.print("[dim]After installation, use 'aico ollama status' to verify.[/dim]")
    console.print()


@app.command("serve")
def serve():
    """Start Ollama server daemon."""
    console.print("\n✨ [bold cyan]Starting Ollama Server[/bold cyan]")
    
    console.print("[yellow]Note: Use the native Ollama command to start the server:[/yellow]")
    console.print("[dim]$ ollama serve[/dim]")
    console.print("[dim]Or run Ollama in the background as a system service.[/dim]")
    console.print("[dim]Use 'aico ollama status' to check if the server is running.[/dim]")
    console.print()


@app.command("logs")
def logs(lines: int = typer.Option(50, "--lines", "-n", help="Number of log lines to show")):
    """View Ollama server logs."""
    console.print(f"\n✨ [bold cyan]Ollama Logs[/bold cyan]")
    
    console.print("[yellow]Note: Ollama logs are typically managed by the system.[/yellow]")
    console.print("[dim]Check system logs or run 'ollama serve' in foreground to see output.[/dim]")
    console.print("[dim]On systemd systems: journalctl -u ollama[/dim]")
    console.print("[dim]On macOS: Check Console.app or system logs[/dim]")
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
    
    base_url = _get_ollama_base_url()
    
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            # Get all models
            response = client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            
            # Get running models
            running_models = set()
            try:
                ps_response = client.get(f"{base_url}/api/ps")
                if ps_response.status_code == 200:
                    ps_data = ps_response.json()
                    running_models = {model.get("name", "") for model in ps_data.get("models", [])}
            except Exception:
                pass  # Continue without running status if ps fails
        
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
            table.add_column("Parameters", style="cyan", justify="left")
            table.add_column("Family", style="yellow", justify="left")
            table.add_column("Status", style="white", justify="left")
            table.add_column("Modified", style="dim", justify="left")
            
            for model in models_data["models"]:
                name = model.get("name", "unknown")
                
                # Size
                size_raw = model.get("size", 0)
                if isinstance(size_raw, int):
                    size = _format_model_size(size_raw)
                else:
                    size = str(size_raw) if size_raw else "N/A"
                
                # Get detailed model information from tags response
                details = model.get("details", {})
                param_size = details.get("parameter_size", "N/A")
                family = details.get("family", "N/A")
                
                # Running status
                if name in running_models:
                    status = "[green]Running[/green]"
                else:
                    status = "[dim]Ready[/dim]"
                
                # Modified date
                modified = str(model.get("modified_at", "N/A"))
                if modified != "N/A" and len(modified) > 19:
                    modified = modified[:19]  # Truncate timestamp
                
                table.add_row(name, size, param_size, family, status, modified)
            
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
    
    base_url = _get_ollama_base_url()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(f"Pulling {model_name}...", total=None)
        
        try:
            import httpx
            with httpx.Client(timeout=300.0) as client:  # Longer timeout for model downloads
                response = client.post(f"{base_url}/api/pull", json={"name": model_name})
                response.raise_for_status()
            
            progress.update(task, description="Download complete")
            console.print(format_success(f"Model '{model_name}' downloaded successfully"))
        
        except Exception as e:
            progress.update(task, description="Download failed")
            error_msg = _format_connection_error(str(e))
            console.print(format_error(error_msg))
    
    console.print()


@models_app.command("remove")
@sensitive
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
    
    base_url = _get_ollama_base_url()
    
    try:
        import httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.request("DELETE", f"{base_url}/api/delete", json={"name": model_name})
            response.raise_for_status()
        
        console.print(format_success(f"Model '{model_name}' removed successfully"))
    
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
    
    console.print()




@app.command("shutdown")
def shutdown():
    """Stop Ollama server daemon."""
    console.print("\n✨ [bold cyan]Stopping Ollama Server[/bold cyan]")
    
    console.print("[yellow]Note: Use system commands to stop Ollama:[/yellow]")
    console.print("[dim]Kill the 'ollama serve' process or use system service controls.[/dim]")
    console.print("[dim]On systemd: sudo systemctl stop ollama[/dim]")
    console.print("[dim]Or find and kill the process: pkill ollama[/dim]")
    console.print()


@app.command("run")
def run(model_name: str = typer.Argument(..., help="Name of the model to run")):
    """Run a model interactively."""
    console.print(f"\n✨ [bold cyan]Running Model: {model_name}[/bold cyan]")
    
    console.print("[yellow]Note: Use the native Ollama command for interactive conversation:[/yellow]")
    console.print(f"[dim]$ ollama run {model_name}[/dim]")
    console.print("[dim]This will start an interactive conversation session with the model.[/dim]")
    console.print()


@app.command("show")
def show(model_name: str = typer.Argument(..., help="Name of the model to show info for")):
    """Show detailed information about a model."""
    console.print(f"\n✨ [bold cyan]Model Information: {model_name}[/bold cyan]")
    
    base_url = _get_ollama_base_url()
    
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{base_url}/api/show", json={"name": model_name})
            response.raise_for_status()
            model_info = response.json()
        
        # Create info table
        table = Table(
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        table.add_column("Property", style="bold white", justify="left")
        table.add_column("Value", style="dim", justify="left")
        
        # Add model details
        if "details" in model_info:
            details = model_info["details"]
            table.add_row("Format", details.get("format", "N/A"))
            table.add_row("Family", details.get("family", "N/A"))
            table.add_row("Parameter Size", details.get("parameter_size", "N/A"))
            table.add_row("Quantization", details.get("quantization_level", "N/A"))
        
        if "license" in model_info:
            table.add_row("License", model_info["license"][:50] + "..." if len(model_info["license"]) > 50 else model_info["license"])
        
        console.print(table)
        
        # Show system prompt if available
        if "system" in model_info and model_info["system"]:
            console.print("\n[bold cyan]System Prompt:[/bold cyan]")
            console.print(f"[dim]{model_info['system'][:200]}{'...' if len(model_info['system']) > 200 else ''}[/dim]")
    
    except Exception as e:
        error_msg = _format_connection_error(str(e))
        console.print(format_error(error_msg))
    
    console.print()




if __name__ == "__main__":
    app()
