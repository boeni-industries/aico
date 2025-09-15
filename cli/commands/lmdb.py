"""
AICO CLI commands for managing the LMDB working memory database.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cli.utils.lmdb_utils import get_lmdb_status_cli, clear_lmdb_cli, list_named_databases, dump_lmdb_db, tail_lmdb_db
from cli.decorators.sensitive import destructive
from cli.utils.help_formatter import format_subcommand_help

def lmdb_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show the status and statistics of the LMDB database."),
            ("ls", "List all named sub-databases within the LMDB environment."),
            ("count", "Count the number of entries in a specific sub-database."),
            ("dump", "View the first N key-value pairs from a sub-database."),
            ("tail", "View the last N key-value pairs from a sub-database."),
            ("clear", "Clear all data from the LMDB database.")
        ]
        
        examples = [
            "aico lmdb status",
            "aico lmdb ls",
            "aico lmdb count conversation_history",
            "aico lmdb dump message_index --limit 10",
            "aico lmdb tail conversation_history --limit 5",
            "aico lmdb tail message_index --limit 3 --full"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="lmdb",
            description="Manage the LMDB working memory database.",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Manage the LMDB working memory database.",
    callback=lmdb_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
console = Console()

@app.command(name="status", help="Show the status and statistics of the LMDB database.")
def status():
    """Show the status and statistics of the LMDB database."""
    status_data = get_lmdb_status_cli()
    
    table = Table(
        title="✨ [bold cyan]LMDB Working Memory Status[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Property", style="cyan", justify="left")
    table.add_column("Value", style="green", justify="left")

    table.add_row("Database Path", status_data["path"])
    table.add_row("Exists", "✅ Yes" if status_data["exists"] else "❌ No")

    if status_data["exists"] and not status_data.get("error"):
        table.add_row("Size (MB)", str(status_data["size_mb"]))
        
        stats_table = Table(title="Sub-Database Entry Counts", box=None, show_header=False)
        stats_table.add_column("DB Name", style="cyan")
        stats_table.add_column("Count", style="white")
        for name, count in status_data.get("db_stats", {}).items():
            stats_table.add_row(name, f"{count:,}")
        table.add_row("Entries", stats_table)

    elif status_data.get("error"):
        table.add_row("Error", f"[red]{status_data['error']}[/red]")

    console.print(table)

@app.command(name="ls", help="List all named sub-databases and their record counts.")
def ls():
    """List all named sub-databases and their record counts."""
    status_data = get_lmdb_status_cli()
    if not status_data["exists"]:
        console.print("[red]Error: LMDB database not found. Run 'aico db init' first.[/red]")
        raise typer.Exit(1)

    if status_data.get("error"):
        console.print(f"[red]Error accessing LMDB database: {status_data['error']}[/red]")
        raise typer.Exit(1)

    table = Table(
        title="✨ [bold cyan]LMDB Sub-Databases[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    
    table.add_column("Database Name", style="cyan", justify="left")
    table.add_column("Records", style="white", justify="right")

    db_stats = status_data.get("db_stats", {})
    if not db_stats:
        console.print("[yellow]No sub-databases found or database is empty.[/yellow]")
        return

    for name, count in sorted(db_stats.items()):
        table.add_row(name, f"{count:,}")
    
    console.print()
    console.print(table)
    console.print()

@app.command(name="count", help="Count entries in a specific sub-database.")
def count(db_name: str = typer.Argument(..., help="The name of the sub-database to count.")):
    """Count entries in a specific sub-database."""
    status_data = get_lmdb_status_cli()
    if not status_data["exists"]:
        console.print(f"[red]Error: LMDB database does not exist.[/red]")
        raise typer.Exit(1)
    
    count = status_data.get("db_stats", {}).get(db_name)
    if count is None:
        console.print(f"[red]Error: Sub-database '{db_name}' not found.[/red]")
        raise typer.Exit(1)
    
    console.print(f"✨ Entries in '{db_name}': [bold green]{count:,}[/bold green]")

@app.command(name="dump", help="View the first N key-value pairs from a sub-database.")
def dump(db_name: str = typer.Argument(..., help="The name of the sub-database to dump."), limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show.")):
    """View the first N key-value pairs from a sub-database."""
    try:
        table = dump_lmdb_db(db_name, limit)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error dumping database: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="tail", help="View the last N key-value pairs from a sub-database.")
def tail(
    db_name: str = typer.Argument(..., help="The name of the sub-database to tail."),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
    full: bool = typer.Option(False, "--full", help="Show full values without truncation")
):
    """View the last N key-value pairs from a sub-database."""
    try:
        table = tail_lmdb_db(db_name, limit, full=full)
        console.print()
        console.print(table)
        console.print()
    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error reading sub-database: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="clear", help="Clear all data from the LMDB database.")
@destructive
def clear():
    """Clear all data from the LMDB database."""
    if typer.confirm("Are you sure you want to clear the LMDB working memory database? This cannot be undone."):
        try:
            clear_lmdb_cli()
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("Operation cancelled.")
        raise typer.Exit()
