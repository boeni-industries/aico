"""AICO CLI InfluxDB Commands

Command group for managing and validating the external InfluxDB instance
used for telemetry/time-series data.

This assumes InfluxDB is installed and running (locally, remotely, or in a
container). The commands focus on configuration and connectivity checks,
not installation.
"""

import sys
import socket
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
        ]

        examples = [
            "aico influx status",
            "aico influx doctor",
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
        return config_manager.get("core.database.influx", {}) or {}
    except Exception:
        return {}


@app.command(help="Show InfluxDB configuration and basic reachability")
def status():
    """Show configured InfluxDB endpoint and perform a TCP reachability check."""

    cfg = _get_influx_config()

    table = Table(
        title="✨ [bold cyan]InfluxDB Backend Status[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("Property", style="cyan", justify="left")
    table.add_column("Value", style="green", justify="left")

    if not cfg:
        table.add_row(
            "Configuration",
            "[red]No core.database.influx configuration found in core.yaml[/red]",
        )
        console.print(table)
        return

    url = cfg.get("url", "http://127.0.0.1:8086")
    org = cfg.get("org", "aico")
    bucket = cfg.get("bucket", "aico_telemetry")

    table.add_row("URL", url)
    table.add_row("Org", org)
    table.add_row("Bucket", bucket)

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8086)

    try:
        with socket.create_connection((host, port), timeout=2.0):
            reachable = "[green]reachable (TCP connect OK)[/green]"
    except OSError as exc:  # pragma: no cover - best-effort diagnostic
        reachable = f"[red]unreachable ({exc.__class__.__name__}: {exc})[/red]"

    table.add_row("Network Reachability", reachable)

    console.print(table)


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
                "No core.database.influx configuration found in core.yaml. "
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
            else:
                table.add_row(
                    "HTTP /health",
                    "[red]FAILED[/red]",
                    f"{health_url} responded with HTTP {resp.status_code}",
                )
        except Exception as exc:  # pragma: no cover - best-effort diagnostic
            table.add_row(
                "HTTP /health",
                "[red]ERROR[/red]",
                f"Error calling {health_url}: {exc}",
            )
    else:
        table.add_row(
            "HTTP /health",
            "[yellow]SKIPPED[/yellow]",
            "Requires TCP connectivity first.",
        )

    console.print(table)

    console.print(
        "\n[blue]Next steps:[/blue] If TCP or HTTP checks failed, ensure your InfluxDB "
        "instance is running and reachable at the configured URL. Once these "
        "checks pass, you can enable instrumentation to start writing "
        "telemetry data to InfluxDB."
    )
