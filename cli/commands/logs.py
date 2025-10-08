"""
AICO Logs Management Commands

Unix-style commands for managing logs in the unified logging system.
Follows the CLI visual style guide with modern, minimal, clean aesthetics.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive

# Import utils
utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_path))
from cli.utils.timezone import format_timestamp_local, get_timezone_suffix

# Add shared path for imports
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.logging import LogRepository, initialize_logging
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security.key_manager import AICOKeyManager

console = Console()

def logs_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("ls", "List recent logs with filtering options"),
            ("cat", "Display full log entry details"),
            ("rm", "Remove log entries based on criteria"),
            ("stat", "Show logging statistics and summary"),
            ("tail", "Show recent logs (like tail -f)"),
            ("grep", "Search logs by pattern/content"),
            ("export", "Export logs to file")
        ]
        
        examples = [
            "aico logs ls --limit=50",
            "aico logs cat --id=123",
            "aico logs grep 'error'",
            "aico logs tail --follow",
            "aico logs stat"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="logs",
            description="Manage AICO logs with Unix-style commands",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Manage AICO logs with Unix-style commands.",
    callback=logs_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


def _get_log_repository() -> LogRepository:
    """Get configured log repository"""
    try:
        config_manager = ConfigurationManager()
        key_manager = AICOKeyManager(config_manager)
        
        # Get database path and connection
        from aico.core.paths import AICOPaths
        paths = AICOPaths()
        db_path = paths.resolve_database_path("aico.db")
        
        # Get encryption key using session-based authentication
        if not key_manager.has_stored_key():
            console.print("[red]Error: Master key not found. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
            
        # Authenticate using session cache (will prompt only if session expired)
        master_key = key_manager.authenticate(interactive=True)
        db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        
        # Connect to database
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        return LogRepository(conn)
        
    except Exception as e:
        console.print(f"[red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)

def _get_log_repository_no_auth() -> LogRepository:
    """Get configured log repository without authentication (assumes already authenticated)"""
    try:
        config_manager = ConfigurationManager()
        key_manager = AICOKeyManager(config_manager)
        
        # Get database path and connection
        from aico.core.paths import AICOPaths
        paths = AICOPaths()
        db_path = paths.resolve_database_path("aico.db")
        
        # Get encryption key from session cache (no prompting)
        if not key_manager.has_stored_key():
            console.print("[red]Error: Master key not found. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
            
        # Get cached session key (decorator should have already authenticated)
        cached_key = key_manager._get_cached_session()
        if not cached_key:
            # Fallback to stored key
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                cached_key = bytes.fromhex(stored_key)
            else:
                console.print("[red]Error: No authenticated session found[/red]")
                raise typer.Exit(1)
        
        db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        
        # Connect to database
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        return LogRepository(conn)
        
    except Exception as e:
        console.print(f"[red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="List recent logs with filtering options")
def ls(
    limit: int = typer.Option(100, "--limit", "-n", help="Number of logs to show"),
    level: Optional[str] = typer.Option(None, "--level", help="Filter by log level"),
    subsystem: Optional[str] = typer.Option(None, "--subsystem", help="Filter by subsystem"),
    module: Optional[str] = typer.Option(None, "--module", help="Filter by module"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since timestamp"),
    last: Optional[str] = typer.Option(None, "--last", help="Show logs from last period (e.g., 1h, 30m, 7d)"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, oneline"),
    oneline: bool = typer.Option(False, "--oneline", help="Compact one-line format"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """List recent logs with filtering options"""
    
    repo = _get_log_repository()
    
    # Build filters (exclude level - we'll filter after retrieval to show level and UP)
    filters = {}
    if subsystem:
        filters["subsystem"] = subsystem
    if module:
        filters["module"] = module
    if since:
        filters["since"] = since
    if last:
        # Convert relative time to timestamp
        if last.endswith('h'):
            hours = int(last[:-1])
            since_time = datetime.utcnow() - timedelta(hours=hours)
        elif last.endswith('d'):
            days = int(last[:-1])
            since_time = datetime.utcnow() - timedelta(days=days)
        else:
            console.print(f"[red]Invalid time format: {last}. Use format like '24h' or '7d'[/red]")
            raise typer.Exit(1)
        filters["since"] = since_time.isoformat() + "Z"
    
    # Get logs
    logs = repo.get_logs(limit=limit, **filters)
    
    # Apply level filtering (show specified level and UP)
    from aico.core.config import ConfigurationManager
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Determine which level to filter by
    filter_level = level.upper() if level else config_manager.get("logging.levels.default", "INFO")
    
    # Level hierarchy for filtering
    level_hierarchy = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
    filter_level_value = level_hierarchy.get(filter_level, 20)
    
    # Filter logs to show specified level and UP
    logs = [log for log in logs if level_hierarchy.get(log['level'], 20) >= filter_level_value]
    
    if not logs:
        console.print("[yellow]No logs found matching criteria[/yellow]")
        return
    
    # Format output
    if format == "json":
        console.print(json.dumps(logs, indent=2, default=str))
    elif format == "oneline" or oneline:
        for log in reversed(logs):  # Unix style: latest entries at bottom
            console.print(f"[dim]{format_timestamp_local(log['timestamp'], show_utc=utc)}[/dim] "
                         f"[bold {_get_level_color(log['level'])}]{log['level']}[/bold {_get_level_color(log['level'])}] "
                         f"[cyan]{log['subsystem']}.{log['module']}[/cyan] {log['message']}")
    else:
        # Table format (default)
        table = Table(
            title="✨ [bold cyan]Recent Logs[/bold cyan]",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        # Dynamic column header based on timezone preference
        time_header = f"Time{get_timezone_suffix(utc)}"
        table.add_column(time_header, style="dim")
        table.add_column("Level", style="bold")
        table.add_column("Source", style="cyan")
        table.add_column("Message", style="white")
        
        for log in reversed(logs):  # Unix style: latest entries at bottom
            # Truncate message for table display
            message = log['message']
            if len(message) > 60:
                message = message[:57] + "..."
                
            table.add_row(
                format_timestamp_local(log['timestamp'], show_utc=utc),
                f"[{_get_level_color(log['level'])}]{log['level']}[/{_get_level_color(log['level'])}]",
                f"{log['subsystem']}.{log['module']}",
                message
            )
        
        console.print()
        console.print(table)
        console.print()


@app.command(help="Display full log entry details")
def cat(
    id: Optional[int] = typer.Option(None, "--id", help="Show specific log by ID"),
    trace_id: Optional[str] = typer.Option(None, "--trace-id", help="Show logs by trace ID"),
    level: Optional[str] = typer.Option(None, "--level", help="Filter by log level"),
    last: Optional[str] = typer.Option(None, "--last", help="Show logs from last period"),
    format: str = typer.Option("pretty", "--format", help="Output format: pretty, json"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Display full log entry details"""
    
    repo = _get_log_repository()
    
    # Build filters
    filters = {}
    if id:
        # Get specific log by ID
        logs = [repo.db.execute("SELECT * FROM logs WHERE id = ?", [id]).fetchone()]
        if not logs[0]:
            console.print(f"[red]Log with ID {id} not found[/red]")
            raise typer.Exit(1)
    else:
        if level:
            filters["level"] = level.upper()
        if trace_id:
            filters["trace_id"] = trace_id
        if last:
            # Convert relative time
            if last.endswith('h'):
                hours = int(last[:-1])
                since_time = datetime.utcnow() - timedelta(hours=hours)
            elif last.endswith('d'):
                days = int(last[:-1])
                since_time = datetime.utcnow() - timedelta(days=days)
            else:
                console.print(f"[red]Invalid time format: {last}[/red]")
                raise typer.Exit(1)
            filters["since"] = since_time.isoformat() + "Z"
        
        logs = repo.get_logs(limit=50, **filters)
    
    if not logs:
        console.print("[yellow]No logs found matching criteria[/yellow]")
        return
    
    # Display logs (newest first - closest to user)
    for i, log in enumerate(reversed(logs)):
        if format == "json":
            console.print(json.dumps(dict(log), indent=2, default=str))
        else:
            # Pretty format
            panel_title = f"Log #{log['id']} - {log['level']} - {log['subsystem']}.{log['module']}"
            
            content = []
            content.append(f"[bold yellow]Timestamp:[/bold yellow] {format_timestamp_local(log['timestamp'], show_utc=utc)}")
            content.append(f"[bold yellow]Level:[/bold yellow] [{_get_level_color(log['level'])}]{log['level']}[/{_get_level_color(log['level'])}]")
            content.append(f"[bold yellow]Source:[/bold yellow] [cyan]{log['subsystem']}.{log['module']}[/cyan]")
            
            if log['function_name']:
                content.append(f"[bold yellow]Function:[/bold yellow] {log['function_name']}")
            if log['file_path'] and log['line_number']:
                content.append(f"[bold yellow]Location:[/bold yellow] {log['file_path']}:{log['line_number']}")
            if log['topic']:
                content.append(f"[bold yellow]Topic:[/bold yellow] {log['topic']}")
            if log['trace_id']:
                content.append(f"[bold yellow]Trace ID:[/bold yellow] {log['trace_id']}")
            if log['session_id']:
                content.append(f"[bold yellow]Session:[/bold yellow] {log['session_id']}")
                
            content.append("")
            content.append(f"[bold yellow]Message:[/bold yellow]")
            content.append(f"[white]{log['message']}[/white]")
            
            if log['extra']:
                content.append("")
                content.append(f"[bold yellow]Extra Data:[/bold yellow]")
                try:
                    extra_data = json.loads(log['extra']) if isinstance(log['extra'], str) else log['extra']
                    content.append(json.dumps(extra_data, indent=2))
                except:
                    content.append(str(log['extra']))
            
            panel = Panel(
                "\n".join(content),
                title=f"[bold cyan]{panel_title}[/bold cyan]",
                border_style="bright_blue",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            
            console.print()
            console.print(panel)
            
            if i < len(logs) - 1:  # Add separator between logs
                console.print()


@app.command(help="Remove log entries based on criteria")
@sensitive
def rm(
    before: Optional[str] = typer.Option(None, "--before", help="Delete logs before date"),
    older_than: Optional[str] = typer.Option(None, "--older-than", help="Delete logs older than period (e.g., 7d)"),
    level: Optional[str] = typer.Option(None, "--level", help="Delete logs of specific level"),
    subsystem: Optional[str] = typer.Option(None, "--subsystem", help="Delete logs from subsystem"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Remove log entries based on criteria"""
    
    repo = _get_log_repository()
    
    # Build criteria
    criteria = {}
    if before:
        criteria["before"] = before
    if older_than:
        if older_than.endswith('d'):
            days = int(older_than[:-1])
            cutoff = datetime.utcnow() - timedelta(days=days)
            criteria["before"] = cutoff.isoformat() + "Z"
        elif older_than.endswith('h'):
            hours = int(older_than[:-1])
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            criteria["before"] = cutoff.isoformat() + "Z"
        else:
            console.print(f"[red]Invalid time format: {older_than}[/red]")
            raise typer.Exit(1)
    if level:
        criteria["level"] = level.upper()
    if subsystem:
        criteria["subsystem"] = subsystem
    
    if not criteria:
        console.print("[red]Error: Must specify deletion criteria[/red]")
        console.print("Use --before, --older-than, --level, or --subsystem")
        raise typer.Exit(1)
    
    # Safety confirmation
    if not confirm:
        criteria_str = ", ".join(f"{k}={v}" for k, v in criteria.items())
        if not typer.confirm(f"Delete logs matching: {criteria_str}?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Delete logs
    try:
        deleted_count = repo.delete_logs(**criteria)
        console.print(f"[green]✓ Deleted {deleted_count} log entries[/green]")
    except Exception as e:
        console.print(f"[red]Error deleting logs: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Show logging statistics and summary")
def stat():
    """Show logging statistics and summary"""
    
    repo = _get_log_repository()
    stats = repo.get_log_stats()
    
    # Create statistics panel
    content = []
    content.append(f"[bold yellow]Total Logs:[/bold yellow] [bold white]{stats['total_logs']:,}[/bold white]")
    content.append(f"[bold yellow]Last 24h:[/bold yellow] [bold white]{stats['last_24h']:,}[/bold white]")
    content.append("")
    
    # By level
    content.append("[bold yellow]By Level:[/bold yellow]")
    for level, count in stats['by_level'].items():
        color = _get_level_color(level)
        content.append(f"  [{color}]{level}[/{color}]: [bold white]{count:,}[/bold white]")
    
    content.append("")
    
    # By subsystem
    content.append("[bold yellow]By Subsystem:[/bold yellow]")
    for subsystem, count in stats['by_subsystem'].items():
        content.append(f"  [cyan]{subsystem}[/cyan]: [bold white]{count:,}[/bold white]")
    
    panel = Panel(
        "\n".join(content),
        title="✨ [bold cyan]Log Statistics[/bold cyan]",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()


@app.command(help="Show recent logs (like tail -f)")
def tail(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output in real-time"),
    level: Optional[str] = typer.Option(None, "--level", help="Filter by log level"),
    subsystem: Optional[str] = typer.Option(None, "--subsystem", help="Filter by subsystem"),
    lines: int = typer.Option(20, "--lines", "-n", help="Number of lines to show"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Number of entries to show (alias for --lines)"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Show recent logs (like tail -f)"""
    
    repo = _get_log_repository()
    
    # Determine number of entries to show (--limit takes precedence over --lines)
    num_entries = limit if limit is not None else lines
    
    # Build filters (exclude level - we'll filter after retrieval to show level and UP)
    filters = {}
    if subsystem:
        filters["subsystem"] = subsystem
    
    # Get recent logs
    logs = repo.get_logs(limit=num_entries, **filters)
    
    # Apply level filtering (show specified level and UP)
    from aico.core.config import ConfigurationManager
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Determine which level to filter by
    filter_level = level.upper() if level else config_manager.get("logging.levels.default", "INFO")
    
    # Level hierarchy for filtering
    level_hierarchy = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
    filter_level_value = level_hierarchy.get(filter_level, 20)
    
    # Filter logs to show specified level and UP
    logs = [log for log in logs if level_hierarchy.get(log['level'], 20) >= filter_level_value]
    
    # Display logs
    for log in reversed(logs):  # Show oldest first
        level_color = _get_level_color(log['level'])
        
        # Main log line
        console.print(f"[dim]{format_timestamp_local(log['timestamp'], show_utc=utc)}[/dim] "
                     f"[bold {level_color}]{log['level']}[/bold {level_color}] "
                     f"[cyan]{log['subsystem']}.{log['module']}[/cyan] {log['message']}")
        
        # Show all extra data with beautiful tree-style formatting
        if log['extra']:
            try:
                extra_data = json.loads(log['extra']) if isinstance(log['extra'], str) else log['extra']
                if isinstance(extra_data, dict) and extra_data:
                    # Get list of items for proper tree formatting
                    items = list(extra_data.items())
                    for i, (key, value) in enumerate(items):
                        # Use proper tree characters for last item
                        if i == len(items) - 1:
                            tree_char = "└─"
                        else:
                            tree_char = "├─"
                        
                        # Format with proper spacing and colors
                        console.print(f"    [dim]{tree_char}[/dim] [yellow]{key}[/yellow]: [bright_green]{value}[/bright_green]")
            except:
                # Fallback for non-JSON extra data - show full content
                console.print(f"    [dim]└─[/dim] [yellow]extra[/yellow]: [bright_green]{log['extra']}[/bright_green]")
    
    if follow:
        console.print("[yellow]Real-time following not implemented yet[/yellow]")
        # TODO: Implement real-time following via ZeroMQ subscription


@app.command(help="Search logs by pattern/content")
def grep(
    pattern: str = typer.Argument(..., help="Search pattern"),
    level: Optional[str] = typer.Option(None, "--level", help="Filter by log level"),
    subsystem: Optional[str] = typer.Option(None, "--subsystem", help="Filter by subsystem"),
    limit: int = typer.Option(100, "--limit", help="Maximum results to show"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Search logs by pattern/content"""
    
    repo = _get_log_repository()
    
    # Build base filters (exclude level - we'll filter after retrieval to show level and UP)
    filters = {}
    if subsystem:
        filters["subsystem"] = subsystem
    
    # Get logs and filter by pattern
    all_logs = repo.get_logs(limit=limit * 2, **filters)  # Get more to account for filtering
    
    # Apply level filtering (show specified level and UP)
    from aico.core.config import ConfigurationManager
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Determine which level to filter by
    filter_level = level.upper() if level else config_manager.get("logging.levels.default", "INFO")
    
    # Level hierarchy for filtering
    level_hierarchy = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
    filter_level_value = level_hierarchy.get(filter_level, 20)
    
    # Filter logs to show specified level and UP
    all_logs = [log for log in all_logs if level_hierarchy.get(log['level'], 20) >= filter_level_value]
    matching_logs = []
    pattern_lower = pattern.lower()
    
    for log in all_logs:
        # Search across multiple fields
        searchable_text = " ".join([
            str(log.get('message', '')),
            str(log.get('level', '')),
            str(log.get('subsystem', '')),
            str(log.get('module', '')),
            str(log.get('function', '')),
            str(log.get('topic', ''))
        ]).lower()
        
        if pattern_lower in searchable_text:
            matching_logs.append(log)
            if len(matching_logs) >= limit:
                break
    
    if not matching_logs:
        console.print(f"[yellow]No logs found matching pattern: '{pattern}'[/yellow]")
        return
    
    # Display matching logs
    console.print(f"\n[bold cyan]Found {len(matching_logs)} logs matching '{pattern}':[/bold cyan]\n")
    
    for log in matching_logs:
        level_color = _get_level_color(log['level'])
        
        # Highlight the pattern in the message
        message = log['message']
        highlighted_message = message.replace(
            pattern, f"[bold yellow on red]{pattern}[/bold yellow on red]"
        )
        
        console.print(f"[dim]{format_timestamp_local(log['timestamp'], show_utc=utc)}[/dim] "
                     f"[bold {level_color}]{log['level']}[/bold {level_color}] "
                     f"[cyan]{log['subsystem']}.{log['module']}[/cyan] {highlighted_message}")


@app.command()
@sensitive("exports potentially sensitive log data to external files")
def export(
    output: str = typer.Option("logs_export.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", help="Export format: json, csv"),
    last: Optional[str] = typer.Option(None, "--last", help="Export logs from last period"),
    level: Optional[str] = typer.Option(None, "--level", help="Filter by log level"),
    subsystem: Optional[str] = typer.Option(None, "--subsystem", help="Filter by subsystem")
):
    """Export logs to file"""
    
    try:
        repo = _get_log_repository()
        
        # Build filters
        filters = {}
        if level:
            filters["level"] = level.upper()
        if subsystem:
            filters["subsystem"] = subsystem
        if last:
            if last.endswith('d'):
                days = int(last[:-1])
                since_time = datetime.utcnow() - timedelta(days=days)
                filters["since"] = since_time.isoformat() + "Z"
        
        # Get logs
        logs = repo.get_logs(limit=10000, **filters)  # Large limit for export
        
        if not logs:
            console.print("[yellow]No logs found to export[/yellow]")
            return
        
        # Export
        output_path = Path(output)
        
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, default=str)
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if logs:
                    writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)
        
        console.print(f"[green]✓ Exported {len(logs)} logs to {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error exporting logs: {e}[/red]")
        raise typer.Exit(1)





def _get_level_color(level: str) -> str:
    """Get Rich color for log level"""
    colors = {
        "DEBUG": "bright_black",
        "INFO": "bright_blue", 
        "WARNING": "yellow",
        "ERROR": "red"
    }
    return colors.get(level, "white")


if __name__ == "__main__":
    app()
