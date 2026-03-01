"""
AICO CLI Container Listing Command

Shows running AICO Docker containers with status and health information.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import box
from datetime import datetime
from pathlib import Path
import sys

# Add shared module to path
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from cli.utils.docker_client import DockerClient, ContainerStatus, detect_deployment_mode
from cli.utils.formatting import get_status_chars

console = Console()
app = typer.Typer(help="List AICO Docker containers")
chars = get_status_chars()


@app.command()
def ps(
    all: bool = typer.Option(False, "--all", "-a", help="Show all containers (including stopped)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only show container IDs"),
):
    """List AICO Docker containers"""
    
    # Check Docker availability
    if not DockerClient.is_docker_available():
        console.print(f"[red]{chars['cross']} Docker is not installed or not in PATH[/red]")
        console.print("[dim]Install Docker: https://docs.docker.com/get-docker/[/dim]")
        raise typer.Exit(1)
    
    if not DockerClient.is_docker_running():
        console.print(f"[red]{chars['cross']} Docker daemon is not running[/red]")
        console.print("[dim]Start Docker Desktop or run: sudo systemctl start docker[/dim]")
        raise typer.Exit(1)
    
    # Get containers
    containers = DockerClient.list_aico_containers()
    
    if not containers:
        console.print(f"[yellow]{chars['warning']} No AICO containers found[/yellow]")
        console.print("[dim]Run 'aico deploy up' to start AICO services[/dim]")
        return
    
    # Filter by status if not showing all
    if not all:
        containers = [c for c in containers if c.status == ContainerStatus.RUNNING]
    
    if not containers:
        console.print(f"[yellow]{chars['warning']} No running AICO containers[/yellow]")
        console.print("[dim]Run 'aico deploy up' to start services or use --all to see stopped containers[/dim]")
        return
    
    # Quiet mode - just IDs
    if quiet:
        for container in containers:
            console.print(container.container_id)
        return
    
    # Create table
    table = Table(
        title="AICO Docker Containers",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        title_style="bold blue"
    )
    
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Container ID", style="dim", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Image", style="dim")
    table.add_column("Ports", style="yellow")
    
    # Sort containers by service name
    service_order = ["gateway", "core", "modelservice", "nats", "postgres", "influxdb", "loki", "grafana"]
    
    def get_service_priority(container):
        # Extract service name from container name
        for idx, service in enumerate(service_order):
            if service in container.name.lower():
                return idx
        return 999
    
    containers.sort(key=get_service_priority)
    
    # Add rows
    for container in containers:
        # Determine status display
        if container.status == ContainerStatus.RUNNING:
            status_display = f"[green]{chars['check']} Running[/green]"
        elif container.status == ContainerStatus.STOPPED or container.status == ContainerStatus.EXITED:
            status_display = f"[red]{chars['cross']} Stopped[/red]"
        elif container.status == ContainerStatus.PAUSED:
            status_display = f"[yellow]{chars['warning']} Paused[/yellow]"
        elif container.status == ContainerStatus.RESTARTING:
            status_display = f"[yellow]{chars['hourglass']} Restarting[/yellow]"
        else:
            status_display = f"[dim]{container.state}[/dim]"
        
        # Extract service name from container name
        service_name = container.name.replace("aico-", "")
        
        # Format ports
        ports_display = ", ".join(container.ports) if container.ports else "-"
        
        # Truncate image name for display
        image_parts = container.image.split(":")
        image_display = f"{image_parts[0].split('/')[-1]}:{image_parts[1]}" if len(image_parts) > 1 else container.image
        
        table.add_row(
            service_name,
            container.container_id,
            status_display,
            image_display,
            ports_display
        )
    
    console.print()
    console.print(table)
    console.print()
    
    # Show helpful commands
    console.print("[dim]Commands:[/dim]")
    console.print(f"  [cyan]aico logs <service>[/cyan]  - View service logs")
    console.print(f"  [cyan]aico exec <service> <cmd>[/cyan]  - Execute command in container")
    console.print(f"  [cyan]aico deploy restart <service>[/cyan]  - Restart a service")
    console.print()


if __name__ == "__main__":
    app()
