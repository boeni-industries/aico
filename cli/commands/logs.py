"""
AICO Logs Command - Query logs from Loki

Provides commands to view and filter logs stored in Loki.
"""

import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime, timedelta
from typing import Optional

# Add shared path for imports
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# Lazy imports - don't load heavy modules at import time
# ConfigurationManager imported in functions

app = typer.Typer(
    help=(
        "📋 Log management and analysis (Loki)\n\n"
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


def _get_loki_url():
    """Get Loki URL from config (lazy imports for fast startup)."""
    try:
        from aico.core.config import ConfigurationManager
        
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        loki_url = config.get("loki.url", "http://127.0.0.1:3100")
        return loki_url
        
    except Exception as e:
        console.print(f"[red]✗ Failed to get Loki config: {e}[/red]")
        raise typer.Exit(1)


def _query_loki(loki_url: str, query: str, limit: int, start: str):
    """Query Loki API with LogQL."""
    import requests
    import json
    from datetime import datetime, timedelta
    
    # Query Loki using instant query for recent logs
    # Loki expects time in RFC3339 format or Unix timestamp in seconds
    url = f"{loki_url}/loki/api/v1/query_range"
    
    # Calculate start and end times
    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = start[-1]
    value = int(start[:-1])
    
    if unit not in time_units:
        raise ValueError(f"Invalid time unit: {unit}")
    
    seconds_ago = value * time_units[unit]
    start_time = datetime.now() - timedelta(seconds=seconds_ago)
    end_time = datetime.now()
    
    # Loki expects Unix timestamps in seconds (not nanoseconds)
    params = {
        "query": query,
        "limit": limit,
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp()),
        "direction": "backward"  # Most recent first
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]✗ Loki query failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("tail")
def tail_logs(
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Filter by service (backend, modelservice, cli, shared)"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by minimum level and above (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    exact_level: Optional[str] = typer.Option(None, "--exact-level", help="Filter by exact level only (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    logger: Optional[str] = typer.Option(None, "--logger", help="Filter by logger name"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    last: str = typer.Option("1h", "--last", help="Time range to search (e.g., 1h, 30m, 2d)"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (not implemented yet)")
):
    """Show the most recent N log entries (like tail -n)."""
    
    if follow:
        console.print("[yellow]⚠ Follow mode not yet implemented[/yellow]")
        return
    
    if level and exact_level:
        console.print("[yellow]⚠ Use either --level or --exact-level (not both)[/yellow]")
        return
    
    loki_url = _get_loki_url()
    
    # Log level hierarchy (lower index = lower severity)
    level_hierarchy = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Build LogQL query - uses labels for filtering
    label_filters = []
    
    if service:
        label_filters.append(f'service="{service}"')
    
    if level:
        level_upper = level.upper()
        if level_upper in level_hierarchy:
            min_index = level_hierarchy.index(level_upper)
            allowed_levels = level_hierarchy[min_index:]
            level_filter = "|".join(allowed_levels)
            label_filters.append(f'level=~"{level_filter}"')
        else:
            console.print(f"[yellow]⚠ Invalid level '{level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    
    if exact_level:
        exact_level_upper = exact_level.upper()
        if exact_level_upper in level_hierarchy:
            label_filters.append(f'level="{exact_level_upper}"')
        else:
            console.print(f"[yellow]⚠ Invalid exact level '{exact_level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    
    if logger:
        # Use logger_prefix label for filtering
        label_filters.append(f'logger_prefix=~".*{logger}.*"')
    
    # Build LogQL query
    # Loki requires at least one label matcher, so if no filters, match all services
    if label_filters:
        query = "{" + ", ".join(label_filters) + "}"
    else:
        query = '{job=~".+"}'  # Match all jobs (all logs)
    
    try:
        result = _query_loki(loki_url, query, lines, last)
        
        if result.get("status") != "success":
            console.print("[yellow]No logs found matching criteria[/yellow]")
            return
        
        data = result.get("data", {})
        result_type = data.get("resultType")
        streams = data.get("result", [])
        
        if not streams:
            console.print("[yellow]No logs found matching criteria[/yellow]")
            return
        
        # Collect all log entries
        all_logs = []
        for stream in streams:
            labels = stream.get("stream", {})
            values = stream.get("values", [])
            
            for value in values:
                timestamp_ns = int(value[0])
                log_line = value[1]
                
                # Parse metadata from log line (format: message | {json_metadata})
                message = log_line
                metadata = {}
                if " | " in log_line:
                    parts = log_line.split(" | ", 1)
                    message = parts[0]
                    if len(parts) > 1:
                        try:
                            import json
                            metadata = json.loads(parts[1])
                        except:
                            pass
                
                all_logs.append({
                    "timestamp": timestamp_ns,
                    "level": labels.get("level", "INFO"),
                    "service": labels.get("service", "unknown"),
                    "logger_prefix": labels.get("logger_prefix", "unknown"),
                    "message": message,
                    "metadata": metadata
                })
        
        # Sort by timestamp (oldest to newest for display)
        all_logs.sort(key=lambda x: x["timestamp"])
        
        # Display logs
        for log in all_logs:
            # Convert nanosecond timestamp to datetime
            timestamp_s = log["timestamp"] / 1_000_000_000
            dt = datetime.fromtimestamp(timestamp_s)
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            level = log["level"]
            service_name = log["service"]
            logger_prefix = log["logger_prefix"]
            message = log["message"]
            
            # Color by level
            level_colors = {
                "DEBUG": "dim",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold red"
            }
            color = level_colors.get(level, "white")
            
            console.print(
                f"[dim]{timestamp}[/dim] [{color}]{level:8}[/{color}] [cyan]{service_name}[/cyan].[dim]{logger_prefix}[/dim] - {message}"
            )
        
    except Exception as e:
        console.print(f"[red]✗ Query failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("ls")
def list_logs(
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Filter by service"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by minimum level and above (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    exact_level: Optional[str] = typer.Option(None, "--exact-level", help="Filter by exact level only (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    last: str = typer.Option("1h", "--last", help="Time range (e.g., 1h, 30m, 1d)"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of logs")
):
    """List logs with filtering options."""
    
    loki_url = _get_loki_url()
    
    # Log level hierarchy (lower index = lower severity)
    level_hierarchy = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    if level and exact_level:
        console.print("[yellow]⚠ Use either --level or --exact-level (not both)[/yellow]")
        return
    
    # Build LogQL query
    label_filters = []
    
    if service:
        label_filters.append(f'service="{service}"')

    if level:
        level_upper = level.upper()
        if level_upper in level_hierarchy:
            min_index = level_hierarchy.index(level_upper)
            allowed_levels = level_hierarchy[min_index:]
            level_filter = "|".join(allowed_levels)
            label_filters.append(f'level=~"{level_filter}"')
        else:
            console.print(f"[yellow]⚠ Invalid level '{level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return

    if exact_level:
        exact_level_upper = exact_level.upper()
        if exact_level_upper in level_hierarchy:
            label_filters.append(f'level="{exact_level_upper}"')
        else:
            console.print(f"[yellow]⚠ Invalid exact level '{exact_level}'. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL[/yellow]")
            return
    
    # Build LogQL query
    # Loki requires at least one label matcher
    if label_filters:
        query = "{" + ", ".join(label_filters) + "}"
    else:
        query = '{job=~".+"}'  # Match all jobs (all logs)
    
    try:
        result = _query_loki(loki_url, query, limit, last)
        
        if result.get("status") != "success":
            console.print("[yellow]No logs found[/yellow]")
            return
        
        data = result.get("data", {})
        streams = data.get("result", [])
        
        if not streams:
            console.print("[yellow]No logs found[/yellow]")
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim")
        table.add_column("Level", style="bold")
        table.add_column("Service", style="cyan")
        table.add_column("Logger", style="dim")
        table.add_column("Message")

        # Collect all log entries
        all_logs = []
        for stream in streams:
            labels = stream.get("stream", {})
            values = stream.get("values", [])
            
            for value in values:
                timestamp_ns = int(value[0])
                log_line = value[1]
                
                # Parse metadata from log line
                message = log_line
                metadata = {}
                if " | " in log_line:
                    parts = log_line.split(" | ", 1)
                    message = parts[0]
                    if len(parts) > 1:
                        try:
                            import json
                            metadata = json.loads(parts[1])
                        except:
                            pass
                
                all_logs.append({
                    "timestamp": timestamp_ns,
                    "level": labels.get("level", "INFO"),
                    "service": labels.get("service", "unknown"),
                    "logger_prefix": labels.get("logger_prefix", "unknown"),
                    "logger": metadata.get("logger", labels.get("logger_prefix", "unknown")),
                    "message": message
                })
        
        # Sort by timestamp (oldest first)
        all_logs.sort(key=lambda x: x["timestamp"])
        
        # Display in table
        for log in all_logs:
            timestamp_s = log["timestamp"] / 1_000_000_000
            dt = datetime.fromtimestamp(timestamp_s)
            timestamp = dt.strftime("%H:%M:%S")
            
            level = log["level"]
            service_name = log["service"]
            logger_name = log["logger"]
            message = log["message"]
            
            # Simplify logger name
            display_logger_name = logger_name
            try:
                if isinstance(service_name, str) and isinstance(logger_name, str) and logger_name.startswith(f"{service_name}."):
                    display_logger_name = logger_name[len(service_name) + 1:]
            except:
                pass
            
            # Truncate message if too long
            if len(message) > 80:
                message = message[:77] + "..."
            
            table.add_row(timestamp, level, service_name, display_logger_name, message)
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(all_logs)} logs from last {last}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Query failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
