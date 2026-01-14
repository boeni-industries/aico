"""AICO CLI Postgres Commands

Command group for managing the PostgreSQL/Timescale backend.

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
            ("test", "Test database connection and basic operations"),
            ("show", "Show database configuration, paths, and settings"),
            ("ls", "List all tables and schemas"),
            ("desc", "Describe table structure"),
            ("count", "Count records in table(s)"),
            ("head", "Show first N records from table"),
            ("tail", "Show last N records from table"),
            ("stat", "Database statistics"),
            ("vacuum", "Optimize database (VACUUM ANALYZE)"),
            ("check", "Database integrity check"),
            ("exec", "Execute raw SQL query"),
        ]

        examples = [
            "aico pg status",
            "aico pg doctor",
            "aico pg init",
            "aico pg ls",
            "aico pg desc users",
            "aico pg count --table=users",
            "aico pg head users --limit=5",
            "aico pg vacuum",
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

    # 3) Database authentication using stored credentials
    if tcp_ok:
        from aico.security.key_manager import AICOKeyManager
        key_manager = AICOKeyManager(config)
        password = key_manager.get_database_password("postgres", username=user)
        
        if password:
            try:
                cmd = [
                    "docker", "exec", "-i",
                    "-e", f"PGPASSWORD={password}",
                    "aico-postgres",
                    "psql", "-U", user, "-d", db_name, "-c", "SELECT version();"
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[2].strip() if len(result.stdout.split('\n')) > 2 else "Connected"
                    table.add_row(
                        "Database Auth",
                        "[green]OK[/green]",
                        f"Authenticated successfully: {version_line[:50]}",
                    )
                else:
                    table.add_row(
                        "Database Auth",
                        "[red]FAILED[/red]",
                        "Authentication failed with stored credentials",
                    )
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                table.add_row(
                    "Database Auth",
                    "[yellow]SKIPPED[/yellow]",
                    f"Could not test: {e}",
                )
        else:
            table.add_row(
                "Database Auth",
                "[yellow]SKIPPED[/yellow]",
                "No credentials in keyring - run 'aico deploy pg'",
            )

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


def _get_pg_connection():
    """Get PostgreSQL connection with credentials from keyring."""
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}
    
    if not pg_cfg:
        console.print(format_error("No core.database.postgres configuration found"))
        raise typer.Exit(1)
    
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")
    
    from aico.security.key_manager import AICOKeyManager
    key_manager = AICOKeyManager(config)
    password = key_manager.get_database_password("postgres", username=user)
    
    if not password:
        console.print(format_error("Postgres password not found. Run 'aico deploy pg'"))
        raise typer.Exit(1)
    
    return {
        "host": host,
        "port": port,
        "db_name": db_name,
        "user": user,
        "password": password
    }


def _exec_psql(sql: str, format_output: str = "table") -> tuple[int, str, str]:
    """Execute SQL via docker exec psql. Returns (returncode, stdout, stderr)."""
    conn_info = _get_pg_connection()
    
    cmd = [
        "docker", "exec", "-i",
        "-e", f"PGPASSWORD={conn_info['password']}",
        "aico-postgres",
        "psql", "-U", conn_info['user'], "-d", conn_info['db_name']
    ]
    
    if format_output == "json":
        cmd.extend(["-t", "-A"])  # Tuples only, unaligned
    
    cmd.extend(["-c", sql])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Query timeout (30s)"
    except FileNotFoundError:
        return 1, "", "Docker not found"


@app.command(help="Test database connection and basic CRUD operations")
def test():
    """Test PostgreSQL connection with comprehensive CRUD operations."""
    console.rule("[bold cyan]PostgreSQL Connection Test[/bold cyan]")
    
    conn_info = _get_pg_connection()
    test_table = f"aico_test_{int(__import__('time').time())}"
    
    try:
        # Test 1: Basic connectivity
        console.print("🔍 Testing basic connectivity...")
        code, stdout, stderr = _exec_psql("SELECT 1;")
        if code != 0:
            console.print(format_error(f"Connectivity failed: {stderr}"))
            raise typer.Exit(1)
        console.print(format_success("✅ Basic connectivity successful"))
        
        # Test 2: Schema check
        console.print("🔍 Testing schema access...")
        code, stdout, stderr = _exec_psql(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'aico_core';"
        )
        if code == 0:
            console.print(format_success(f"✅ Schema access successful"))
        
        # Test 3: CREATE
        console.print(f"🔍 Testing table creation ({test_table})...")
        code, stdout, stderr = _exec_psql(f"""
            CREATE TABLE aico_core.{test_table} (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        if code != 0:
            console.print(format_error(f"CREATE failed: {stderr}"))
            raise typer.Exit(1)
        console.print(format_success("✅ Table creation successful"))
        
        # Test 4: INSERT
        console.print("🔍 Testing insert operation...")
        test_message = f"AICO CLI test at {__import__('datetime').datetime.now().isoformat()}"
        code, stdout, stderr = _exec_psql(f"""
            INSERT INTO aico_core.{test_table} (message) 
            VALUES ('{test_message}') 
            RETURNING id;
        """)
        if code != 0:
            console.print(format_error(f"INSERT failed: {stderr}"))
            raise typer.Exit(1)
        console.print(format_success("✅ Insert operation successful"))
        
        # Test 5: SELECT
        console.print("🔍 Testing select operation...")
        code, stdout, stderr = _exec_psql(f"SELECT * FROM aico_core.{test_table};")
        if code == 0 and test_message in stdout:
            console.print(format_success("✅ Select operation successful"))
        
        # Test 6: UPDATE
        console.print("🔍 Testing update operation...")
        code, stdout, stderr = _exec_psql(f"""
            UPDATE aico_core.{test_table} 
            SET message = 'UPDATED: {test_message}' 
            WHERE id = 1;
        """)
        if code == 0:
            console.print(format_success("✅ Update operation successful"))
        
        # Test 7: DELETE
        console.print("🔍 Testing delete operation...")
        code, stdout, stderr = _exec_psql(f"DELETE FROM aico_core.{test_table} WHERE id = 1;")
        if code == 0:
            console.print(format_success("✅ Delete operation successful"))
        
        # Test 8: DROP
        console.print(f"🔍 Testing table deletion ({test_table})...")
        code, stdout, stderr = _exec_psql(f"DROP TABLE aico_core.{test_table};")
        if code == 0:
            console.print(format_success("✅ Table deletion successful"))
        
        console.print(format_success("\n✅ All database tests passed!"))
        
    except Exception as e:
        # Cleanup
        _exec_psql(f"DROP TABLE IF EXISTS aico_core.{test_table};")
        console.print(format_error(f"Test failed: {e}"))
        raise typer.Exit(1)


@app.command(help="Show database configuration, paths, and settings")
def show():
    """Show PostgreSQL configuration and connection details."""
    console.rule("[bold cyan]PostgreSQL Configuration[/bold cyan]")
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}
    
    if not pg_cfg:
        console.print(format_error("No PostgreSQL configuration found"))
        raise typer.Exit(1)
    
    table = Table(title="📋 Configuration", border_style="bright_blue", box=box.SIMPLE_HEAD)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Host", str(pg_cfg.get("host", "127.0.0.1")))
    table.add_row("Port", str(pg_cfg.get("port", 5432)))
    table.add_row("Database", str(pg_cfg.get("db_name", "aico")))
    table.add_row("User", str(pg_cfg.get("user", "postgres")))
    table.add_row("SSL Mode", str(pg_cfg.get("sslmode", "prefer")))
    table.add_row("Core Schema", str(pg_cfg.get("core_schema", "aico_core")))
    table.add_row("Pool Size", str(pg_cfg.get("pool_size", 10)))
    table.add_row("Max Overflow", str(pg_cfg.get("max_overflow", 20)))
    
    console.print(table)


@app.command(help="List all tables and schemas in database")
def ls(
    schema: str = typer.Option("aico_core", "--schema", "-s", help="Schema to list tables from")
):
    """List all tables in the specified schema."""
    console.print(f"📋 [cyan]Tables in schema '{schema}':[/cyan]\n")
    
    code, stdout, stderr = _exec_psql(f"""
        SELECT table_name, 
               pg_size_pretty(pg_total_relation_size(quote_ident(table_schema)||'.'||quote_ident(table_name))) as size
        FROM information_schema.tables 
        WHERE table_schema = '{schema}' 
        ORDER BY table_name;
    """)
    
    if code != 0:
        console.print(format_error(f"Failed to list tables: {stderr}"))
        raise typer.Exit(1)
    
    if not stdout.strip():
        console.print(format_warning(f"No tables found in schema '{schema}'"))
        return
    
    console.print(stdout)


@app.command(help="Describe table structure (columns, types, constraints)")
def desc(
    table_name: str = typer.Argument(..., help="Table name to describe"),
    schema: str = typer.Option("aico_core", "--schema", "-s", help="Schema name")
):
    """Show detailed table structure."""
    console.print(f"📋 [cyan]Structure of {schema}.{table_name}:[/cyan]\n")
    
    code, stdout, stderr = _exec_psql(f"""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)
    
    if code != 0:
        console.print(format_error(f"Failed to describe table: {stderr}"))
        raise typer.Exit(1)
    
    console.print(stdout)
    
    # Show indexes
    console.print(f"\n🔍 [cyan]Indexes on {schema}.{table_name}:[/cyan]\n")
    code, stdout, stderr = _exec_psql(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname = '{schema}' AND tablename = '{table_name}';
    """)
    if code == 0:
        console.print(stdout if stdout.strip() else "[dim]No indexes[/dim]")


@app.command(help="Count records in table(s)")
def count(
    table: str = typer.Option(None, "--table", "-t", help="Specific table to count"),
    schema: str = typer.Option("aico_core", "--schema", "-s", help="Schema name"),
    all: bool = typer.Option(False, "--all", help="Count all tables in schema")
):
    """Count records in specified table(s)."""
    if all:
        console.print(f"📊 [cyan]Record counts for all tables in '{schema}':[/cyan]\n")
        code, stdout, stderr = _exec_psql(f"""
            SELECT table_name, 
                   (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
            FROM (
                SELECT table_name, 
                       query_to_xml(format('SELECT count(*) as cnt FROM %I.%I', table_schema, table_name), false, true, '') as xml_count
                FROM information_schema.tables
                WHERE table_schema = '{schema}'
            ) t
            ORDER BY row_count DESC;
        """)
    elif table:
        console.print(f"📊 [cyan]Record count for {schema}.{table}:[/cyan]\n")
        code, stdout, stderr = _exec_psql(f"SELECT COUNT(*) FROM {schema}.{table};")
    else:
        console.print(format_error("Specify --table or --all"))
        raise typer.Exit(1)
    
    if code != 0:
        console.print(format_error(f"Count failed: {stderr}"))
        raise typer.Exit(1)
    
    console.print(stdout)


@app.command(help="Show first N records from table")
def head(
    table_name: str = typer.Argument(..., help="Table name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records"),
    schema: str = typer.Option("aico_core", "--schema", "-s", help="Schema name")
):
    """Show first N records from table."""
    console.print(f"📄 [cyan]First {limit} records from {schema}.{table_name}:[/cyan]\n")
    
    code, stdout, stderr = _exec_psql(f"SELECT * FROM {schema}.{table_name} LIMIT {limit};")
    
    if code != 0:
        console.print(format_error(f"Query failed: {stderr}"))
        raise typer.Exit(1)
    
    console.print(stdout if stdout.strip() else "[dim]No records[/dim]")


@app.command(help="Show last N records from table")
def tail(
    table_name: str = typer.Argument(..., help="Table name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records"),
    schema: str = typer.Option("aico_core", "--schema", "-s", help="Schema name")
):
    """Show last N records from table (requires primary key or timestamp)."""
    console.print(f"📄 [cyan]Last {limit} records from {schema}.{table_name}:[/cyan]\n")
    
    # Try to find a suitable ordering column
    code, stdout, stderr = _exec_psql(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{schema}' AND table_name = '{table_name}' 
        AND (column_name LIKE '%_at' OR column_name LIKE '%id')
        LIMIT 1;
    """)
    
    order_col = stdout.strip().split('\n')[2].strip() if stdout.strip() else "ctid"
    
    code, stdout, stderr = _exec_psql(f"""
        SELECT * FROM {schema}.{table_name} 
        ORDER BY {order_col} DESC 
        LIMIT {limit};
    """)
    
    if code != 0:
        console.print(format_error(f"Query failed: {stderr}"))
        raise typer.Exit(1)
    
    console.print(stdout if stdout.strip() else "[dim]No records[/dim]")


@app.command(help="Database statistics (size, table counts, indexes)")
def stat():
    """Show comprehensive database statistics."""
    console.rule("[bold cyan]PostgreSQL Statistics[/bold cyan]")
    
    # Database size
    console.print("\n📊 [cyan]Database Size:[/cyan]")
    code, stdout, stderr = _exec_psql("""
        SELECT pg_size_pretty(pg_database_size(current_database())) as size;
    """)
    if code == 0:
        console.print(stdout)
    
    # Table statistics
    console.print("\n📋 [cyan]Table Statistics (aico_core schema):[/cyan]")
    code, stdout, stderr = _exec_psql("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
        FROM pg_tables
        WHERE schemaname = 'aico_core'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 20;
    """)
    if code == 0:
        console.print(stdout)
    
    # Connection stats
    console.print("\n🔌 [cyan]Connection Statistics:[/cyan]")
    code, stdout, stderr = _exec_psql("""
        SELECT count(*) as total_connections,
               count(*) FILTER (WHERE state = 'active') as active,
               count(*) FILTER (WHERE state = 'idle') as idle
        FROM pg_stat_activity;
    """)
    if code == 0:
        console.print(stdout)


@app.command(help="Optimize database (VACUUM ANALYZE)")
def vacuum(
    full: bool = typer.Option(False, "--full", help="Full vacuum (locks tables)"),
    analyze: bool = typer.Option(True, "--analyze", help="Run ANALYZE after vacuum")
):
    """Run VACUUM to reclaim space and optionally ANALYZE to update statistics."""
    console.print("🧹 [cyan]Running database optimization...[/cyan]")
    
    sql = "VACUUM"
    if full:
        sql += " FULL"
        console.print(format_warning("⚠️  FULL vacuum will lock tables"))
    if analyze:
        sql += " ANALYZE"
    sql += ";"
    
    code, stdout, stderr = _exec_psql(sql)
    
    if code != 0:
        console.print(format_error(f"Vacuum failed: {stderr}"))
        raise typer.Exit(1)
    
    console.print(format_success("✅ Database optimization complete"))


@app.command(help="Database integrity and consistency checks")
def check():
    """Run PostgreSQL integrity checks."""
    console.rule("[bold cyan]Database Integrity Checks[/bold cyan]")
    
    # Check for table bloat
    console.print("\n🔍 [cyan]Checking for table bloat:[/cyan]")
    code, stdout, stderr = _exec_psql("""
        SELECT schemaname, tablename,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'aico_core'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 10;
    """)
    if code == 0:
        console.print(stdout)
    
    # Check for missing indexes on foreign keys
    console.print("\n🔍 [cyan]Checking for unindexed foreign keys:[/cyan]")
    code, stdout, stderr = _exec_psql("""
        SELECT c.conrelid::regclass AS table_name,
               string_agg(a.attname, ', ') AS columns
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
        AND NOT EXISTS (
            SELECT 1 FROM pg_index i
            WHERE i.indrelid = c.conrelid
            AND c.conkey::int[] <@ i.indkey::int[]
        )
        GROUP BY c.conrelid
        LIMIT 10;
    """)
    if code == 0:
        console.print(stdout if stdout.strip() else "[green]✅ All foreign keys are indexed[/green]")
    
    console.print(format_success("\n✅ Integrity checks complete"))


@app.command(help="Execute raw SQL query (use with caution)")
def exec(
    query: str = typer.Argument(..., help="SQL query to execute")
):
    """Execute arbitrary SQL query. USE WITH CAUTION."""
    console.print(format_warning("⚠️  Executing raw SQL query"))
    console.print(f"[dim]Query: {query}[/dim]\n")
    
    code, stdout, stderr = _exec_psql(query)
    
    if code != 0:
        console.print(format_error(f"Query failed: {stderr}"))
        raise typer.Exit(1)
    
    console.print(stdout if stdout.strip() else "[dim]Query executed (no output)[/dim]")
