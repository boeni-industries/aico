"""
AICO CLI Container Exec Command

Execute commands inside AICO Docker containers.
"""

import typer
from rich.console import Console
from pathlib import Path
import sys

# Add shared module to path
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from cli.utils.docker_client import DockerClient
from cli.utils.formatting import get_status_chars

console = Console()
app = typer.Typer(help="Execute commands in AICO containers")
chars = get_status_chars()


@app.command()
def exec(
    service: str = typer.Argument(..., help="Service name (gateway, core, modelservice, etc.)"),
    command: str = typer.Argument(..., help="Command to execute"),
    interactive: bool = typer.Option(False, "--interactive", "-it", help="Interactive mode with TTY"),
):
    """Execute a command in an AICO container"""
    
    # Check Docker availability
    if not DockerClient.is_docker_available():
        console.print(f"[red]{chars['cross']} Docker is not installed or not in PATH[/red]")
        raise typer.Exit(1)
    
    if not DockerClient.is_docker_running():
        console.print(f"[red]{chars['cross']} Docker daemon is not running[/red]")
        raise typer.Exit(1)
    
    # Get container name
    container_name = DockerClient.AICO_SERVICES.get(service)
    if not container_name:
        console.print(f"[red]{chars['cross']} Unknown service: {service}[/red]")
        console.print(f"[dim]Available services: {', '.join(DockerClient.AICO_SERVICES.keys())}[/dim]")
        raise typer.Exit(1)
    
    # Check if container is running
    if not DockerClient.is_service_running(service):
        console.print(f"[red]{chars['cross']} Service '{service}' is not running[/red]")
        console.print("[dim]Start it with: aico deploy up[/dim]")
        raise typer.Exit(1)
    
    # Parse command (handle shell commands)
    cmd_parts = command.split()
    
    # Execute command
    exit_code = DockerClient.exec_in_container(container_name, cmd_parts, interactive=interactive)
    
    if exit_code is None:
        console.print(f"[red]{chars['cross']} Failed to execute command[/red]")
        raise typer.Exit(1)
    
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    app()
