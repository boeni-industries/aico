"""AICO CLI Postgres Commands

Command group for managing the Postgres/Timescale backend that will replace LibSQL.

This module is intentionally minimal for now and will be extended as the
Postgres migration is implemented. It follows the same patterns as the
existing `database` command group (aico db ...).
"""

import sys
import socket
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Add shared module to path for CLI usage (mirrors database.py pattern)
if getattr(sys, "frozen", False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / "shared"
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths

from cli.utils.help_formatter import format_subcommand_help
from cli.utils.formatting import (
    format_error,
    format_success,
    format_warning,
    format_info,
)

console = Console()


def _get_compose_file() -> Path:
    """Return path to the local docker-compose file for DB services."""
    # cli/commands/pg.py -> project root
    root = Path(__file__).parent.parent.parent
    return root / "docker" / "docker-compose.local.yml"


def _run_compose(args: list[str]) -> int:
    """Run docker compose with the given args, handling basic errors.

    Returns the subprocess return code.
    """

    compose_file = _get_compose_file()
    if not compose_file.exists():
        console.print(
            format_error(
                f"Docker compose file not found: {compose_file}. "
                "Ensure local docker configuration is present."
            )
        )
        return 1

    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
    ] + args

    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            console.print(
                format_error(
                    f"docker compose command failed with exit code {result.returncode}:\n"
                    + " ".join(cmd)
                )
            )
        return result.returncode
    except FileNotFoundError:
        console.print(
            format_error(
                "'docker' command not found. Install Docker and ensure it is on your PATH."
            )
        )
        return 1


def pg_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show Postgres backend configuration and basic reachability"),
            ("doctor", "Run detailed environment checks for Postgres"),
            ("init", "Initialize or update the Postgres schema (idempotent)"),
            ("start", "Start the Postgres container (docker-compose local)"),
            ("stop", "Stop the Postgres container (docker-compose local)"),
        ]

        examples = [
            "aico pg status",
            "aico pg doctor",
            "aico pg init",
            "aico pg start",
            "aico pg stop",
        ]

        format_subcommand_help(
            console=console,
            command_name="pg",
            description="Postgres/Timescale backend management (scaffold)",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Postgres backend management (experimental)",
    callback=pg_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


@app.command(help="Show Postgres backend status with comprehensive health checks")
def status():
    """Show configuration and perform comprehensive health checks.
    
    Checks:
    - Configuration presence
    - Container status (if using docker-compose)
    - TCP connectivity
    - Database authentication
    - Schema existence
    - Credential availability
    """

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}

    console.rule("[bold cyan]Postgres Backend Status[/bold cyan]")

    if not pg_cfg:
        console.print(format_error("No core.database.postgres configuration found in core.yaml"))
        raise typer.Exit(code=1)

    # Extract config
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")
    sslmode = pg_cfg.get("sslmode", "prefer")
    core_schema = pg_cfg.get("core_schema", "aico_core")

    # Configuration table
    config_table = Table(
        title="📋 Configuration",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    config_table.add_column("Property", style="cyan")
    config_table.add_column("Value", style="white")
    config_table.add_row("Host", str(host))
    config_table.add_row("Port", str(port))
    config_table.add_row("Database", str(db_name))
    config_table.add_row("User", str(user))
    config_table.add_row("SSL Mode", str(sslmode))
    config_table.add_row("Core Schema", str(core_schema))
    console.print(config_table)
    console.print()

    # Health checks table
    health_table = Table(
        title="🏥 Health Checks",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    health_table.add_column("Check", style="cyan", justify="left")
    health_table.add_column("Status", justify="left")
    health_table.add_column("Details", style="dim", justify="left")

    # 1. Container status check
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=aico-postgres", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            container_status = result.stdout.strip()
            if "Up" in container_status:
                health_table.add_row("Container", "[green]✓ Running[/green]", container_status)
            else:
                health_table.add_row("Container", "[yellow]⚠ Not running[/yellow]", container_status)
        else:
            health_table.add_row("Container", "[yellow]⚠ Not found[/yellow]", "Run 'aico deploy pg' to start")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        health_table.add_row("Container", "[dim]○ Unknown[/dim]", "Docker not available")

    # 2. TCP connectivity
    try:
        with socket.create_connection((host, port), timeout=3.0):
            health_table.add_row("TCP Connectivity", "[green]✓ Connected[/green]", f"{host}:{port}")
            tcp_ok = True
    except OSError as exc:
        health_table.add_row("TCP Connectivity", "[red]✗ Failed[/red]", f"{exc.__class__.__name__}")
        tcp_ok = False

    # 3. Credential availability
    from aico.security.key_manager import AICOKeyManager
    key_manager = AICOKeyManager(config)
    password = key_manager.get_database_password("postgres", username=user)
    
    if password:
        health_table.add_row("Credentials", "[green]✓ Available[/green]", "Stored in keyring")
        has_password = True
    else:
        health_table.add_row("Credentials", "[yellow]⚠ Missing[/yellow]", "Run 'aico deploy pg'")
        has_password = False

    # 4. Database authentication (only if TCP works and we have password)
    if tcp_ok and has_password:
        try:
            cmd = [
                "docker", "exec", "-i",
                "-e", f"PGPASSWORD={password}",
                "aico-postgres",
                "psql", "-U", user, "-d", db_name, "-c", "SELECT 1;"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                health_table.add_row("Database Auth", "[green]✓ Authenticated[/green]", "Connection successful")
                db_ok = True
            else:
                health_table.add_row("Database Auth", "[red]✗ Failed[/red]", "Authentication error")
                db_ok = False
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            health_table.add_row("Database Auth", "[yellow]⚠ Skipped[/yellow]", str(e))
            db_ok = False
    else:
        health_table.add_row("Database Auth", "[dim]○ Skipped[/dim]", "Prerequisites not met")
        db_ok = False

    # 5. Schema existence check (only if DB connection works)
    if db_ok:
        try:
            cmd = [
                "docker", "exec", "-i",
                "-e", f"PGPASSWORD={password}",
                "aico-postgres",
                "psql", "-U", user, "-d", db_name, "-t", "-c",
                f"SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = '{core_schema}');"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "t" in result.stdout:
                health_table.add_row("Schema Exists", "[green]✓ Found[/green]", f"Schema '{core_schema}' exists")
            else:
                health_table.add_row("Schema Exists", "[yellow]⚠ Not found[/yellow]", "Run 'aico pg init'")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            health_table.add_row("Schema Exists", "[dim]○ Unknown[/dim]", "Could not verify")
    else:
        health_table.add_row("Schema Exists", "[dim]○ Skipped[/dim]", "Database not accessible")

    console.print(health_table)
    console.print()

    # Summary
    if tcp_ok and has_password and db_ok:
        console.print(format_success("✅ Postgres is healthy and ready"))
    elif tcp_ok and has_password:
        console.print(format_warning("⚠️  Postgres is reachable but database connection failed"))
    elif tcp_ok:
        console.print(format_warning("⚠️  Postgres is reachable but credentials are missing"))
    else:
        console.print(format_error("❌ Postgres is not accessible. Run 'aico deploy pg' to set up."))


@app.command(help="Run detailed environment checks for Postgres/Timescale")
def doctor():
    """Run a series of checks to validate the Postgres environment.

    This command assumes Postgres is installed by the OS (or via Docker) and
    focuses on verifying that AICO can talk to it and that basic tools are
    available:

    - core.database.postgres configuration presence.
    - TCP connectivity to host:port.
    """

    console.rule("[bold cyan]Postgres / Timescale Doctor[/bold cyan]")

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}

    if not pg_cfg:
        console.print(
            format_error(
                "No core.database.postgres configuration found in core.yaml. "
                "Please configure host/port/db_name/user before running 'aico pg doctor'."
            )
        )
        raise typer.Exit(code=1)

    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "aico")
    sslmode = pg_cfg.get("sslmode", "prefer")

    table = Table(
        title="✨ [bold cyan]Environment Checks[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Check", style="cyan", justify="left")
    table.add_column("Result", style="green", justify="left")
    table.add_column("Details", style="white", justify="left")

    # 1) Config present
    table.add_row(
        "Configuration",
        "[green]OK[/green]",
        f"host={host}, port={port}, db={db_name}, user={user}, sslmode={sslmode}",
    )

    # 2) TCP connectivity
    try:
        with socket.create_connection((host, port), timeout=3.0):
            table.add_row(
                "TCP connectivity",
                "[green]OK[/green]",
                f"Successfully connected to {host}:{port}",
            )
            tcp_ok = True
    except OSError as exc:  # pragma: no cover - best-effort diagnostic
        table.add_row(
            "TCP connectivity",
            "[red]FAILED[/red]",
            f"Could not connect to {host}:{port} ({exc.__class__.__name__}: {exc})",
        )
        tcp_ok = False

    console.print(table)

    console.print(
        "\n[blue]Next steps:[/blue] If TCP connectivity or psql checks failed, "
        "ensure your Postgres server is running, listening on the configured "
        "host/port, and that client tools are installed. Once these checks "
        "pass, run 'aico pg init' to finalize the AICO database schema."
    )


@app.command(help="Initialize or update the Postgres schema (idempotent)")
def init():
    """Initialize or update the Postgres schema.

    This command applies the authoritative schema.sql to the running Postgres
    container. It is idempotent: CREATE TABLE IF NOT EXISTS and CREATE INDEX
    IF NOT EXISTS statements ensure repeated runs are safe.
    """

    console.rule("[bold cyan]Postgres Init[/bold cyan]")

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}

    if not pg_cfg:
        console.print(
            format_error(
                "No core.database.postgres configuration found in core.yaml. "
                "Please configure host/port/db_name/user before running 'aico pg init'."
            )
        )
        raise typer.Exit(code=1)

    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")

    # Get password from keyring
    from aico.security.key_manager import AICOKeyManager
    key_manager = AICOKeyManager(config)
    password = key_manager.get_database_password("postgres", username=user)
    
    if not password:
        console.print(
            format_error(
                "Postgres password not found in keyring. "
                "Run 'aico deploy pg' to auto-generate and store credentials."
            )
        )
        raise typer.Exit(code=1)

    # Basic connectivity check
    try:
        with socket.create_connection((host, port), timeout=3.0):
            console.print(
                format_success(f"Postgres reachable at {host}:{port}; proceeding with schema init.")
            )
    except OSError as exc:
        console.print(
            format_error(
                f"Cannot connect to Postgres at {host}:{port} ({exc.__class__.__name__}: {exc}). "
                "Start the server/container before running 'aico pg init'."
            )
        )
        raise typer.Exit(code=1)

    # Locate schema.sql
    schema_path = Path(__file__).parent.parent.parent / "shared" / "aico" / "data" / "postgres" / "schema.sql"
    if not schema_path.exists():
        console.print(
            format_error(
                f"Schema file not found: {schema_path}. "
                "Ensure shared/aico/data/postgres/schema.sql exists."
            )
        )
        raise typer.Exit(code=1)

    console.print(f"📄 [cyan]Applying schema from:[/cyan] {schema_path}")

    # Apply schema via docker exec + psql
    # We pipe the schema.sql into the container's psql
    # Set PGPASSWORD environment variable for authentication
    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={password}",  # Pass password via environment
            "aico-postgres",
            "psql", "-h", "localhost", "-U", user, "-d", db_name, "-v", "ON_ERROR_STOP=1"
        ]

        result = subprocess.run(
            cmd,
            input=schema_sql,
            text=True,
            capture_output=True,
            check=False
        )

        if result.returncode != 0:
            console.print(
                format_error(
                    f"Failed to apply schema (exit code {result.returncode}).\n"
                    f"STDERR: {result.stderr}"
                )
            )
            raise typer.Exit(code=1)

        # Count successful operations for progress feedback
        stdout_lines = result.stdout.strip().split('\n')
        create_count = sum(1 for line in stdout_lines if line.startswith('CREATE'))
        alter_count = sum(1 for line in stdout_lines if line.startswith('ALTER'))
        
        console.print(format_success(
            f"✅ Postgres schema applied successfully.\n"
            f"   Created {create_count} objects, applied {alter_count} constraints."
        ))

    except FileNotFoundError:
        console.print(
            format_error(
                "'docker' command not found. Install Docker and ensure it is on your PATH."
            )
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(
            format_error(f"Unexpected error during schema application: {exc}")
        )
        raise typer.Exit(code=1)


@app.command(help="Start the Postgres container using docker-compose.local.yml")
def start():
    """Start the local Postgres container (docker compose)."""

    console.print("🚀 [cyan]Starting Postgres container (docker compose)...[/cyan]")
    code = _run_compose(["up", "-d", "postgres"])
    if code != 0:
        raise typer.Exit(code)
    console.print(format_success("Postgres container started (if Docker is available)."))


@app.command(help="Stop the Postgres container using docker-compose.local.yml")
def stop():
    """Stop the local Postgres container (docker compose)."""

    console.print("🛑 [cyan]Stopping Postgres container (docker compose)...[/cyan]")
    code = _run_compose(["stop", "postgres"])
    if code != 0:
        raise typer.Exit(code)
    console.print(format_success("Postgres container stopped (if it was running)."))
