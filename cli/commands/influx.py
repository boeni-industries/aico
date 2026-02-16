"""AICO CLI InfluxDB Commands

Command group for managing and validating the external InfluxDB instance
used for telemetry/time-series data.

This assumes InfluxDB is installed and running (locally, remotely, or in a
container). The commands focus on configuration and connectivity checks,
not installation.
"""

import sys
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import typer
import requests
from rich.console import Console
from rich.table import Table
from rich import box

# Add shared module to path for CLI usage (mirrors database.py pattern)
if getattr(sys, "frozen", False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager

from cli.utils.help_formatter import format_subcommand_help
from cli.utils.formatting import (
    format_error,
    format_info,
    format_success,
    format_warning,
)

console = Console()


def influx_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit"),
):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show InfluxDB configuration and basic reachability"),
            ("doctor", "Run detailed environment checks for InfluxDB"),
            ("init", "Initialize or update the InfluxDB org/bucket (idempotent)"),
            ("start", "Start the InfluxDB container (docker-compose local)"),
            ("stop", "Stop the InfluxDB container (docker-compose local)"),
        ]

        examples = [
            "aico influx status",
            "aico influx doctor",
            "aico influx init",
            "aico influx start",
            "aico influx stop",
        ]

        format_subcommand_help(
            console=console,
            command_name="influx",
            description="InfluxDB telemetry backend management (scaffold)",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="InfluxDB telemetry backend management (experimental)",
    callback=influx_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


def _get_influx_config() -> dict:
    """Get InfluxDB configuration from core config.

    We expect a section like `database.influx` in core.yaml. If it is
    missing, callers decide how to report that to the user.
    """
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("influx", {}) or {}
    except Exception:
        return {}


def _get_compose_file() -> Path:
    """Return path to the local docker-compose file for DB services."""
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


@app.command(help="Show InfluxDB backend status with comprehensive health checks")
def status():
    """Show configuration and perform comprehensive health checks.
    
    Checks:
    - Configuration presence
    - Container status (if using docker-compose)
    - TCP connectivity
    - HTTP API health endpoint
    - Authentication with token
    - Org/bucket existence
    - Credential availability
    """

    cfg = _get_influx_config()

    console.rule("[bold cyan]InfluxDB Backend Status[/bold cyan]")

    if not cfg:
        console.print(format_error("No influx configuration found"))
        raise typer.Exit(code=1)

    # Extract config
    url = cfg.get("url", "http://127.0.0.1:8086")
    org = cfg.get("org", "aico")
    bucket = cfg.get("bucket", "aico_telemetry")

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8086)

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
    config_table.add_row("URL", url)
    config_table.add_row("Org", org)
    config_table.add_row("Bucket", bucket)
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
            ["docker", "ps", "--filter", "name=aico-influxdb", "--format", "{{.Status}}"],
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
            health_table.add_row("Container", "[yellow]⚠ Not found[/yellow]", "Run 'aico deploy influx' to start")
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

    # 3. HTTP health endpoint
    if tcp_ok:
        try:
            response = requests.get(f"{url}/health", timeout=3)
            if response.status_code == 200:
                health_table.add_row("HTTP Health", "[green]✓ Healthy[/green]", "API responding")
                http_ok = True
            else:
                health_table.add_row("HTTP Health", "[yellow]⚠ Unhealthy[/yellow]", f"Status {response.status_code}")
                http_ok = False
        except requests.RequestException as e:
            health_table.add_row("HTTP Health", "[red]✗ Failed[/red]", str(e)[:50])
            http_ok = False
    else:
        health_table.add_row("HTTP Health", "[dim]○ Skipped[/dim]", "TCP not connected")
        http_ok = False

    # 4. Credential availability
    from aico.security.key_manager import AICOKeyManager
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=True)
    key_manager = AICOKeyManager(config_manager)
    
    admin_token = key_manager.get_database_password("influx", username="admin_token")
    
    if admin_token:
        health_table.add_row("Credentials", "[green]✓ Available[/green]", "Token stored in keyring")
        has_token = True
    else:
        health_table.add_row("Credentials", "[yellow]⚠ Missing[/yellow]", "Run 'aico deploy influx'")
        has_token = False

    # 5. Authentication check (only if HTTP works and we have token)
    if http_ok and has_token:
        try:
            headers = {"Authorization": f"Token {admin_token}"}
            response = requests.get(f"{url}/api/v2/me", headers=headers, timeout=3)
            if response.status_code == 200:
                health_table.add_row("Authentication", "[green]✓ Authenticated[/green]", "Token valid")
                auth_ok = True
            else:
                health_table.add_row("Authentication", "[red]✗ Failed[/red]", f"Status {response.status_code}")
                auth_ok = False
        except requests.RequestException as e:
            health_table.add_row("Authentication", "[yellow]⚠ Error[/yellow]", str(e)[:50])
            auth_ok = False
    else:
        health_table.add_row("Authentication", "[dim]○ Skipped[/dim]", "Prerequisites not met")
        auth_ok = False

    # 6. Org existence check (only if authenticated)
    if auth_ok:
        try:
            headers = {"Authorization": f"Token {admin_token}"}
            response = requests.get(f"{url}/api/v2/orgs", headers=headers, timeout=3)
            if response.status_code == 200:
                orgs = response.json().get("orgs", [])
                org_exists = any(o.get("name") == org for o in orgs)
                if org_exists:
                    health_table.add_row("Org Exists", "[green]✓ Found[/green]", f"Org '{org}' exists")
                    org_ok = True
                else:
                    health_table.add_row("Org Exists", "[yellow]⚠ Not found[/yellow]", "Run 'aico influx init'")
                    org_ok = False
            else:
                health_table.add_row("Org Exists", "[yellow]⚠ Error[/yellow]", f"Status {response.status_code}")
                org_ok = False
        except requests.RequestException as e:
            health_table.add_row("Org Exists", "[dim]○ Unknown[/dim]", str(e)[:50])
            org_ok = False
    else:
        health_table.add_row("Org Exists", "[dim]○ Skipped[/dim]", "Not authenticated")
        org_ok = False

    # 7. Bucket existence check (only if org exists)
    if org_ok:
        try:
            headers = {"Authorization": f"Token {admin_token}"}
            response = requests.get(f"{url}/api/v2/buckets", headers=headers, params={"org": org}, timeout=3)
            if response.status_code == 200:
                buckets = response.json().get("buckets", [])
                bucket_exists = any(b.get("name") == bucket for b in buckets)
                if bucket_exists:
                    health_table.add_row("Bucket Exists", "[green]✓ Found[/green]", f"Bucket '{bucket}' exists")
                else:
                    health_table.add_row("Bucket Exists", "[yellow]⚠ Not found[/yellow]", "Run 'aico influx init'")
            else:
                health_table.add_row("Bucket Exists", "[yellow]⚠ Error[/yellow]", f"Status {response.status_code}")
        except requests.RequestException as e:
            health_table.add_row("Bucket Exists", "[dim]○ Unknown[/dim]", str(e)[:50])
    else:
        health_table.add_row("Bucket Exists", "[dim]○ Skipped[/dim]", "Org not found")

    console.print(health_table)
    console.print()

    # Data Overview (only if authenticated and bucket exists)
    if auth_ok and org_ok:
        try:
            from aico.data.influx.connection import InfluxDBConnection
            
            console.rule("[bold cyan]📊 Data Overview[/bold cyan]")
            
            with InfluxDBConnection() as conn:
                # Get all measurements from the bucket
                measurements_query = f'''
                    import "influxdata/influxdb/schema"
                    schema.measurements(bucket: "{bucket}")
                '''
                measurements_results = conn.query(measurements_query)
                measurements = sorted([r.get('_value') for r in measurements_results if r.get('_value')])
                
                if not measurements:
                    console.print("[yellow]No measurements found in bucket[/yellow]")
                    console.print()
                else:
                    data_table = Table(
                        border_style="bright_blue",
                        header_style="bold yellow",
                        box=box.SIMPLE_HEAD,
                        padding=(0, 1),
                    )
                    data_table.add_column("Measurement", style="cyan", justify="left")
                    data_table.add_column("Last 1h", justify="right")
                    data_table.add_column("Last 24h", justify="right")
                    data_table.add_column("Last 7d", justify="right")
                    data_table.add_column("Total", justify="right")
                    
                    total_1h = 0
                    total_24h = 0
                    total_7d = 0
                    total_all = 0
                    
                    for measurement in measurements:
                        # Count for different time ranges
                        query_1h = f'''
                            from(bucket: "{bucket}")
                            |> range(start: -1h)
                            |> filter(fn: (r) => r._measurement == "{measurement}")
                            |> count()
                        '''
                        results_1h = conn.query(query_1h)
                        count_1h = sum(r.get('value', 0) for r in results_1h)
                        
                        query_24h = f'''
                            from(bucket: "{bucket}")
                            |> range(start: -24h)
                            |> filter(fn: (r) => r._measurement == "{measurement}")
                            |> count()
                        '''
                        results_24h = conn.query(query_24h)
                        count_24h = sum(r.get('value', 0) for r in results_24h)
                        
                        query_7d = f'''
                            from(bucket: "{bucket}")
                            |> range(start: -7d)
                            |> filter(fn: (r) => r._measurement == "{measurement}")
                            |> count()
                        '''
                        results_7d = conn.query(query_7d)
                        count_7d = sum(r.get('value', 0) for r in results_7d)
                        
                        # Total (all time - limited to retention period)
                        query_all = f'''
                            from(bucket: "{bucket}")
                            |> range(start: -30d)
                            |> filter(fn: (r) => r._measurement == "{measurement}")
                            |> count()
                        '''
                        results_all = conn.query(query_all)
                        count_all = sum(r.get('value', 0) for r in results_all)
                        
                        # Format counts with color based on presence
                        def format_count(count):
                            if count == 0:
                                return "[dim]0[/dim]"
                            elif count < 100:
                                return f"[yellow]{count:,}[/yellow]"
                            else:
                                return f"[green]{count:,}[/green]"
                        
                        data_table.add_row(
                            measurement,
                            format_count(count_1h),
                            format_count(count_24h),
                            format_count(count_7d),
                            format_count(count_all)
                        )
                        
                        total_1h += count_1h
                        total_24h += count_24h
                        total_7d += count_7d
                        total_all += count_all
                    
                    # Add totals row
                    data_table.add_row(
                        "[bold]TOTAL[/bold]",
                        f"[bold cyan]{total_1h:,}[/bold cyan]",
                        f"[bold cyan]{total_24h:,}[/bold cyan]",
                        f"[bold cyan]{total_7d:,}[/bold cyan]",
                        f"[bold cyan]{total_all:,}[/bold cyan]"
                    )
                    
                    console.print(data_table)
                    console.print()
                    
                    # Data rate summary
                    if total_1h > 0:
                        rate_per_second = total_1h / 3600
                        rate_per_minute = total_1h / 60
                        console.print(f"[dim]Current rate: ~{rate_per_second:.1f} points/sec (~{rate_per_minute:.0f} points/min)[/dim]")
                        console.print()
                
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not fetch data overview: {e}[/yellow]")
            console.print()

    # Summary
    if tcp_ok and http_ok and has_token and auth_ok and org_ok:
        console.print(format_success("✅ InfluxDB is healthy and ready"))
    elif tcp_ok and http_ok and has_token and auth_ok:
        console.print(format_warning("⚠️  InfluxDB is accessible but org/bucket may need initialization"))
    elif tcp_ok and http_ok and has_token:
        console.print(format_warning("⚠️  InfluxDB is accessible but authentication failed"))
    elif tcp_ok and http_ok:
        console.print(format_warning("⚠️  InfluxDB is accessible but credentials are missing"))
    else:
        console.print(format_error("❌ InfluxDB is not accessible. Run 'aico deploy influx' to set up."))


@app.command(help="Run detailed environment checks for InfluxDB")
def doctor():
    """Run a series of checks to validate the InfluxDB environment.

    This assumes InfluxDB is installed and running (locally, remotely, or in
    a container) and focuses on:

    - Configuration presence.
    - TCP connectivity to the InfluxDB HTTP endpoint.
    - HTTP /health endpoint responsiveness.
    """

    console.rule("[bold cyan]InfluxDB Doctor[/bold cyan]")

    cfg = _get_influx_config()
    if not cfg:
        console.print(
            format_error(
                "No influx configuration found. "
                "Please configure url/org/bucket before running 'aico influx doctor'."
            )
        )
        raise typer.Exit(code=1)

    url = cfg.get("url", "http://127.0.0.1:8086")
    org = cfg.get("org", "aico")
    bucket = cfg.get("bucket", "aico_telemetry")

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8086)

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
        f"url={url}, org={org}, bucket={bucket}",
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

    # 3) HTTP /health check
    if tcp_ok:
        health_url = url.rstrip("/") + "/health"
        try:
            resp = requests.get(health_url, timeout=3.0)
            if resp.status_code == 200:
                table.add_row(
                    "HTTP /health",
                    "[green]OK[/green]",
                    f"{health_url} responded with 200",
                )
                http_ok = True
            else:
                table.add_row(
                    "HTTP /health",
                    "[red]FAILED[/red]",
                    f"{health_url} responded with HTTP {resp.status_code}",
                )
                http_ok = False
        except Exception as exc:  # pragma: no cover - best-effort diagnostic
            table.add_row(
                "HTTP /health",
                "[red]ERROR[/red]",
                f"Error calling {health_url}: {exc}",
            )
            http_ok = False
    else:
        table.add_row(
            "HTTP /health",
            "[yellow]SKIPPED[/yellow]",
            "Requires TCP connectivity first.",
        )
        http_ok = False

    # 4) API authentication using stored credentials
    if http_ok:
        from aico.security.key_manager import AICOKeyManager
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        key_manager = AICOKeyManager(config_manager)
        
        admin_token = key_manager.get_database_password("influx", username="admin_token")
        
        if admin_token:
            try:
                headers = {"Authorization": f"Token {admin_token}"}
                response = requests.get(f"{url}/api/v2/me", headers=headers, timeout=3)
                if response.status_code == 200:
                    user_data = response.json()
                    username = user_data.get("name", "unknown")
                    table.add_row(
                        "API Auth",
                        "[green]OK[/green]",
                        f"Authenticated as '{username}' using stored token",
                    )
                else:
                    table.add_row(
                        "API Auth",
                        "[red]FAILED[/red]",
                        f"Authentication failed with status {response.status_code}",
                    )
            except Exception as e:
                table.add_row(
                    "API Auth",
                    "[yellow]ERROR[/yellow]",
                    f"Could not test: {str(e)[:50]}",
                )
        else:
            table.add_row(
                "API Auth",
                "[yellow]SKIPPED[/yellow]",
                "No credentials in keyring - run 'aico deploy influx'",
            )

    console.print(table)

    console.print(
        "\n[blue]Next steps:[/blue] If TCP or HTTP checks failed, ensure your InfluxDB "
        "instance is running and reachable at the configured URL. Once these "
        "checks pass, you can enable instrumentation to start writing "
        "telemetry data to InfluxDB."
    )


@app.command(help="Initialize or update InfluxDB org/bucket (idempotent)")
def init(
    admin_password: str = typer.Option(
        ...,
        "--admin-password",
        envvar="AICO_INFLUX_ADMIN_PASSWORD",
        prompt=True,
        hide_input=True,
        help="Admin password for initial InfluxDB setup (or set AICO_INFLUX_ADMIN_PASSWORD)"
    ),
    admin_token: str = typer.Option(
        ...,
        "--admin-token",
        envvar="AICO_INFLUX_ADMIN_TOKEN",
        prompt=True,
        hide_input=True,
        help="Admin API token for InfluxDB (or set AICO_INFLUX_ADMIN_TOKEN)"
    ),
):
    """Initialize or update the InfluxDB org/bucket.

    This command performs initial InfluxDB setup:
    - Creates org 'aico' and bucket 'aico_telemetry' if they don't exist.
    - Generates an admin API token.
    - Sets retention policy for the bucket (30 days as per schema.lp).

    It is idempotent: if the org/bucket already exist, the command will skip
    creation and only update retention if needed.

    Required secrets:
    - AICO_INFLUX_ADMIN_PASSWORD: Admin password for initial setup.
    - AICO_INFLUX_ADMIN_TOKEN: API token to use (will be created if setup is fresh).

    After running this, store the token via 'aico security influx-set'.
    """

    console.rule("[bold cyan]InfluxDB Init[/bold cyan]")

    cfg = _get_influx_config()
    if not cfg:
        console.print(
            format_error(
                "No influx configuration found. "
                "Please configure url/org/bucket before running 'aico influx init'."
            )
        )
        raise typer.Exit(code=1)

    url = cfg.get("url", "http://127.0.0.1:8086")
    org = cfg.get("org", "aico")
    bucket = cfg.get("bucket", "aico_telemetry")

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8086)

    # Connectivity check
    try:
        with socket.create_connection((host, port), timeout=3.0):
            console.print(
                format_success(f"InfluxDB reachable at {host}:{port}; proceeding with init.")
            )
    except OSError as exc:
        console.print(
            format_error(
                f"Cannot connect to InfluxDB at {host}:{port} ({exc.__class__.__name__}: {exc}). "
                "Start the server/container before running 'aico influx init'."
            )
        )
        raise typer.Exit(code=1)

    # Check if InfluxDB is already set up by querying /api/v2/setup
    try:
        setup_url = url.rstrip("/") + "/api/v2/setup"
        resp = requests.get(setup_url, timeout=3.0)
        if resp.status_code == 200:
            setup_data = resp.json()
            already_setup = not setup_data.get("allowed", True)
        else:
            already_setup = False
    except Exception:
        already_setup = False

    if not already_setup:
        console.print("🔧 [cyan]Running initial InfluxDB setup...[/cyan]")
        # Perform initial setup via docker exec influx setup
        cmd = [
            "docker", "exec", "-i", "aico-influxdb",
            "influx", "setup",
            "--org", org,
            "--bucket", bucket,
            "--username", "aico-admin",
            "--password", admin_password,
            "--token", admin_token,
            "--force"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                console.print(
                    format_error(
                        f"Failed to run influx setup (exit code {result.returncode}).\n"
                        f"STDERR: {result.stderr}"
                    )
                )
                raise typer.Exit(code=1)

            console.print(format_success(f"✅ InfluxDB setup complete: org '{org}', bucket '{bucket}' created."))
            if result.stdout.strip():
                console.print(f"[dim]influx setup output:[/dim]\n{result.stdout}")

        except FileNotFoundError:
            console.print(
                format_error(
                    "'docker' command not found. Install Docker and ensure it is on your PATH."
                )
            )
            raise typer.Exit(code=1)
        except Exception as exc:
            console.print(
                format_error(f"Unexpected error during InfluxDB setup: {exc}")
            )
            raise typer.Exit(code=1)
    else:
        console.print(
            format_warning(
                f"ℹ️  InfluxDB already set up. Org '{org}' and bucket '{bucket}' should exist."
            )
        )

    # Retention policy is now set automatically via DOCKER_INFLUXDB_INIT_RETENTION
    # in docker-compose.local.yml (720h = 30 days)

    # Final instructions
    console.print(
        "\n[bold green]✅ InfluxDB initialization complete![/bold green]\n"
        f"Org: [cyan]{org}[/cyan]\n"
        f"Bucket: [cyan]{bucket}[/cyan]\n"
        f"Token: [yellow](use the token you provided)[/yellow]\n\n"
        "[blue]Next steps:[/blue]\n"
        "1. Store the token securely: [bold]uv run aico security influx-set[/bold]\n"
        "2. Export it for runtime: [bold]eval \"$(uv run aico security influx-env --include-secrets --format env)\"[/bold]\n"
        "3. Verify with: [bold]uv run aico influx doctor[/bold]"
    )


@app.command(help="Start the InfluxDB container using docker-compose.local.yml")
def start():
    """Start the local InfluxDB container (docker compose)."""

    console.print("🚀 [cyan]Starting InfluxDB container (docker compose)...[/cyan]")
    code = _run_compose(["up", "-d", "influxdb"])
    if code != 0:
        raise typer.Exit(code)
    console.print(format_success("InfluxDB container started (if Docker is available)."))


@app.command(help="Stop the InfluxDB container using docker-compose.local.yml")
def stop():
    """Stop the local InfluxDB container (docker compose)."""

    console.print("🛑 [cyan]Stopping InfluxDB container (docker compose)...[/cyan]")
    code = _run_compose(["stop", "influxdb"])
    if code != 0:
        raise typer.Exit(code)
    console.print(format_success("InfluxDB container stopped (if it was running)."))
