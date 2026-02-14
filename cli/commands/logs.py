"""
AICO Logs Command - Query logs from InfluxDB

Provides commands to view and filter logs stored in InfluxDB.
"""

import sys
import warnings
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime, timedelta
from typing import Optional

# Suppress InfluxDB client cleanup warnings
warnings.filterwarnings("ignore", message=".*ApiClient.__del__.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

# Add shared path for imports
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.security import AICOKeyManager

# Monkey patch InfluxDB ApiClient to suppress __del__ errors
try:
    from influxdb_client._sync.api_client import ApiClient
    _original_del = ApiClient.__del__
    def _patched_del(self):
        try:
            _original_del(self)
        except:
            pass  # Suppress all cleanup errors
    ApiClient.__del__ = _patched_del
except ImportError:
    pass  # InfluxDB client not installed yet

app = typer.Typer(
    help=(
        "📋 Log management and analysis (InfluxDB)\n\n"
        "Level filtering:\n"
        "- --level: minimum severity and above (e.g. --level=info shows INFO+WARNING+ERROR+CRITICAL)\n"
        "- --exact-level: exact match only (e.g. --exact-level=info shows INFO only)"
    )
)
console = Console()


@app.callback(invoke_without_command=True)
def _logs_main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


def _get_influx_client():
    """Get InfluxDB client with credentials."""
    try:
        from influxdb_client import InfluxDBClient
        
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        influx_url = config.get("influx.url", "http://127.0.0.1:8086")
        org = config.get("influx.org", "aico")
        bucket = config.get("influx.bucket", "aico_telemetry")
        
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token")
        
        if not token:
            console.print("[red]✗ InfluxDB token not found. Run 'aico security influx-set' first.[/red]")
            raise typer.Exit(1)
        
        client = InfluxDBClient(url=influx_url, token=token, org=org)
        return client, org, bucket
        
    except ImportError:
        console.print("[red]✗ influxdb-client not installed. Run: pip install influxdb-client[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to connect to InfluxDB: {e}[/red]")
        raise typer.Exit(1)


@app.command("tail")
def tail_logs(
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Filter by service (backend, modelservice, cli, shared)"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by minimum level and above (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    exact_level: Optional[str] = typer.Option(None, "--exact-level", help="Filter by exact level only (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    logger: Optional[str] = typer.Option(None, "--logger", help="Filter by logger name"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    last: str = typer.Option("48h", "--last", help="Time range to search (e.g., 1h, 30m, 2d)"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (not implemented yet)")
):
    """Show the most recent N log entries (like tail -n)."""
    
    if follow:
        console.print("[yellow]⚠ Follow mode not yet implemented[/yellow]")
        return
    
    if level and exact_level:
        console.print("[yellow]⚠ Use either --level or --exact-level (not both)[/yellow]")
        return
    
    client, org, bucket = _get_influx_client()
    
    # Log level hierarchy (lower index = lower severity)
    level_hierarchy = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Build Flux query
    filters = [
        f'r._measurement == "logs"',
        # We store message/logger/module/function as FIELDS (not tags).
        # Influx returns one row per field, so we must pivot to reconstruct
        # the full log entry for display.
        (
            '('
            'r._field == "message" or '
            'r._field == "logger" or '
            'r._field == "module" or '
            'r._field == "function"'
            ')'
        )
    ]
    
    if service:
        filters.append(f'r.service == "{service}"')
    if level:
        level_upper = level.upper()
        if level_upper in level_hierarchy:
            min_index = level_hierarchy.index(level_upper)
            allowed_levels = level_hierarchy[min_index:]
            level_filter = " or ".join([f'r.level == "{lvl}"' for lvl in allowed_levels])
            filters.append(f'({level_filter})')
        else:
            console.print(f"[yellow]⚠ Invalid level '{level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    if exact_level:
        exact_level_upper = exact_level.upper()
        if exact_level_upper in level_hierarchy:
            filters.append(f'r.level == "{exact_level_upper}"')
        else:
            console.print(f"[yellow]⚠ Invalid exact level '{exact_level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    if logger:
        filters.append(f'r.logger =~ /{logger}/')
    
    filter_str = " and ".join(filters)
    
    # Tail shows the most recent N lines.
    # Keep this query efficient: apply a global limit server-side.
    # In Flux, limit() applies per-table, so we group() first to get a single table.
    # Then we pivot fields into columns so we can display logger/module/function.
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{last})
      |> filter(fn: (r) => {filter_str})
      |> group(columns: ["_time", "service", "level"])
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> group()
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {lines})
    '''
    
    try:
        query_api = client.query_api()
        tables = query_api.query(query, org=org)
        
        if not tables:
            console.print("[yellow]No logs found matching criteria[/yellow]")
            return
        
        # Collect all records from all tables
        all_records = []
        for table in tables:
            all_records.extend(table.records)

        if not all_records:
            console.print("[yellow]No logs found matching criteria[/yellow]")
            return

        # Re-sort for display (oldest to newest)
        all_records.sort(key=lambda r: r.get_time())
        
        # Display logs
        for record in all_records:
                # Convert UTC timestamp to local time for display
                utc_time = record.get_time()
                local_time = utc_time.replace(tzinfo=None) if utc_time.tzinfo is None else utc_time.astimezone()
                timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")
                level = record.values.get("level", "INFO")
                service_name = record.values.get("service", "unknown")
                logger_name = record.values.get("logger") or "unknown"
                message = record.values.get("message") or ""
                module = record.values.get("module")
                function = record.values.get("function")

                display_logger_name = logger_name
                try:
                    if (
                        isinstance(service_name, str)
                        and isinstance(logger_name, str)
                        and logger_name.startswith(f"{service_name}.")
                    ):
                        display_logger_name = logger_name[len(service_name) + 1 :]
                except Exception:
                    display_logger_name = logger_name
                
                # Color by level
                level_colors = {
                    "DEBUG": "dim",
                    "INFO": "blue",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold red"
                }
                color = level_colors.get(level, "white")
                
                suffix = ""
                if module and function:
                    suffix = f" ({module}.{function})"
                console.print(
                    f"[dim]{timestamp}[/dim] [{color}]{level:8}[/{color}] [cyan]{service_name}[/cyan].[dim]{display_logger_name}[/dim] - {message}{suffix}"
                )
        
    except Exception as e:
        console.print(f"[red]✗ Query failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("ls")
def list_logs(
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Filter by service"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by minimum level and above (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    exact_level: Optional[str] = typer.Option(None, "--exact-level", help="Filter by exact level only (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    last: str = typer.Option("1h", "--last", help="Time range (e.g., 1h, 30m, 1d)"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of logs")
):
    """List logs with filtering options."""
    
    client, org, bucket = _get_influx_client()
    
    # Log level hierarchy (lower index = lower severity)
    level_hierarchy = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Build Flux query
    filters = [
        f'r._measurement == "logs"',
        f'r._field == "message"'
    ]

    if level and exact_level:
        console.print("[yellow]⚠ Use either --level or --exact-level (not both)[/yellow]")
        return
    
    if service:
        filters.append(f'r.service == "{service}"')

    if level:
        level_upper = level.upper()
        if level_upper in level_hierarchy:
            min_index = level_hierarchy.index(level_upper)
            allowed_levels = level_hierarchy[min_index:]
            level_filter = " or ".join([f'r.level == "{lvl}"' for lvl in allowed_levels])
            filters.append(f'({level_filter})')
        else:
            console.print(f"[yellow]⚠ Invalid level '{level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return

    if exact_level:
        exact_level_upper = exact_level.upper()
        if exact_level_upper in level_hierarchy:
            filters.append(f'r.level == "{exact_level_upper}"')
        else:
            console.print(f"[yellow]⚠ Invalid exact level '{exact_level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    
    filter_str = " and ".join(filters)
    
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{last})
      |> filter(fn: (r) => {filter_str})
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    '''
    
    try:
        query_api = client.query_api()
        tables = query_api.query(query, org=org)
        
        if not tables or not tables[0].records:
            console.print("[yellow]No logs found[/yellow]")
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim")
        table.add_column("Level", style="bold")
        table.add_column("Service", style="cyan")
        table.add_column("Logger", style="dim")
        table.add_column("Message")

        all_records = []
        
        for flux_table in tables:
            for record in reversed(flux_table.records):
                timestamp = record.get_time().strftime("%H:%M:%S")
                level = record.values.get("level", "INFO")
                service_name = record.values.get("service", "unknown")
                logger_name = record.values.get("logger", "unknown")
                message = record.get_value()

                display_logger_name = logger_name
                try:
                    if (
                        isinstance(service_name, str)
                        and isinstance(logger_name, str)
                        and logger_name.startswith(f"{service_name}.")
                    ):
                        display_logger_name = logger_name[len(service_name) + 1 :]
                except Exception:
                    display_logger_name = logger_name
                
                # Truncate message if too long
                if len(message) > 80:
                    message = message[:77] + "..."
                
                table.add_row(timestamp, level, service_name, display_logger_name, message)
                all_records.append(record)
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(all_records)} logs from last {last}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Query failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("stats")
def log_stats(
    last: str = typer.Option("1h", "--last", help="Time range (e.g., 1h, 30m, 1d)")
):
    """Show log statistics."""
    
    client, org, bucket = _get_influx_client()
    
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{last})
      |> filter(fn: (r) => r._measurement == "logs" and r._field == "count")
      |> group(columns: ["service", "level"])
      |> count()
    '''
    
    try:
        query_api = client.query_api()
        tables = query_api.query(query, org=org)
        
        if not tables:
            console.print("[yellow]No logs found[/yellow]")
            return
        
        # Create stats table
        stats_table = Table(show_header=True, header_style="bold magenta")
        stats_table.add_column("Service", style="cyan")
        stats_table.add_column("Level", style="bold")
        stats_table.add_column("Count", justify="right")
        
        for table in tables:
            for record in table.records:
                service = record.values.get("service", "unknown")
                level = record.values.get("level", "unknown")
                count = record.get_value()
                
                stats_table.add_row(service, level, str(count))
        
        console.print(stats_table)
        console.print(f"\n[dim]Statistics for last {last}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Query failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    app()
