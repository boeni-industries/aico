"""AICO CLI Upgrade Command

Manages system upgrades for containerized AICO architecture.
Handles container image updates, database migrations, and rollback capability.
"""

import sys
import subprocess
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add shared module to path
if getattr(sys, "frozen", False):
    shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from cli.utils.formatting import format_error, format_success, format_info, format_warning
from cli.decorators.sensitive import sensitive

app = typer.Typer(help="Upgrade AICO system components")
console = Console()


def _get_aico_repo_root() -> Path:
    """Resolve the AICO repo root."""
    # cli/commands/upgrade.py -> cli/commands -> cli -> repo_root
    return Path(__file__).parent.parent.parent.resolve()


def _read_versions_file() -> Dict[str, str]:
    """Read current versions from VERSIONS file."""
    repo_root = _get_aico_repo_root()
    versions_file = repo_root / "VERSIONS"
    
    if not versions_file.exists():
        return {}
    
    versions = {}
    with open(versions_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                key, value = line.split(':', 1)
                versions[key.strip()] = value.strip()
    
    return versions


def _get_container_image_version(container_name: str) -> Optional[str]:
    """Get the current image version of a running container."""
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{.Config.Image}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _get_running_containers() -> List[Dict[str, str]]:
    """Get list of running AICO containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=com.aico.project=aico", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                container = json.loads(line)
                containers.append({
                    'name': container.get('Names', ''),
                    'image': container.get('Image', ''),
                    'status': container.get('Status', ''),
                    'id': container.get('ID', '')
                })
        
        return containers
    except subprocess.CalledProcessError:
        return []


def _check_postgres_health() -> bool:
    """Check if Postgres is healthy and accessible."""
    try:
        result = subprocess.run(
            [
                "docker", "exec", "aico-postgres",
                "sh", "-c",
                "PGPASSWORD=$(cat /run/secrets/pg_password) psql -U postgres -d aico -c 'SELECT 1;'"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _backup_database() -> Optional[Path]:
    """Create a database backup before upgrade."""
    repo_root = _get_aico_repo_root()
    backup_dir = repo_root / "backups" / "pre-upgrade"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"aico_backup_{timestamp}.sql"
    
    try:
        console.print(format_info(f"Creating database backup: {backup_file.name}"))
        
        result = subprocess.run(
            [
                "docker", "exec", "aico-postgres",
                "sh", "-c",
                f"PGPASSWORD=$(cat /run/secrets/pg_password) pg_dump -U postgres -d aico"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=300
        )
        
        with open(backup_file, 'w') as f:
            f.write(result.stdout)
        
        console.print(format_success(f"Database backup created: {backup_file}"))
        return backup_file
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        console.print(format_error(f"Failed to create database backup: {e}"))
        return None


def _get_compose_file() -> Path:
    """Get the docker-compose file path."""
    repo_root = _get_aico_repo_root()
    return repo_root / "docker" / "docker-compose.local.yml"


@app.command("status")
def upgrade_status():
    """Check current system status and available upgrades."""
    console.print(Panel("[bold cyan]AICO System Status[/bold cyan]", expand=False))
    
    # Read versions file
    versions = _read_versions_file()
    
    # Create versions table
    versions_table = Table(title="Component Versions", show_header=True, header_style="bold cyan")
    versions_table.add_column("Component", style="cyan", width=20)
    versions_table.add_column("Version", style="green", width=15)
    
    for component, version in versions.items():
        versions_table.add_row(component, version)
    
    console.print(versions_table)
    console.print()
    
    # Get running containers
    containers = _get_running_containers()
    
    if containers:
        containers_table = Table(title="Running Containers", show_header=True, header_style="bold cyan")
        containers_table.add_column("Name", style="cyan", width=25)
        containers_table.add_column("Image", style="yellow", width=30)
        containers_table.add_column("Status", style="green", width=20)
        
        for container in containers:
            containers_table.add_row(
                container['name'],
                container['image'],
                container['status']
            )
        
        console.print(containers_table)
    else:
        console.print(format_warning("No AICO containers are currently running"))
    
    console.print()
    
    # Check Postgres health
    if _check_postgres_health():
        console.print(format_success("✅ Database connection: Healthy"))
    else:
        console.print(format_warning("⚠️  Database connection: Unable to verify"))


@app.command("check")
def upgrade_check():
    """Check if system is ready for upgrade."""
    console.print(Panel("[bold cyan]Pre-Upgrade Checks[/bold cyan]", expand=False))
    
    checks_passed = True
    
    # Check 1: Docker running
    try:
        subprocess.run(["docker", "ps"], capture_output=True, check=True, timeout=5)
        console.print(format_success("✅ Docker is running"))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        console.print(format_error("❌ Docker is not running"))
        checks_passed = False
    
    # Check 2: Containers running
    containers = _get_running_containers()
    if containers:
        console.print(format_success(f"✅ Found {len(containers)} AICO containers"))
    else:
        console.print(format_warning("⚠️  No AICO containers running"))
    
    # Check 3: Postgres health
    if _check_postgres_health():
        console.print(format_success("✅ Database connection healthy"))
    else:
        console.print(format_error("❌ Database connection failed"))
        checks_passed = False
    
    # Check 4: Compose file exists
    compose_file = _get_compose_file()
    if compose_file.exists():
        console.print(format_success(f"✅ Docker Compose file found: {compose_file}"))
    else:
        console.print(format_error(f"❌ Docker Compose file not found: {compose_file}"))
        checks_passed = False
    
    # Check 5: Backup directory writable
    repo_root = _get_aico_repo_root()
    backup_dir = repo_root / "backups"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        test_file = backup_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        console.print(format_success(f"✅ Backup directory writable: {backup_dir}"))
    except Exception as e:
        console.print(format_error(f"❌ Backup directory not writable: {e}"))
        checks_passed = False
    
    console.print()
    
    if checks_passed:
        console.print(format_success("✅ System is ready for upgrade"))
    else:
        console.print(format_error("❌ System is NOT ready for upgrade. Please fix the issues above."))
        raise typer.Exit(1)


@app.command("run")
@sensitive
def upgrade_run(
    skip_backup: bool = typer.Option(False, "--skip-backup", help="Skip database backup (not recommended)"),
    services: Optional[List[str]] = typer.Option(None, "--service", "-s", help="Specific services to upgrade (default: all)"),
):
    """Run system upgrade with safety checks and rollback capability."""
    console.print(Panel("[bold cyan]AICO System Upgrade[/bold cyan]", expand=False))
    
    # Pre-flight checks
    console.print(format_info("Running pre-flight checks..."))
    try:
        upgrade_check.callback()
    except typer.Exit:
        console.print(format_error("Pre-flight checks failed. Aborting upgrade."))
        raise
    
    console.print()
    
    # Create backup
    backup_file = None
    if not skip_backup:
        backup_file = _backup_database()
        if not backup_file:
            console.print(format_error("Failed to create backup. Aborting upgrade."))
            console.print(format_info("Use --skip-backup to proceed without backup (not recommended)"))
            raise typer.Exit(1)
    else:
        console.print(format_warning("⚠️  Skipping database backup (--skip-backup flag)"))
    
    console.print()
    
    # Determine services to upgrade
    compose_file = _get_compose_file()
    
    if services:
        service_list = services
        console.print(format_info(f"Upgrading specific services: {', '.join(service_list)}"))
    else:
        service_list = ["gateway", "core", "modelservice"]
        console.print(format_info("Upgrading all AICO services"))
    
    # Pull latest images
    console.print(format_info("Pulling latest container images..."))
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Pulling images...", total=None)
            
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "pull"] + service_list,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                console.print(format_error(f"Failed to pull images: {result.stderr}"))
                raise typer.Exit(1)
        
        console.print(format_success("✅ Images pulled successfully"))
    except subprocess.TimeoutExpired:
        console.print(format_error("Image pull timed out"))
        raise typer.Exit(1)
    
    console.print()
    
    # Rebuild containers
    console.print(format_info("Building updated containers..."))
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Building containers...", total=None)
            
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "build"] + service_list,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                console.print(format_error(f"Failed to build containers: {result.stderr}"))
                raise typer.Exit(1)
        
        console.print(format_success("✅ Containers built successfully"))
    except subprocess.TimeoutExpired:
        console.print(format_error("Container build timed out"))
        raise typer.Exit(1)
    
    console.print()
    
    # Restart services
    console.print(format_info("Restarting services with new containers..."))
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"] + service_list,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            console.print(format_error(f"Failed to restart services: {result.stderr}"))
            console.print(format_warning("Services may be in inconsistent state. Check logs with 'aico logs'"))
            raise typer.Exit(1)
        
        console.print(format_success("✅ Services restarted successfully"))
    except subprocess.TimeoutExpired:
        console.print(format_error("Service restart timed out"))
        raise typer.Exit(1)
    
    console.print()
    
    # Verify health
    console.print(format_info("Verifying system health..."))
    import time
    time.sleep(5)  # Give services time to start
    
    if _check_postgres_health():
        console.print(format_success("✅ Database connection verified"))
    else:
        console.print(format_warning("⚠️  Database connection could not be verified"))
    
    console.print()
    console.print(Panel(
        "[bold green]✅ Upgrade completed successfully![/bold green]\n\n"
        f"Backup location: {backup_file if backup_file else 'N/A'}\n"
        "Run 'aico upgrade status' to verify system state.",
        title="Upgrade Complete",
        border_style="green"
    ))


@app.command("rollback")
@sensitive
def upgrade_rollback(
    backup_file: Optional[Path] = typer.Option(None, "--backup", "-b", help="Backup file to restore from"),
):
    """Rollback to previous version using backup."""
    console.print(Panel("[bold yellow]AICO System Rollback[/bold yellow]", expand=False))
    
    if not backup_file:
        # Find most recent backup
        repo_root = _get_aico_repo_root()
        backup_dir = repo_root / "backups" / "pre-upgrade"
        
        if not backup_dir.exists():
            console.print(format_error("No backup directory found"))
            raise typer.Exit(1)
        
        backups = sorted(backup_dir.glob("*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if not backups:
            console.print(format_error("No backup files found"))
            raise typer.Exit(1)
        
        backup_file = backups[0]
        console.print(format_info(f"Using most recent backup: {backup_file.name}"))
    
    if not backup_file.exists():
        console.print(format_error(f"Backup file not found: {backup_file}"))
        raise typer.Exit(1)
    
    # Confirm rollback
    console.print(format_warning("⚠️  This will restore the database from backup and may result in data loss."))
    confirm = typer.confirm("Are you sure you want to proceed with rollback?")
    
    if not confirm:
        console.print(format_info("Rollback cancelled"))
        raise typer.Exit(0)
    
    # Restore database
    console.print(format_info("Restoring database from backup..."))
    try:
        with open(backup_file, 'r') as f:
            backup_sql = f.read()
        
        result = subprocess.run(
            [
                "docker", "exec", "-i", "aico-postgres",
                "sh", "-c",
                "PGPASSWORD=$(cat /run/secrets/pg_password) psql -U postgres -d aico"
            ],
            input=backup_sql,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            console.print(format_error(f"Failed to restore database: {result.stderr}"))
            raise typer.Exit(1)
        
        console.print(format_success("✅ Database restored successfully"))
        
    except subprocess.TimeoutExpired:
        console.print(format_error("Database restore timed out"))
        raise typer.Exit(1)
    except Exception as e:
        console.print(format_error(f"Failed to restore database: {e}"))
        raise typer.Exit(1)
    
    console.print()
    console.print(Panel(
        "[bold green]✅ Rollback completed successfully![/bold green]\n\n"
        f"Restored from: {backup_file}\n"
        "Run 'aico upgrade status' to verify system state.",
        title="Rollback Complete",
        border_style="green"
    ))


if __name__ == "__main__":
    app()
